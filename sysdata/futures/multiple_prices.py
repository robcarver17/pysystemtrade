"""
A multiple price object is a:

pd. dataframe with the 6 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD, FORWARD_CONTRACT
s
All contracts are in yyyymm format

We require these to calculate back adjusted prices and also to work out carry

They can be stored, or worked out 'on the fly'
"""

from sysdata.base_data import baseData

# These are used when inferring prices in an incomplete series
from sysobjects.multiple_prices import futuresMultiplePrices

USE_CHILD_CLASS_ERROR = "You need to use a child class of futuresMultiplePricesData"


class futuresMultiplePricesData(baseData):
    """
    Read and write data class to get multiple prices for a specific future

    We'd inherit from this class for a specific implementation

    """

    def __repr__(self):
        return "futuresMultiplePricesData base class - DO NOT USE"

    def keys(self):
        return self.get_list_of_instruments()

    def get_list_of_instruments(self):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_multiple_prices(self, instrument_code):
        if self.is_code_in_data(instrument_code):
            return self._get_multiple_prices_without_checking(instrument_code)
        else:
            return futuresMultiplePrices.create_empty()

    def _get_multiple_prices_without_checking(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def __getitem__(self, instrument_code):
        return self.get_multiple_prices(instrument_code)

    def _delete_all_multiple_prices(self, are_you_sure=False):
        if are_you_sure:
            instrument_list = self.get_list_of_instruments()
            for instrument_code in instrument_list:
                self.delete_multiple_prices(
                    instrument_code, are_you_sure=are_you_sure)
        else:
            self.log.error(
                "You need to call delete_all_multiple_prices with a flag to be sure"
            )

    def delete_multiple_prices(self, instrument_code, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_multiple_prices_without_any_warning_be_careful(
                    instrument_code
                )
                self.log.terse(
                    "Deleted multiple price data for %s" %
                    instrument_code)

            else:
                # doesn't exist anyway
                self.log.warn(
                    "Tried to delete non existent multiple prices for %s"
                    % instrument_code
                )
        else:
            self.log.error(
                "You need to call delete_multiple_prices with a flag to be sure"
            )

    def _delete_multiple_prices_without_any_warning_be_careful(
            instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_multiple_prices(
        self, instrument_code, multiple_price_data, ignore_duplication=False
    ):
        self.log.label(instrument_code=instrument_code)
        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                self.log.error(
                    "There is already %s in the data, you have to delete it first" %
                    instrument_code)

        self._add_multiple_prices_without_checking_for_existing_entry(
            instrument_code, multiple_price_data
        )

        self.log.terse("Added data for instrument %s" % instrument_code)

    def _add_multiple_prices_without_checking_for_existing_entry(
        self, instrument_code, multiple_price_data
    ):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)
