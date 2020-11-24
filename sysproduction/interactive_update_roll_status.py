"""
Roll adjusted and multiple prices for a given contract, after checking that we do not have positions

NOTE: this does not update the roll calendar .csv files stored elsewhere. Under DRY the sole source of production
  roll info is the multiple prices series
"""
from dataclasses import dataclass
from copy import copy
import numpy as np
import pandas as pd

from syscore.genutils import print_menu_of_values_and_get_response

from sysobjects.contracts import futuresContract
from sysobjects.instruments import futuresInstrument
from sysobjects.multiple_prices import futuresMultiplePrices, singleRowMultiplePrices
from sysobjects.dict_of_named_futures_per_contract_prices import price_name, carry_name, forward_name, \
    price_column_names, contract_column_names
from sysobjects.adjusted_prices import futuresAdjustedPrices

from syscore.objects import success, failure, status

from sysdata.production.roll_state_storage import (
    allowable_roll_state_from_current_and_position,
    explain_roll_state,
    roll_adj_state,
    no_state_available,
    default_state,
)

from sysproduction.diagnostic.report_configs import roll_report_config
from sysproduction.diagnostic.reporting import run_report_with_data_blob, landing_strip

from sysproduction.data.positions import diagPositions, updatePositions
from sysproduction.data.contracts import diagContracts
from sysproduction.data.get_data import dataBlob
from sysproduction.data.prices import diagPrices, updatePrices, get_valid_instrument_code_from_user


def interactive_update_roll_status():
    """
    Update the roll state for a particular instrument
    This includes the option, where possible, to switch the adjusted price series on to a new contract

    :param instrument_code: str
    :return: None
    """

    with dataBlob(log_name="Interactive_Update-Roll-Status") as data:
        instrument_code = get_valid_instrument_code_from_user(data=data)
        data.log.setup(instrument_code = instrument_code)
        # First get the roll info
        # This will also update to console
        run_roll_report(data, instrument_code)

        roll_data = get_required_roll_state(
            data, instrument_code
        )
        if roll_data is no_state_available:
            exit()
        roll_state_required = roll_data.required_state

        modify_roll_state(data, instrument_code, roll_state_required)

        if roll_state_required is roll_adj_state:
            roll_adjusted_prices(data, instrument_code, roll_data.original_roll_status)

    exit()

def run_roll_report(data:dataBlob, instrument_code: str):
    config = roll_report_config.new_config_with_modified_output("console")
    config.modify_kwargs(instrument_code=instrument_code)
    report_results = run_report_with_data_blob(config, data)
    if report_results is failure:
        raise Exception("Can't run roll report, so can't change status")


@dataclass
class RollData(object):
    instrument_code: str
    original_roll_status: str
    position_priced_contract: int
    allowable_roll_states: list

    def display_roll_query_banner(self):

        print(landing_strip(80))
        print("Current State: %s" % self.original_roll_status)
        print(
            "Current position in priced contract %d (if zero can Roll Adjusted prices)" %
            self.position_priced_contract)
        print("")
        print("These are your options:")
        print("")

        for state_number, state in enumerate(self.allowable_roll_states):
            print("%d) %s: %s" % (state_number, state, explain_roll_state(state)))

        print("")

    def get_roll_state_required(self) -> str:
        invalid_input = True
        while invalid_input:
            self.display_roll_query_banner()
            roll_state_required = print_menu_of_values_and_get_response(self.allowable_roll_states)

            if roll_state_required != self.original_roll_status:
                # check if changing
                print("")
                check = input(
                    "Changing roll state for %s from %s to %s, are you sure y/n to try again/<RETURN> to exist: "
                    % (self.instrument_code, self.original_roll_status, roll_state_required)
                )
                print("")
                if check == "y":
                    # happy
                    invalid_input = False
                    break
                elif check=="":
                    print("Okay, we're done")
                    return no_state_available

                else:
                    print("OK. Choose again.")
                    # back to top of loop
                    continue

        self.set_new_roll_state(roll_state_required)

        return roll_state_required

    def set_new_roll_state(self, required_state: str):
        self._required_state = required_state

    @property
    def required_state(self):
        return self._required_state

def get_required_roll_state(data: dataBlob, instrument_code: str)-> RollData:
    roll_data = setup_roll_data(data, instrument_code)

    roll_status  = roll_data.get_roll_state_required()

    if roll_status is no_state_available:
        return no_state_available

    return roll_data


def setup_roll_data(data: dataBlob, instrument_code: str) -> RollData:
    diag_positions = diagPositions(data)
    diag_contracts = diagContracts(data)

    original_roll_status = diag_positions.get_roll_state(instrument_code)
    priced_contract_date = diag_contracts.get_priced_contract_id(
        instrument_code)
    position_priced_contract = (
        diag_positions.get_position_for_instrument_and_contract_date(
            instrument_code, priced_contract_date
        )
    )

    allowable_roll_states = allowable_roll_state_from_current_and_position(
        original_roll_status, position_priced_contract
    )

    roll_data = RollData(instrument_code, original_roll_status, position_priced_contract, allowable_roll_states)

    return roll_data


def modify_roll_state(data: dataBlob, instrument_code: str, roll_state_required: str):
    update_positions = updatePositions(data)
    update_positions.set_roll_state(instrument_code, roll_state_required)


def roll_adjusted_prices(data: dataBlob, instrument_code: str, original_roll_status: str):
    # Going to roll adjusted prices
    update_positions = updatePositions(data)

    roll_result = _roll_adjusted_and_multiple_prices(
        data, instrument_code)
    if roll_result is success:
        # Return the state back to default (no roll) state
        data.log.msg(
            "Successful roll! Returning roll state of %s to %s"
            % (instrument_code, default_state)
        )

        update_positions.set_roll_state(instrument_code, default_state)
    else:
        data.log.msg(
            "Something has gone wrong with rolling adjusted of %s! Returning roll state to previous state of %s" %
            (instrument_code, original_roll_status))
        update_positions.set_roll_state(
            instrument_code, original_roll_status)


def _roll_adjusted_and_multiple_prices(data: dataBlob, instrument_code: str) -> status:
    """
    Roll multiple and adjusted prices

    THE POSITION MUST BE ZERO IN THE PRICED CONTRACT! WE DON'T CHECK THIS HERE

    :param data: dataBlob
    :param instrument_code: str
    :return:
    """
    print(landing_strip(80))
    print("")
    print("Rolling adjusted prices!")
    print("")

    diag_prices = diagPrices(data)

    current_multiple_prices = diag_prices.get_multiple_prices(instrument_code)

    # Only required for potential rollback
    current_adjusted_prices = diag_prices.get_adjusted_prices(instrument_code)

    updated_multiple_prices = update_multiple_prices_on_roll(
        data, current_multiple_prices, instrument_code
    )
    new_adj_prices = futuresAdjustedPrices.stich_multiple_prices(
        updated_multiple_prices
    )

    # We want user input before we do anything
    compare_old_and_new_prices(
        [
            current_multiple_prices,
            updated_multiple_prices,
            current_adjusted_prices,
            new_adj_prices,
        ],
        [
            "Current multiple prices",
            "New multiple prices",
            "Current adjusted prices",
            "New adjusted prices",
        ],
    )
    print("")
    confirm_roll = input(
        "Confirm roll adjusted prices for %s are you sure y/n:" %
        instrument_code)
    if confirm_roll != "y":
        print("\nUSER DID NOT WANT TO ROLL: Setting roll status back to previous state")
        return failure

    try:
        # Apparently good let's try and write rolled data
        price_updater = updatePrices(data)
        price_updater.add_adjusted_prices(
            instrument_code, new_adj_prices, ignore_duplication=True
        )
        price_updater.add_multiple_prices(
            instrument_code, updated_multiple_prices, ignore_duplication=True
        )

    except Exception as e:
        data.log.warn(
            "%s went wrong when rolling: Going to roll-back to original multiple/adjusted prices" %
            e)
        rollback_adjustment(
            data,
            instrument_code,
            current_adjusted_prices,
            current_multiple_prices)
        return failure

    return success


def compare_old_and_new_prices(price_list, price_list_names):
    for df_prices, df_name in zip(price_list, price_list_names):
        print(df_name)
        print("")
        print(df_prices.tail(6))
        print("")


def rollback_adjustment(
    data: dataBlob, instrument_code: str,
        current_adjusted_prices: futuresAdjustedPrices,
        current_multiple_prices: futuresMultiplePrices
):
    price_updater = updatePrices(data)

    try:
        price_updater.add_adjusted_prices(
            instrument_code, current_adjusted_prices, ignore_duplication=True
        )
        price_updater.add_multiple_prices(
            instrument_code, current_multiple_prices, ignore_duplication=True
        )
    except Exception as e:
        data.log.warn(
            "***** ROLLBACK FAILED! %s!You may need to rebuild your data! Check before trading!! *****" %
            e)
        return failure

    return success


def update_multiple_prices_on_roll(
        data: dataBlob,
        current_multiple_prices: futuresMultiplePrices,
        instrument_code: str) -> futuresMultiplePrices:
    """
    Roll multiple prices

    Adds rows to multiple prices

    First row: (optionally) Inferred price and forward prices
    If there is no (old) forward contract price, one needs to be inferred
    If there is no (old) price contract price, one needs to be inferred

    Time index = Last time index + 1 second

    Second row:
    Time index:  Last time index + 1 second

    PRICE = last price of the forward contract
    PRICE_CONTRACT = previous forward contract

    FORWARD_CONTRACT = the new forward contract
    FORWARD_PRICE = the new forward price, this can be Nan; it will get filled in

    CARRY_CONTRACT = the new carry contract
    CARRY_PRICE = the new carry price: if possible infer from price, this can be Nan

    :param data: dataBlob
    :param current_multiple_prices: futuresMultiplePrices
    :return: new futuresMultiplePrices
    """

    new_multiple_prices = futuresMultiplePrices(copy(current_multiple_prices))

    # If the last row is all Nans, we can't do this
    new_multiple_prices = new_multiple_prices.sort_index()
    new_multiple_prices = new_multiple_prices.drop_trailing_nan()

    price_column = price_column_names["PRICE"]
    fwd_column = price_column_names["FORWARD"]

    current_contract_dict = new_multiple_prices.current_contract_dict()
    old_forward_contract = current_contract_dict.forward

    old_priced_contract_last_price, price_inferred = get_or_infer_latest_price(
        new_multiple_prices, price_col=price_column
    )
    old_forward_contract_last_price, forward_inferred = get_or_infer_latest_price(
        new_multiple_prices, price_col=fwd_column)

    diag_contracts = diagContracts(data)

    instrument_object = futuresInstrument(instrument_code)
    # Old forward contract -> New price contract
    new_price_contract_date_object = (
        diag_contracts.get_contract_date_object_with_roll_parameters(
            instrument_code, old_forward_contract
        )
    )
    new_forward_contract_date = new_price_contract_date_object.next_held_contract()
    new_carry_contract_date = new_price_contract_date_object.carry_contract()

    new_price_contract_object = futuresContract(instrument_object, new_price_contract_date_object.contract_date)
    new_forward_contract_object = futuresContract(instrument_object, new_forward_contract_date.contract_date)
    new_carry_contract_object = futuresContract(instrument_object, new_carry_contract_date.contract_date)

    new_price_price = old_forward_contract_last_price
    new_forward_price = get_final_matched_price_from_contract_object(
        data, new_forward_contract_object, new_multiple_prices
    )
    new_carry_price = get_final_matched_price_from_contract_object(
        data, new_carry_contract_object, new_multiple_prices
    )

    new_price_contractid = new_price_contract_object.date_str
    new_forward_contractid = new_forward_contract_object.date_str
    new_carry_contractid = new_carry_contract_object.date_str

    # If any prices had to be inferred, then add row with both current priced and forward prices
    # Otherwise adjusted prices will break
    if price_inferred or forward_inferred:
        new_single_row = singleRowMultiplePrices(price=old_priced_contract_last_price,
                forward=old_forward_contract_last_price)
        new_multiple_prices = new_multiple_prices.add_one_row_with_time_delta(
            new_single_row
        )
    # SOME KIND OF WARNING HERE...?

    # Now we add a row with the new rolled contracts
    newer_single_row = singleRowMultiplePrices( price=new_price_price,
            forward=new_forward_price,
            carry=new_carry_price,
            price_contract=new_price_contractid,
            forward_contract=new_forward_contractid,
            carry_contract=new_carry_contractid)
    newer_multiple_prices = new_multiple_prices.add_one_row_with_time_delta(
        newer_single_row)

    return newer_multiple_prices


def get_final_matched_price_from_contract_object(
    data, contract_object, new_multiple_prices
):

    diag_prices = diagPrices(data)
    price_series = diag_prices.get_prices_for_contract_object(
        contract_object
    ).return_final_prices()

    price_series_reindexed = price_series.reindex(new_multiple_prices.index)

    final_price = price_series_reindexed.values[-1]

    return final_price

## order of preference to  use for missing data
preferred_columns = dict(
    PRICE=[
        forward_name, carry_name], FORWARD=[
            price_name, carry_name], CARRY=[
                price_name, forward_name])


def get_or_infer_latest_price(new_multiple_prices, price_col="PRICE"):
    """
    Get the last price in a given column

    If one can't be found, infer (There will always be a price in some column)

    :param current_multiple_prices: futuresMultiplePrices
    :param price_col: one of 'PRICE','CARRY','FORWARD'
    :return: tuple: float, bool. Bool is true if the price is inferred, otherwise False
    """

    last_price = new_multiple_prices[price_col].values[-1]
    if not np.isnan(last_price):
        ## not inferred
        return last_price, False

    # try and infer from another column
    which_columns_preference = preferred_columns[price_col]

    for col_to_use in which_columns_preference:
        inferred_price = infer_latest_price(
            new_multiple_prices, price_col, col_to_use)
        if not np.isnan(inferred_price):
            # do in order of preference so if we find one we stop
            break

    if np.isnan(inferred_price):
        raise Exception(
            "Couldn't infer price of %s column - can't roll" %
            price_col)

    return inferred_price, True


def infer_latest_price(new_multiple_prices, price_col, col_to_use):
    """
    Infer the last price in price_col from col_to_use

    :param new_multiple_prices:
    :param price_col: str, must be column in new_multiple_prices
    :param col_to_use: str, must be column in new_multiple_prices
    :return: float or np.nan if no price found
    """

    last_price_to_infer_from = new_multiple_prices[col_to_use].values[-1]

    if np.isnan(last_price_to_infer_from):
        # Can't infer
        return np.nan

    # Can infer, but need last valid time these were matched
    # Need to match up, ensuring that there is no contract switch
    price_col_contract_col = contract_column_names[price_col]
    col_to_use_contract_col = contract_column_names[col_to_use]

    df_of_col_and_col_to_use = new_multiple_prices[
        [price_col, price_col_contract_col, col_to_use, col_to_use_contract_col]
    ]
    df_of_col_and_col_to_use.columns = [
        "Price_to_find",
        "Contract_of_to_find",
        "Price_infer_from",
        "Contract_infer_from",
    ]

    try:
        # Ensure we only have price data back to the last roll
        matched_price_data = last_price_data_with_matched_contracts(
            df_of_col_and_col_to_use
        )
        inferred_price = infer_price_from_matched_price_data(
            matched_price_data)
    except BaseException:
        return np.nan

    return inferred_price


def last_price_data_with_matched_contracts(df_of_col_and_col_to_use):
    """
    Track back in a Df, removing the early period before a roll

    :param df_of_col_and_col_to_use: DataFrame with ['Price_to_find', 'Contract_of_to_find', 'Price_infer_from', 'Contract_infer_from']
    :return: DataFrame with ['Price_to_find', 'Price_infer_from']
    """

    final_contract_of_to_infer_from = (
        df_of_col_and_col_to_use.Contract_infer_from.values[-1]
    )
    final_contract_of_to_find = df_of_col_and_col_to_use.Contract_of_to_find.values[-1]

    matched_df_dict = pd.DataFrame(
        columns=[
            "Price_to_find",
            "Price_infer_from"])

    # We will do this backwards, but then sort the final DF so in right order
    length_data = len(df_of_col_and_col_to_use)
    for data_row_idx in range(length_data - 1, 0, -1):
        relevant_row_of_data = df_of_col_and_col_to_use.iloc[data_row_idx]
        current_contract_to_infer_from = relevant_row_of_data.Contract_infer_from
        current_contract_to_find = relevant_row_of_data.Contract_of_to_find

        if (
            current_contract_to_find == final_contract_of_to_find
            and current_contract_to_infer_from == final_contract_of_to_infer_from
        ):

            row_to_copy = df_of_col_and_col_to_use[
                ["Price_to_find", "Price_infer_from"]
            ].iloc[data_row_idx]
            matched_df_dict = matched_df_dict.append(row_to_copy)
        else:
            # We're full
            break

    if len(matched_df_dict) == 0:
        raise Exception("Empty matched price series!")

    matched_df_dict = matched_df_dict.sort_index()

    return matched_df_dict


def infer_price_from_matched_price_data(matched_price_data):
    """
    Infer the final price of one contract from the price of another contract

    :param matched_price_data: df with two price columns: Price_to_find, Price_infer_from
    :return: float
    """
    final_price_to_infer_from = matched_price_data.Price_infer_from.values[-1]
    matched_price_data_no_nan = matched_price_data.dropna()

    if len(matched_price_data_no_nan) == 0:
        print("Can't find any non NA when implying price")
        return np.nan

    offset = (
        matched_price_data_no_nan["Price_to_find"]
        - matched_price_data_no_nan["Price_infer_from"]
    )
    # Might be noisy. Okay this might be a mixture of daily or weekly, or
    # intraday data, but live with it
    smoothed_offset = offset.rolling(5, min_periods=1).median().values[-1]

    inferred_price = final_price_to_infer_from + smoothed_offset

    return inferred_price
