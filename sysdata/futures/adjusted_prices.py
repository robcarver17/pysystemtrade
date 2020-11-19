"""
Adjusted prices:

- back-adjustor
- just adjusted prices

"""

import pandas as pd
import numpy as np
from copy import copy

from syscore.objects import _named_object
from syscore.pdutils import full_merge_of_existing_series
from sysdata.base_data import baseData
from sysobjects.dict_of_named_futures_per_contract_prices import price_column_names, contract_column_names, \
    futuresNamedContractFinalPricesWithContractID


def panama_stitch(multiple_prices_input, forward_fill=False):
    """
    Do a panama stitch for adjusted prices

    :param multiple_prices:  futuresMultiplePrices
    :return: pd.Series of adjusted prices
    """
    multiple_prices = copy(multiple_prices_input)

    if multiple_prices.empty:
        raise Exception("Can't stitch an empty multiple prices object")

    previous_row = multiple_prices.iloc[0, :]
    adjusted_prices_values = [previous_row.PRICE]

    roll_differential_series = multiple_prices.FORWARD - multiple_prices.PRICE

    for dateindex in multiple_prices.index[1:]:
        current_row = multiple_prices.loc[dateindex, :]

        if current_row.PRICE_CONTRACT == previous_row.PRICE_CONTRACT:
            # no roll has occured
            # we just append the price
            adjusted_prices_values.append(current_row.PRICE)
        else:
            # A roll has occured
            # This is the sort of code you will need to change to adjust the roll logic
            # The roll differential is from the previous_row
            roll_differential = previous_row.FORWARD - previous_row.PRICE
            if np.isnan(roll_differential):
                raise Exception(
                    "On this day %s which should be a roll date we don't have prices for both %s and %s contracts" %
                    (str(dateindex), previous_row.PRICE_CONTRACT, previous_row.FORWARD_CONTRACT, ))

            # We add the roll differential to all previous prices
            adjusted_prices_values = [
                adj_price + roll_differential for adj_price in adjusted_prices_values]

            # note this includes the price for the previous row, which will now be equal to the forward price
            # We now add todays price. This will be for the new contract

            adjusted_prices_values.append(current_row.PRICE)

        previous_row = current_row

    # it's ok to return a DataFrame since the calling object will change the
    # type
    adjusted_prices = pd.Series(
        adjusted_prices_values,
        index=multiple_prices.index)

    return adjusted_prices


class futuresAdjustedPrices(pd.Series):
    """
    adjusted price information
    """

    def __init__(self, data):

        super().__init__(data)

        self._is_empty = False

        data.index.name = "index"  # arctic compatible
        data.name = ""

    @classmethod
    def create_empty(futuresContractPrices):
        """
        Our graceful fail is to return an empty, but valid, dataframe
        """

        data = pd.Series()

        futures_contract_prices = futuresContractPrices(data)

        futures_contract_prices._is_empty = True
        return futures_contract_prices

    def empty(self):
        return

    @classmethod
    def stich_multiple_prices(
        futuresAdjustedPrices, multiple_prices, forward_fill=False
    ):
        """
        Do backstitching of multiple prices using panama method

        If you want to change then override this method

        :param multiple_prices: multiple prices object
        :param forward_fill: forward fill prices and forwards before stitching

        :return: futuresAdjustedPrices

        """

        adjusted_prices = panama_stitch(
            multiple_prices, forward_fill=forward_fill)

        return futuresAdjustedPrices(adjusted_prices)

    def update_with_multiple_prices_no_roll(self, updated_multiple_prices):
        """
        Update adjusted prices assuming no roll has happened

        :param updated_multiple_prices: futuresMultiplePrices
        :return: updated adjusted prices
        """

        updated_adj = update_adjusted_prices_from_multiple_no_roll(
            self, updated_multiple_prices
        )

        return updated_adj


no_update_roll_has_occured = _named_object("Roll has occured")


def update_adjusted_prices_from_multiple_no_roll(
    existing_adjusted_prices, updated_multiple_prices
):
    """
    Update adjusted prices assuming no roll has happened

    :param existing_adjusted_prices: futuresAdjustedPrices
    :param updated_multiple_prices: futuresMultiplePrices
    :return: updated adjusted prices
    """

    last_date_in_adj = existing_adjusted_prices.index[-1]
    multiple_prices_as_dict = updated_multiple_prices.as_dict()

    prices_in_multiple_prices = multiple_prices_as_dict["PRICE"]
    price_column = price_column_names["PRICE"]
    contract_column = contract_column_names["PRICE"]

    last_contract_in_price_data = prices_in_multiple_prices[contract_column][
        :last_date_in_adj
    ][-1]

    new_price_data = prices_in_multiple_prices.prices_after_date(last_date_in_adj)

    has_roll_occured = not new_price_data.check_all_contracts_equal_to(
        last_contract_in_price_data
    )

    if has_roll_occured:
        return no_update_roll_has_occured

    new_adjusted_prices = new_price_data[price_column]
    new_adjusted_prices = new_adjusted_prices.dropna()

    merged_adjusted_prices = full_merge_of_existing_series(
        existing_adjusted_prices, new_adjusted_prices
    )
    merged_adjusted_prices = futuresAdjustedPrices(merged_adjusted_prices)

    return merged_adjusted_prices


USE_CHILD_CLASS_ERROR = "You need to use a child class of futuresAdjustedPricesData"


class futuresAdjustedPricesData(baseData):
    """
    Read and write data class to get adjusted prices

    We'd inherit from this class for a specific implementation

    """

    def __repr__(self):
        return USE_CHILD_CLASS_ERROR

    def keys(self):
        return self.get_list_of_instruments()

    def get_list_of_instruments(self):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_adjusted_prices(self, instrument_code):
        if self.is_code_in_data(instrument_code):
            return self._get_adjusted_prices_without_checking(instrument_code)
        else:
            return futuresAdjustedPrices.create_empty()

    def _get_adjusted_prices_without_checking(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def __getitem__(self, instrument_code):
        return self.get_adjusted_prices(instrument_code)

    def _delete_all_adjusted_prices(self, are_you_sure=False):
        if are_you_sure:
            instrument_list = self.get_list_of_instruments()
            for instrument_code in instrument_list:
                self.delete_adjusted_prices(
                    instrument_code, are_you_sure=are_you_sure)
        else:
            self.log.error(
                "You need to call delete_all_adjusted_prices with a flag to be sure"
            )

    def delete_adjusted_prices(self, instrument_code, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_adjusted_prices_without_any_warning_be_careful(
                    instrument_code
                )
                self.log.terse(
                    "Deleted adjusted price data for %s" %
                    instrument_code)

            else:
                # doesn't exist anyway
                self.log.warn(
                    "Tried to delete non existent adjusted prices for %s"
                    % instrument_code
                )
        else:
            self.log.error(
                "You need to call delete_adjusted_prices with a flag to be sure"
            )

    def _delete_adjusted_prices_without_any_warning_be_careful(
            instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_adjusted_prices(
        self, instrument_code, adjusted_price_data, ignore_duplication=False
    ):
        self.log.label(instrument_code=instrument_code)
        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                self.log.error(
                    "There is already %s in the data, you have to delete it first" %
                    instrument_code)

        self._add_adjusted_prices_without_checking_for_existing_entry(
            instrument_code, adjusted_price_data
        )

        self.log.terse("Added data for instrument %s" % instrument_code)

    def _add_adjusted_prices_without_checking_for_existing_entry(
        self, instrument_code, adjusted_price_data
    ):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)
