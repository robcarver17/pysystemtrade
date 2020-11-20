import datetime as datetime
from copy import copy

import numpy as np
import pandas as pd

from sysobjects.dict_of_named_futures_per_contract_prices import list_of_price_column_names, \
    list_of_contract_column_names, contract_column_names, setOfNamedContracts, contract_name_from_column_name, \
    futuresNamedContractFinalPricesWithContractID, dictFuturesNamedContractFinalPricesWithContractID, price_column_names

from sysobjects.dict_of_futures_per_contract_prices import dictFuturesContractFinalPrices


multiple_data_columns = sorted(
    list_of_price_column_names +
    list_of_contract_column_names)


class futuresMultiplePrices(pd.DataFrame):
    def __init__(self, data):

        _check_valid_multiple_price_data(data)
        super().__init__(data)

        data.index.name = "index"  # arctic compatible

    @classmethod
    def create_from_raw_data(
            futuresMultiplePrices,
            roll_calendar,
            dict_of_futures_contract_closing_prices: dictFuturesContractFinalPrices):
        """

        :param roll_calendar: rollCalendar
        :param dict_of_futures_closing_contract_prices: dictFuturesContractPrices with only one column

        :return: pd.DataFrame with the 6 columns PRICE, CARRY, FORWARD, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD_CONTRACT
        """

        all_price_data_stack = create_multiple_price_stack_from_raw_data(
            roll_calendar, dict_of_futures_contract_closing_prices
        )

        multiple_prices = futuresMultiplePrices(all_price_data_stack)
        multiple_prices._is_empty = False

        return multiple_prices

    @classmethod
    def create_empty(futuresMultiplePrices):
        """
        Our graceful fail is to return an empty, but valid, dataframe
        """

        data = pd.DataFrame(columns=multiple_data_columns)

        multiple_prices = futuresMultiplePrices(data)

        return multiple_prices


    def current_contract_dict(self) -> setOfNamedContracts:
        final_row = self.iloc[-1]
        contract_dict = dict([(key, final_row[value])
                              for key, value in contract_column_names.items()])
        contract_dict = setOfNamedContracts(contract_dict)

        return contract_dict

    def as_dict(self) ->dictFuturesNamedContractFinalPricesWithContractID:
        """
        Split up and transform into dict

        :return: dictFuturesContractFinalPricesWithContractID, keys PRICE, FORWARD, CARRY
        """

        self_as_dict = {}
        for price_column_name in list_of_price_column_names:
            contract_column_name = contract_name_from_column_name(price_column_name)
            self_as_dict[price_column_name] = futuresNamedContractFinalPricesWithContractID(
                self[price_column_name],
                self[contract_column_name],
                price_column_name=price_column_name
            )

        self_as_dict = dictFuturesNamedContractFinalPricesWithContractID(
            self_as_dict)

        return self_as_dict

    @classmethod
    def from_merged_dict(futuresMultiplePrices, prices_dict: dictFuturesNamedContractFinalPricesWithContractID):
        """
        Re-create from dict, eg results of _as_dict

        :param prices_dict: dictFuturesContractFinalPricesWithContractID keys PRICE, CARRY, FORWARD
        :return: object
        """

        multiple_prices_list = []
        for key_name in price_column_names.keys():
            try:
                relevant_data = prices_dict[key_name]

            except KeyError:
                raise Exception(
                    "Create multiple prices as dict needs %s as key" % key_name
                )

            multiple_prices_list.append(relevant_data.as_pd())

        multiple_prices_data_frame = pd.concat(multiple_prices_list, axis=1)

        # Now it's possible we have more price data for some things than others
        # so we forward fill contract_ids; not prices
        multiple_prices_data_frame[
            list_of_contract_column_names
        ] = multiple_prices_data_frame[list_of_contract_column_names].ffill()

        multiple_prices_object = futuresMultiplePrices(
            multiple_prices_data_frame)

        return multiple_prices_object

    def sort_index(self):
        df = pd.DataFrame(self)
        sorted_df = df.sort_index()

        return futuresMultiplePrices(sorted_df)

    def update_multiple_prices_with_dict(self, new_prices_dict: dictFuturesNamedContractFinalPricesWithContractID):
        """
        Given a dict containing prices, forward, carry prices; update existing multiple prices
        Because of asynchronicity, we allow overwriting of earlier data
        WILL NOT WORK IF A ROLL HAS HAPPENED

        :return:
        """

        # Add contractid labels to new_prices_dict

        # For each key in new_prices dict,
        #   merge the prices together
        #   allowing historic updates, but not overwrites of non nan values

        # from the updated prices dict
        # create a new multiple prices object

        current_prices_dict = self.as_dict()

        try:
            merged_data_as_dict = current_prices_dict.merge_data(
                new_prices_dict)
        except Exception as e:
            raise e

        merged_data = futuresMultiplePrices.from_merged_dict(merged_data_as_dict)

        return merged_data

    def drop_trailing_nan(self):
        """
        Drop rows where all values are NaN

        :return: new futuresMultiplePrices
        """
        new_multiple_prices = copy(self)
        found_zeros = True

        while found_zeros and len(new_multiple_prices) > 0:
            last_prices_nan_values = (new_multiple_prices.isna(
            ).iloc[-1][list_of_price_column_names].values)
            if all(last_prices_nan_values):
                # drop the last row
                new_multiple_prices = new_multiple_prices[:-1]
                # Should still be true but let's be careful
                found_zeros = True

            else:
                # Terminate loop
                found_zeros = False
                # Should terminate anyway let's be sure
                break

        return futuresMultiplePrices(new_multiple_prices)

    def add_one_row_with_time_delta(self, prices_dict, timedelta_seconds=1):
        """
        Add a row with a slightly different timestamp

        :param prices_dict: dict of scalars, keys are one or more of 'price','forward','carry','*_contract'
                            If a contract column is missing, we forward fill
                            If a price column is missing, we include nans
        :return: new multiple prices
        """

        alignment_dict = dict(
            price=price_column_names["PRICE"],
            forward=price_column_names["FORWARD"],
            carry=price_column_names["CARRY"],
            price_contract=contract_column_names["PRICE"],
            carry_contract=contract_column_names["CARRY"],
            forward_contract=contract_column_names["FORWARD"],
        )

        new_time_index = self.index[-1] + datetime.timedelta(seconds=1)

        new_dict = {}
        for keyname, value in prices_dict.items():
            new_key = alignment_dict[keyname]
            new_dict[new_key] = value

        new_df = pd.DataFrame(new_dict, index=[new_time_index])

        combined_df = pd.concat([pd.DataFrame(self), new_df], axis=0)

        for colname in list_of_contract_column_names:
            combined_df[colname] = combined_df[colname].ffill()

        return futuresMultiplePrices(combined_df)


def create_multiple_price_stack_from_raw_data(
    roll_calendar, dict_of_futures_contract_closing_prices
):
    """

    :param roll_calendar: rollCalendar
    :param dict_of_futures_closing_contract_prices: dictFuturesContractPrices with only one column

    :return: pd.DataFrame with the 6 columns PRICE, CARRY, FORWARD, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD_CONTRACT
    """

    # We need the carry contracts

    all_price_data_stack = []
    contract_keys = dict_of_futures_contract_closing_prices.keys()

    for rolling_row_index in range(len(roll_calendar.index))[1:]:
        # Between these dates is where we are populating prices
        last_roll_date = roll_calendar.index[rolling_row_index - 1]
        next_roll_date = roll_calendar.index[rolling_row_index]

        end_of_roll_period = next_roll_date
        start_of_roll_period = last_roll_date + pd.DateOffset(
            seconds=1
        )  # to avoid overlaps

        contracts_now = roll_calendar.loc[next_roll_date, :]
        current_contract = contracts_now.current_contract
        next_contract = contracts_now.next_contract
        carry_contract = contracts_now.carry_contract

        current_contract_str = str(current_contract)
        next_contract_str = str(next_contract)
        carry_contract_str = str(carry_contract)

        if (current_contract_str not in contract_keys) or (
            carry_contract_str not in contract_keys
        ):

            # missing, this is okay if we haven't started properly yet
            if len(all_price_data_stack) == 0:
                print(
                    "Missing contracts at start of roll calendar not in price data, ignoring"
                )
                continue
            else:
                raise Exception(
                    "Missing contracts in middle of roll calendar %s, not in price data!" %
                    str(next_roll_date))

        current_price_data = dict_of_futures_contract_closing_prices[
            current_contract_str
        ][start_of_roll_period:end_of_roll_period]
        carry_price_data = dict_of_futures_contract_closing_prices[
            carry_contract_str][start_of_roll_period:end_of_roll_period]

        if next_contract_str not in contract_keys:

            if rolling_row_index == len(roll_calendar.index) - 1:
                # Last entry, this is fine
                print(
                    "Next contract %s missing in last row of roll calendar - this is okay" %
                    next_contract_str)
                next_price_data = pd.Series(np.nan, current_price_data.index)
                next_price_data.iloc[:] = np.nan
            else:
                raise Exception(
                    "Missing contract %s in middle of roll calendar on %s"
                    % (next_contract_str, str(next_roll_date))
                )
        else:
            next_price_data = dict_of_futures_contract_closing_prices[
                next_contract_str
            ][start_of_roll_period:end_of_roll_period]

        all_price_data = pd.concat(
            [current_price_data, next_price_data, carry_price_data], axis=1
        )
        all_price_data.columns = [
            price_column_names["PRICE"],
            price_column_names["FORWARD"],
            price_column_names["CARRY"],
        ]

        all_price_data[contract_column_names["PRICE"]] = current_contract
        all_price_data[contract_column_names["FORWARD"]] = next_contract
        all_price_data[contract_column_names["CARRY"]] = carry_contract

        all_price_data_stack.append(all_price_data)

    # end of loop
    all_price_data_stack = pd.concat(all_price_data_stack, axis=0)

    return all_price_data_stack



def _check_valid_multiple_price_data(data):
    data_present = sorted(data.columns)
    try:
        assert data_present == multiple_data_columns
    except AssertionError:
        raise Exception("futuresMultiplePrices has to conform to pattern")
