"""
Adjusted prices:

- back-adjustor
- just adjusted prices

"""

import pandas as pd
from sysdata.data import baseData


class futuresAdjustedPrices(pd.Series):
    """
    adjusted price information
    """

    def __init__(self, data):

        super().__init__(data)

        self._is_empty=False

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

    def delete_adjusted_prices(self, instrument_code, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_adjusted_prices_without_any_warning_be_careful(instrument_code)
                self.log.terse("Deleted adjusted price data for %s" % instrument_code)

            else:
                ## doesn't exist anyway
                self.log.warn("Tried to delete non existent adjusted prices for %s" % instrument_code)
        else:
            self.log.error("You need to call delete_adjusted_prices with a flag to be sure")

    def _delete_adjusted_prices_without_any_warning_be_careful(instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_adjusted_prices(self, instrument_code, adjusted_price_data, ignore_duplication=False):
        self.log.label(instrument_code=instrument_code)
        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                self.log.error("There is already %s in the data, you have to delete it first" % instrument_code)

        self._add_adjusted_prices_without_checking_for_existing_entry(instrument_code, adjusted_price_data)

        self.log.terse("Added data for instrument %s" % instrument_code)

    def _add_adjusted_prices_without_checking_for_existing_entry(self, instrument_code, adjusted_price_data):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

