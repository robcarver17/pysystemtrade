"""
Spot fx prices
"""

import pandas as pd
from sysdata.data import baseData
from syscore.pdutils import merge_newer_data, full_merge_of_existing_data

class fxPrices(pd.Series):
    """
    adjusted price information
    """

    def __init__(self, data):

        super().__init__(data)
        data.index.name="index"
        self._is_empty=False
        data.name = ""

    @classmethod
    def create_empty(fxPrices):
        """
        Our graceful fail is to return an empty, but valid, dataframe
        """

        data = pd.Series()

        fx_prices = fxPrices(data)

        fx_prices._is_empty = True

        return fx_prices

    @property
    def empty(self):
        return self._is_empty

    def merge_with_other_prices(self, new_fx_prices, only_add_rows=True):
        """
        Merges self with new data.
        If only_add_rows is True,
        Otherwise: Any Nan in the existing data will be replaced (be careful!)

        :param new_fx_prices:

        :return: merged fx prices: doesn't update self
        """
        if only_add_rows:
            return self.add_rows_to_existing_data(new_fx_prices)
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

    def add_rows_to_existing_data(self, new_fx_prices):
        """
        Merges self with new data.
        Only newer data will be added

        :param new_fx_prices:

        :return: merged fxPrices
        """

        merged_fx_prices = merge_newer_data(self, new_fx_prices)
        merged_fx_prices = fxPrices(merged_fx_prices)

        return merged_fx_prices


USE_CHILD_CLASS_ERROR = "You need to use a child class of fxPricesData"

class fxPricesData(baseData):
    """
    Read and write data class to get fx prices

    We'd inherit from this class for a specific implementation

    """

    def __repr__(self):
        return USE_CHILD_CLASS_ERROR

    def keys(self):
        return self.get_list_of_fxcodes()

    def get_list_of_fxcodes(self):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_fx_prices(self, code):
        """
        Get a historical series of FX prices

        :param code: currency code, in the form EURUSD
        :return: fxData object
        """
        if self.is_code_in_data(code):
            return self._get_fx_prices_without_checking(code)
        else:
            self.log.warn("Code %s is missing from list of FX data" % code, currency_code=code)
            return fxPrices.create_empty()



    def _get_fx_prices_without_checking(self, code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)


    def __getitem__(self, code):
        return self.get_fx_prices(code)

    def delete_fx_prices(self, code, are_you_sure=False):
        self.log.label(fx_code=code)

        if are_you_sure:
            if self.is_code_in_data(code):
                self._delete_fx_prices_without_any_warning_be_careful(code)
                self.log.terse("Deleted fx price data for %s" % code)

            else:
                ## doesn't exist anyway
                self.log.warn("Tried to delete non existent fx prices for %s" % code)
        else:
            self.log.warn("You need to call delete_fx_prices with a flag to be sure")

    def _delete_fx_prices_without_any_warning_be_careful(self, code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def is_code_in_data(self, code):
        if code in self.get_list_of_fxcodes():
            return True
        else:
            return False

    def add_fx_prices(self, code, fx_price_data, ignore_duplication=False):
        self.log.label(fx_code=code)
        if self.is_code_in_data(code):
            if ignore_duplication:
                pass
            else:
                self.log.warn("There is already %s in the data, you have to delete it first" % code)
                return None

        self._add_fx_prices_without_checking_for_existing_entry(code, fx_price_data)

        self.log.terse("Added fx data for code %s" % code)

    def _add_fx_prices_without_checking_for_existing_entry(self, code, fx_price_data):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def update_fx_prices(self, code, new_fx_prices):
        """
        Checks existing data, adds any new data with a timestamp greater than the existing data

        :param code: FX code
        :param new_fx_prices: fxPrices object
        :return: int, number of rows added
        """
        new_log = self.log.setup(fx_code=code)

        old_fx_prices = self.get_fx_prices(code)
        merged_fx_prices = old_fx_prices.add_rows_to_existing_data(new_fx_prices)

        rows_added = len(merged_fx_prices) - len(old_fx_prices)

        if rows_added==0:
            new_log.msg("No additional data since %s for %s" % (str(old_fx_prices.index[-1]), code))
            return 0

        self.add_fx_prices(code, merged_fx_prices, ignore_duplication=True)

        new_log.msg("Added %d additional rows for %s" % (rows_added, code))

        return rows_added