"""
Spot fx prices
"""

import pandas as pd
from sysdata.data import baseData


class fxPrices(pd.Series):
    """
    adjusted price information
    """

    def __init__(self, data):

        super().__init__(data)

        self._is_empty=False

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
            return fxPrices.create_empty()

    def get_current_fx_price(self, code):
        """
        Get a snapshot of the latest FX price for a currency

        :param code: str
        :return: float
        """
        if self.is_code_in_data(code):
            return self._get_current_fx_price_without_checking()
        else:
            return np.nan


    def _get_fx_prices_without_checking(self, code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def _get_current_fx_price_without_checking(self, code):
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
            self.log.error("You need to call delete_fx_prices with a flag to be sure")

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
                self.log.error("There is already %s in the data, you have to delete it first" % code)

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
        self.log.label(fx_code=code)

        old_fx_prices = self.get_fx_prices(code)
        last_date_in_old_price = old_fx_prices.index[-1]

        new_fx_prices = new_fx_prices[new_fx_prices.index>last_date_in_old_price]

        if len(new_fx_prices)==0:
            self.log.msg("No additional data since %s for %s" % (str(last_date_in_old_price), code))
            return 0

        fx_prices = pd.concat([old_fx_prices, new_fx_prices], axis=0)
        fx_prices = fx_prices.sort_index()

        # remove duplicates (shouldn't be any, but...)
        fx_prices = fx_prices[~fx_prices.index.duplicated(keep='first')]

        # write sum of both prices
        self.add_fx_prices(code, fx_prices, ignore_duplication=True)
