from collections import namedtuple

import pandas as pd

from syscore.pandas.merge_data_keeping_past_data import (
    merge_newer_data,
    SPIKE_IN_DATA,
)
from syscore.pandas.full_merge_with_replacement import full_merge_of_existing_data


class fxPrices(pd.Series):
    """
    adjusted price information
    """

    def __init__(self, data):

        super().__init__(data)
        data.index.name = "index"
        data.name = ""

    @classmethod
    def create_empty(fxPrices):
        """
        Our graceful fail is to return an empty, but valid, dataframe
        """

        empty_data = pd.Series()
        fx_prices = fxPrices(empty_data)

        return fx_prices

    @classmethod
    def from_data_frame(fxPrices, data_frame):
        return fxPrices(data_frame.T.squeeze())

    def merge_with_other_prices(
        self, new_fx_prices, only_add_rows=True, check_for_spike=True
    ):
        """
        Merges self with new data.
        If only_add_rows is True,
        Otherwise: Any Nan in the existing data will be replaced (be careful!)

        :param new_fx_prices:

        :return: merged fx prices: doesn't update self
        """
        if only_add_rows:
            return self.add_rows_to_existing_data(
                new_fx_prices, check_for_spike=check_for_spike
            )
        else:
            return self._full_merge_of_existing_data(new_fx_prices)

    def _full_merge_of_existing_data(self, new_fx_prices):
        """
        Merges self with new data.
        Any Nan in the existing data will be replaced (be careful!)
        We make this private so not called accidentally

        :param new_fx_prices: the new data
        :return: updated data, doesn't update self
        """

        merged_data = full_merge_of_existing_data(self, new_fx_prices)

        return fxPrices(merged_data)

    def add_rows_to_existing_data(self, new_fx_prices, check_for_spike=True):
        """
        Merges self with new data.
        Only newer data will be added

        :param new_fx_prices:

        :return: merged fxPrices
        """

        merged_fx_prices = merge_newer_data(
            self, new_fx_prices, check_for_spike=check_for_spike
        )
        if merged_fx_prices is SPIKE_IN_DATA:
            return SPIKE_IN_DATA

        merged_fx_prices = fxPrices(merged_fx_prices)

        return merged_fx_prices


currencyValue = namedtuple("currencyValue", "currency, value")


class listOfCurrencyValues(list):
    pass


# by convention we always get prices vs the dollar
DEFAULT_CURRENCY = "USD"


def get_fx_tuple_from_code(code):
    assert len(code) == 6

    currency1 = code[:3]
    currency2 = code[3:]

    return currency1, currency2
