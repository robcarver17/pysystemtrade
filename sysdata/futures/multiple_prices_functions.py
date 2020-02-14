from copy import copy
import numpy as np
import pandas as pd

from sysdata.futures.contracts import  futuresContract
from sysdata.futures.instruments import futuresInstrument
from sysdata.futures.multiple_prices import preferred_columns, contract_column_names, price_column_names, futuresMultiplePrices
from sysproduction.data.contracts import diagContracts


def update_multiple_prices_on_roll(data, current_multiple_prices, instrument_code):
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

    ## If the last row is all Nans, we can't do this
    new_multiple_prices = new_multiple_prices.sort_index()
    new_multiple_prices = new_multiple_prices.drop_trailing_nan()

    price_column = price_column_names['PRICE']
    fwd_column = price_column_names['FORWARD']

    current_contract_dict = new_multiple_prices.current_contract_dict()
    old_forward_contract = current_contract_dict[fwd_column]

    old_priced_contract_last_price, price_inferred = get_or_infer_latest_price(new_multiple_prices,
                                                                               price_col=price_column)
    old_forward_contract_last_price, forward_inferred = get_or_infer_latest_price(new_multiple_prices,
                                                                                  price_col=fwd_column)

    diag_contracts = diagContracts(data)

    instrument_object = futuresInstrument(instrument_code)
    ## Old forward contract -> New price contract
    new_price_contract_date_object = diag_contracts.get_contract_date_object_with_roll_parameters(instrument_code,
                                                                                                  old_forward_contract)
    new_price_contract_object = futuresContract(instrument_object, new_price_contract_date_object)
    new_forward_contract_object = new_price_contract_object.next_held_contract()
    new_carry_contract_object = new_price_contract_object.carry_contract()

    new_price_price = get_final_matched_price_from_contract_object(data, new_price_contract_object, new_multiple_prices)
    new_forward_price = get_final_matched_price_from_contract_object(data, new_forward_contract_object,
                                                                     new_multiple_prices)
    new_carry_price = get_final_matched_price_from_contract_object(data, new_carry_contract_object, new_multiple_prices)

    new_price_contractid = new_price_contract_object.date
    new_forward_contractid = new_forward_contract_object.date
    new_carry_contractid = new_carry_contract_object.date

    # If any prices had to be inferred, then add row with both current priced and forward prices
    # Otherwise adjusted prices will break
    if price_inferred or forward_inferred:
        new_multiple_prices = new_multiple_prices.add_one_row_with_time_delta(
            dict(price=old_priced_contract_last_price, forward=old_forward_contract_last_price))

    ## SOME KIND OF WARNING HERE...?

    # Now we add a row with the new rolled contracts
    new_multiple_prices = new_multiple_prices.add_one_row_with_time_delta(dict(price=new_price_price,
                                                                               forward=new_forward_price,
                                                                               carry=new_carry_price,
                                                                               price_contract=new_price_contractid,
                                                                               forward_contract=new_forward_contractid,
                                                                               carry_contract=new_carry_contractid))

    return new_multiple_prices


def get_final_matched_price_from_contract_object(data, contract_object, new_multiple_prices):
    data.add_class_list("arcticFuturesContractPriceData")
    price_series = data.arctic_futures_contract_price.get_prices_for_contract_object(
        contract_object).return_final_prices()

    price_series_reindexed = price_series.reindex(new_multiple_prices.index)

    final_price = price_series_reindexed.values[-1]

    return final_price


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
        inferred_price = infer_latest_price(new_multiple_prices, price_col, col_to_use)
        if not np.isnan(inferred_price):
            # do in order of preference so if we find one we stop
            break

    if np.isnan(inferred_price):
        raise Exception("Couldn't infer price of %s column - can't roll" % price_col)

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
        ## Can't infer
        return np.nan

    ## Can infer, but need last valid time these were matched
    ## Need to match up, ensuring that there is no contract switch
    price_col_contract_col = contract_column_names[price_col]
    col_to_use_contract_col = contract_column_names[col_to_use]

    df_of_col_and_col_to_use = new_multiple_prices[
        [price_col, price_col_contract_col, col_to_use, col_to_use_contract_col]]
    df_of_col_and_col_to_use.columns = ['Price_to_find', 'Contract_of_to_find', 'Price_infer_from',
                                        'Contract_infer_from']

    try:
        ## Ensure we only have price data back to the last roll
        matched_price_data = last_price_data_with_matched_contracts(df_of_col_and_col_to_use)
        inferred_price = infer_price_from_matched_price_data(matched_price_data)
    except:
        return np.nan

    return inferred_price


def last_price_data_with_matched_contracts(df_of_col_and_col_to_use):
    """
    Track back in a Df, removing the early period before a roll

    :param df_of_col_and_col_to_use: DataFrame with ['Price_to_find', 'Contract_of_to_find', 'Price_infer_from', 'Contract_infer_from']
    :return: DataFrame with ['Price_to_find', 'Price_infer_from']
    """

    final_contract_of_to_infer_from = df_of_col_and_col_to_use.Contract_infer_from.values[-1]
    final_contract_of_to_find = df_of_col_and_col_to_use.Contract_of_to_find.values[-1]

    matched_df_dict = pd.DataFrame(columns=['Price_to_find', 'Price_infer_from'])

    ## We will do this backwards, but then sort the final DF so in right order
    length_data = len(df_of_col_and_col_to_use)
    for data_row_idx in range(length_data - 1, 0, -1):
        relevant_row_of_data = df_of_col_and_col_to_use.iloc[data_row_idx]
        current_contract_to_infer_from = relevant_row_of_data.Contract_infer_from
        current_contract_to_find = relevant_row_of_data.Contract_of_to_find

        if current_contract_to_find == final_contract_of_to_find \
                and current_contract_to_infer_from == final_contract_of_to_infer_from:

            row_to_copy = df_of_col_and_col_to_use[['Price_to_find', 'Price_infer_from']].iloc[data_row_idx]
            matched_df_dict = matched_df_dict.append(row_to_copy)
        else:
            ## We're full
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

    offset = matched_price_data_no_nan['Price_to_find'] - matched_price_data_no_nan['Price_infer_from']
    ## Might be noisy. Okay this might be a mixture of daily or weekly, or intraday data, but live with it
    smoothed_offset = offset.rolling(5, min_periods=1).median().values[-1]

    inferred_price = final_price_to_infer_from + smoothed_offset

    return inferred_price

