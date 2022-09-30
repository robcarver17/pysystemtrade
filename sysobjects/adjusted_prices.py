from copy import copy

import numpy as np
import pandas as pd

from syscore.objects import named_object
from syscore.merge_data import full_merge_of_existing_series
from sysobjects.dict_of_named_futures_per_contract_prices import (
    price_column_names,
    contract_column_names,
    price_name,
    contract_name_from_column_name,
)
from sysobjects.multiple_prices import futuresMultiplePrices


class futuresAdjustedPrices(pd.Series):
    """
    adjusted price information
    """

    def __init__(self, price_data):
        price_data.index.name = "index"  # arctic compatible
        super().__init__(price_data)

    @classmethod
    def create_empty(futuresContractPrices):
        """
        Our graceful fail is to return an empty, but valid, dataframe
        """

        futures_contract_prices = futuresContractPrices(pd.Series(dtype='float64'))

        return futures_contract_prices

    @classmethod
    def stitch_multiple_prices(
        futuresAdjustedPrices,
        multiple_prices: futuresMultiplePrices,
        forward_fill: bool = False,
    ):
        """
        Do backstitching of multiple prices using panama method

        If you want to change then override this method

        :param multiple_prices: multiple prices object
        :param forward_fill: forward fill prices and forwards before stitching

        :return: futuresAdjustedPrices

        """
        adjusted_prices = _panama_stitch(multiple_prices, forward_fill)
        return futuresAdjustedPrices(adjusted_prices)

    def update_with_multiple_prices_no_roll(
        self, updated_multiple_prices: futuresMultiplePrices
    ):
        """
        Update adjusted prices assuming no roll has happened

        :param updated_multiple_prices: futuresMultiplePrices
        :return: updated adjusted prices
        """

        updated_adj = _update_adjusted_prices_from_multiple_no_roll(
            self, updated_multiple_prices
        )

        return updated_adj


def _panama_stitch(
    multiple_prices_input: futuresMultiplePrices, forward_fill: bool = False
) -> pd.Series:
    """
    Do a panama stitch for adjusted prices

    :param multiple_prices:  futuresMultiplePrices
    :return: pd.Series of adjusted prices
    """
    multiple_prices = copy(multiple_prices_input)
    if forward_fill:
        multiple_prices.ffill(inplace=True)

    if multiple_prices.empty:
        raise Exception("Can't stitch an empty multiple prices object")

    previous_row = multiple_prices.iloc[0, :]
    adjusted_prices_values = [previous_row.PRICE]

    for dateindex in multiple_prices.index[1:]:
        current_row = multiple_prices.loc[dateindex, :]

        if current_row.PRICE_CONTRACT == previous_row.PRICE_CONTRACT:
            # no roll has occured
            # we just append the price
            adjusted_prices_values.append(current_row.PRICE)
        else:
            # A roll has occured
            adjusted_prices_values = _roll_in_panama(
                adjusted_prices_values, previous_row, current_row
            )

        previous_row = current_row

    # it's ok to return a DataFrame since the calling object will change the
    # type
    adjusted_prices = pd.Series(adjusted_prices_values, index=multiple_prices.index)

    return adjusted_prices


def _roll_in_panama(adjusted_prices_values, previous_row, current_row):
    # This is the sort of code you will need to change to adjust the roll logic
    # The roll differential is from the previous_row
    roll_differential = previous_row.FORWARD - previous_row.PRICE
    if np.isnan(roll_differential):
        raise Exception(
            "On this day %s which should be a roll date we don't have prices for both %s and %s contracts"
            % (
                str(current_row.name),
                previous_row.PRICE_CONTRACT,
                previous_row.FORWARD_CONTRACT,
            )
        )

    # We add the roll differential to all previous prices
    adjusted_prices_values = [
        adj_price + roll_differential for adj_price in adjusted_prices_values
    ]

    # note this includes the price for the previous row, which will now be equal to the forward price
    # We now add todays price. This will be for the new contract

    adjusted_prices_values.append(current_row.PRICE)

    return adjusted_prices_values


no_update_roll_has_occured = futuresAdjustedPrices.create_empty()


def _update_adjusted_prices_from_multiple_no_roll(
    existing_adjusted_prices: futuresAdjustedPrices,
    updated_multiple_prices: futuresMultiplePrices,
) -> futuresAdjustedPrices:
    """
    Update adjusted prices assuming no roll has happened

    :param existing_adjusted_prices: futuresAdjustedPrices
    :param updated_multiple_prices: futuresMultiplePrices
    :return: updated adjusted prices
    """
    new_multiple_price_data, last_contract_in_price_data = _calc_new_multiple_prices(
        existing_adjusted_prices, updated_multiple_prices
    )

    no_roll_has_occured = new_multiple_price_data.check_all_contracts_equal_to(
        last_contract_in_price_data
    )

    if not no_roll_has_occured:
        return no_update_roll_has_occured

    new_adjusted_prices = new_multiple_price_data[price_name]
    new_adjusted_prices = new_adjusted_prices.dropna()

    merged_adjusted_prices = full_merge_of_existing_series(
        existing_adjusted_prices, new_adjusted_prices
    )
    merged_adjusted_prices = futuresAdjustedPrices(merged_adjusted_prices)

    return merged_adjusted_prices


def _calc_new_multiple_prices(
    existing_adjusted_prices: futuresAdjustedPrices,
    updated_multiple_prices: futuresMultiplePrices,
) -> (futuresMultiplePrices, str):

    last_date_in_current_adj = existing_adjusted_prices.index[-1]
    multiple_prices_as_dict = updated_multiple_prices.as_dict()

    prices_in_multiple_prices = multiple_prices_as_dict[price_name]
    price_contract_column = contract_name_from_column_name(price_name)

    last_contract_in_price_data = prices_in_multiple_prices[price_contract_column][
        :last_date_in_current_adj
    ][-1]

    new_multiple_price_data = prices_in_multiple_prices.prices_after_date(
        last_date_in_current_adj
    )

    return new_multiple_price_data, last_contract_in_price_data
