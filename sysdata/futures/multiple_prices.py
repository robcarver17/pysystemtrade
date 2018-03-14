"""
A multiple price object is a:

pd. dataframe with the 6 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD, FORWARD_CONTRACT

All contracts are in yyyymm format

We require these to calculate back adjusted prices and also to work out carry

They can be stored, or worked out 'on the fly'
"""


import pandas as pd

from sysdata.data import baseData

MULTIPLE_DATA_COLUMNS = ['PRICE', 'CARRY', 'FORWARD', 'PRICE_CONTRACT', 'CARRY_CONTRACT', 'FORWARD_CONTRACT']
MULTIPLE_DATA_COLUMNS.sort()

class futuresMultiplePrices(pd.DataFrame):

    def __init__(self, data):

        data_present = list(data.columns)
        data_present.sort()

        try:
            assert data_present == MULTIPLE_DATA_COLUMNS
        except AssertionError:
            raise Exception("futuresMultiplePrices has to conform to pattern")

        super().__init__(data)

        self._is_empty=False


    @classmethod
    def create_from_raw_data(futuresMultiplePrices, roll_calendar, dict_of_futures_contract_prices):
        """

        :param roll_calendar: rollCalendar
        :param dict_of_futures_contract_prices: dictFuturesContractPrices with only one column

        :return: pd.DataFrame with the 6 columns PRICE, CARRY, FORWARD, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD_CONTRACT
        """

        # We need the carry contracts

        all_price_data_stack=[]

        for rolling_row_index in range(len(roll_calendar.index))[1:]:
            # Between these dates is where we are populating prices
            last_roll_date = roll_calendar.index[rolling_row_index-1]
            next_roll_date = roll_calendar.index[rolling_row_index]

            end_of_roll_period = next_roll_date
            start_of_roll_period = last_roll_date + pd.DateOffset(seconds=1) # to avoid overlaps

            contracts_now = roll_calendar.loc[next_roll_date, :]
            current_contract = contracts_now.current_contract
            next_contract = contracts_now.next_contract
            carry_contract = contracts_now.carry_contract

            current_price_data = dict_of_futures_contract_prices[str(current_contract)][start_of_roll_period:end_of_roll_period]
            next_price_data = dict_of_futures_contract_prices[str(next_contract)][start_of_roll_period:end_of_roll_period]
            carry_price_data = dict_of_futures_contract_prices[str(carry_contract)][start_of_roll_period:end_of_roll_period]

            all_price_data = pd.concat([current_price_data, next_price_data, carry_price_data], axis=1)
            all_price_data.columns = ["PRICE", "FORWARD", "CARRY"]

            all_price_data['PRICE_CONTRACT'] = current_contract
            all_price_data['FORWARD_CONTRACT'] = next_contract
            all_price_data['CARRY_CONTRACT'] = carry_contract

            all_price_data_stack.append(all_price_data)

        all_price_data_stack = pd.concat(all_price_data_stack, axis=0)

        multiple_prices = futuresMultiplePrices(all_price_data_stack)
        multiple_prices._is_empty = False

        return multiple_prices

    @classmethod
    def create_empty(futuresMultiplePrices):
        """
        Our graceful fail is to return an empty, but valid, dataframe
        """

        data = pd.DataFrame(columns=MULTIPLE_DATA_COLUMNS)

        multiple_prices = futuresMultiplePrices(data)
        multiple_prices._is_empty = True

        return multiple_prices

    @property
    def empty(self):
        return self._is_empty

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
        return self.get_instrument_data(instrument_code)

    def delete_multiple_prices(self, instrument_code, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_multiple_prices_without_any_warning_be_careful(instrument_code)
                self.log.terse("Deleted multiple price data for %s" % instrument_code)

            else:
                ## doesn't exist anyway
                self.log.warn("Tried to delete non existent multiple prices for %s" % instrument_code)
        else:
            self.log.error("You need to call delete_multiple_prices with a flag to be sure")

    def _delete_multiple_prices_without_any_warning_be_careful(instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_multiple_prices(self, instrument_code, multiple_price_data, ignore_duplication=False):
        self.log.label(instrument_code=instrument_code)
        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                self.log.error("There is already %s in the data, you have to delete it first" % instrument_code)

        self._add_multiple_prices_without_checking_for_existing_entry(instrument_code, multiple_price_data)

        self.log.terse("Added data for instrument %s" % instrument_code)

    def _add_multiple_prices_without_checking_for_existing_entry(self, instrument_code, multiple_price_data):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

