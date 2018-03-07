import datetime
import pandas as pd

from sysdata.data import simData
from syscore.dateutils import contract_month_from_number, month_from_contract_letter

class FuturesData(simData):
    """
        Get futures specific data

        Extends the simData class to add additional features for asset specific

        Will normally be overriden by a method for a specific data source
        See legacy.py

    """

    def __repr__(self):
        return "FuturesData object with %d instruments" % len(
            self.get_instrument_list())

    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

        These are specifically needed for futures trading

        For other asset classes we'd probably pop in eg equities fundamental data, FX interest rates...

        Normally we'd inherit from this method for a specific data source

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        """
        # Default method to get instrument price
        # Will usually be overriden when inherited with specific data source
        error_msg = "You have created a FuturesData() object or you probably need to replace this method to do anything useful"
        self.log.critical(error_msg)



class futuresInstrument(object):
    """
    Define a generic instrument
    """

    def __init__(self, instrument_code,  **ignored_kwargs):
        """
        Create a new instrument

        :param instrument_code: The name of the contract
        :param rollcycle:  The roll cycle
        :param ignored_kwargs: Stuff that might be passed by accident
        """
        assert type(instrument_code) is str

        self.instrument_code = instrument_code

    def __repr__(self):
        return self.instrument_code





class listOfFuturesContracts(list):
    """
    An ordered list of futures contracts
    """

    pass

NO_ROLL_CYCLE = object()

class rollCycle(object):
    """
    A cycle determining how one contract rolls to the next

    Only works with monthly contracts
    """

    def __init__(self, cyclestring):

        assert type(cyclestring) is str

        self.cyclestring = ''.join(sorted(cyclestring))
        self.cycle_as_list = [month_from_contract_letter(contract_letter)
                              for contract_letter in self.cyclestring]


    def as_list(self):
        """

        :return: list with int values referring to month numbers eg January =12 etc
        """
        return self.cycle_as_list

    def offset_month(self, current_month, offset):
        """
        Move a number of months in the expiry cycle

        :param current_month: Current month as a str
        :param offset: number of months to go forwards or backwards
        :return: new month as str
        """

        current_index = self.where_month(current_month)
        len_cycle = len(self.cyclestring)
        new_index = current_index+offset
        cycled_index = new_index % len_cycle

        return self.cyclestring[cycled_index]

    def next_month(self, current_month):
        """
        Move one month forward in expiry cycle

        :param current_month: Current month as a str
        :return: new month as str
        """

        return self.offset_month(current_month, 1)

    def previous_month(self, current_month):
        """
        Move one month back in expiry cycle

        :param current_month: Current month as a str
        :return: new month as str
        """

        return self.offset_month(current_month, -1)

    def where_month(self, current_month):
        """
        Return the index value (0 is first) of month in expiry

        :param current_month: month as str
        :return: int
        """
        self.check_is_month_in_rollcycle(current_month)

        return self.cyclestring.index(current_month)


    def month_is_first(self, current_month):
        """
        Is this the first month in the expiry cycle?

        :param current_month: month as str
        :return: bool
        """

        return self.where_month(current_month) == 0

    def month_is_last(self, current_month):
        """
        Is this the last month in the expiry cycle?

        :param current_month: month as str
        :return: bool
        """

        return self.where_month(current_month) == len(self.cyclestring) - 1


    def check_is_month_in_rollcycle(self, current_month):
        """
        Is current_month in our expiry cycle?

        :param current_month: month as str
        :return: bool
        """
        if current_month in self.cyclestring:
            return True
        else:
            raise Exception("%s not in cycle %s" % (current_month, self.cyclestring))







NO_DAY_DEFINED = object()
NO_EXPIRY_DATE = object()

YEAR_SLICE = slice(0,4)
MONTH_SLICE = slice(4,6)
DAY_SLICE = slice(6,8)

class contractDate(object):
    """
    A single contract date; eithier in the form YYYYMM or YYYYMMDD

    Use cases:
    - normal contract eg 201712 and expiry date like 20171214
    - VIX where contract needs to be defined as 20171214 because of weekly expiries
    - Gas where contract month and expiry date are in different months

    We store the expiry date seperately
    """

    def __init__(self, contract_date, expiry_date=NO_EXPIRY_DATE, rollcycle_string=NO_ROLL_CYCLE, **ignored_kwargs):

        try:
            assert type(contract_date) is str
            assert int(contract_date)

            if len(contract_date)==6:
                self._init_with_month(contract_date)
            elif len(contract_date)==8:
                self._init_with_day(contract_date)
            else:
                raise Exception()

        except:
            raise Exception("contractDate(contract_date) needs to be defined as a str, yyyymm or yyyymmdd")

        self.expiry_date=expiry_date
        self.rollcycle = rollcycle_string

    def _init_with_month(self, contract_date):
        """
        Initialise class with length 6 str eg '201901'

        :param contract_date: str
        :return: None
        """

        self.contract_date = contract_date + "00"
        self._only_has_month=True

    def _init_with_day(self, contract_date):
        """
        Initialise class with length 8 str eg '20190115'

        :param contract_date: str
        :return: None
        """

        self.contract_date=contract_date
        self._only_has_month=False

    def __repr__(self):
        return self.contract_date


    def year(self):
        return int(self.contract_date[YEAR_SLICE])

    def month(self):
        return int(self.contract_date[MONTH_SLICE])

    def day(self):
        if self._only_has_month:
            return NO_DAY_DEFINED

        return int(self.contract_date[DAY_SLICE])

    def letter_month(self):
        return contract_month_from_number(self.month())

    def as_date(self):
        if self._only_has_month:
            day = 1
        else:
            day = self.day()

        return datetime.datetime(self.year(), self.month(), day)

    @classmethod
    def approx_first_contractDate_after_date(contractDate, first_date, rollcycle_string, **kwargs):
        """
        Returns the first contract date in a rollCycle after the month of first_date

        :param rollcycle_string: str to build roll cycle with
        :param first_date: datetime object representing a date
        :return: str representing contract month
        """

        rollcycle = rollCycle(rollcycle_string)
        rollcycle_as_numbers = rollcycle.as_list()

        first_year = first_date.year
        first_month = first_date.month

        if first_month == 12:
            first_month = -1
            first_year = first_year + 1

        # because we don't know exactly when a contract expires in month, if the month of first_date is in the expiry
        #   cycle then we use that month

        relevant_month_number_list = [month_number for month_number in rollcycle_as_numbers if month_number>first_month]

        first_trailing_month = min(relevant_month_number_list)

        return contractDate.contract_date_from_numbers(first_year, first_trailing_month,
                                                       NO_DAY_DEFINED,
                                               rollcycle_string=rollcycle_string, expiry_date=NO_EXPIRY_DATE,
                                                       **kwargs)


    @classmethod
    def contract_date_from_numbers(contractDate, new_year_number, new_month_number, new_day_number=NO_DAY_DEFINED, **kwargs):
        """
        Create a contract date but using numbers rather than a string

        :param new_year_number: int
        :param new_month_number: int
        :param new_day: int
        :param kwargs: other arguments for new contract
        :return: contractDate
        """

        new_month_str = '{0:02d}'.format(new_month_number)
        new_year_str = str(new_year_number)

        if new_day_number is NO_DAY_DEFINED:
            return contractDate(new_year_str + new_month_str, **kwargs)
        else:
            new_day_str = '{0:02d}'.format(new_day_number)
            return contractDate(new_year_str + new_month_str + new_day_str, **kwargs)

    @property
    def rollcycle(self):
        return self._rollcycle

    @rollcycle.setter
    def rollcycle(self, rollcycle_string):
        """
        We can optionally embed roll cycles inside contract dates

        :param rollcycle_string: str defining a roll cycle
        :return: None
        """

        if rollcycle_string is NO_ROLL_CYCLE:
            self._rollcycle = NO_ROLL_CYCLE
        else:
            self._rollcycle = rollCycle(rollcycle_string)

            if not self._rollcycle.check_is_month_in_rollcycle(self.letter_month()):
                raise Exception("ContractDate with roll cycle, month %s must be in cycle %s" % (self.letter_month(),
                                                                                                self.rollcycle))

    def check_for_rollcycle(self):
        """
        Check for the existence of a rollcycle

        :return: bool or error
        """

        if self.rollcycle is NO_ROLL_CYCLE:
            raise Exception("You need a roll cycle to do this")

        else:
            return True

    def next_contract_date(self):
        """
        cycle forwards

        :return: a new contractDate
        """

        self.check_for_rollcycle()
        current_month = self.letter_month()
        if self.rollcycle.month_is_last(current_month):
            ## last period
            new_year_number = self.year()+1
        else:
            new_year_number = self.year()

        new_month_letter = self.rollcycle.next_month(current_month)
        new_month_number = month_from_contract_letter(new_month_letter)

        return self.contract_date_from_numbers(new_year_number, new_month_number, new_day_number=self.day(),
                                          rollcycle_string = self.rollcycle.cyclestring) ## we don't pass expiry date as that will change

    def previous_contract_date(self):
        """
        cycle back in contractDate space

        :return: a new contractDate
        """
        self.check_for_rollcycle()
        current_month = self.letter_month()
        if self.rollcycle.month_is_first(current_month):
            ## first period
            new_year_number = self.year()-1
        else:
            new_year_number = self.year()

        new_month_letter = self.rollcycle.previous_month(current_month)
        new_month_number = month_from_contract_letter(new_month_letter)

        return self.contract_date_from_numbers(new_year_number, new_month_number, new_day_number=self.day(),
                                               rollcycle_string=self.rollcycle.cyclestring) ## we don't pass expiry date as that will change

    def check_if_contract_signature_after_date(self, date_to_check):
        """
        Check to see if the contract signature falls after a given date;
        ignores expiry date if set

        :param date_to_check: datetime.datetime
        :return: bool
        """

        return self.as_date()>date_to_check


class futuresContract(object):
    """
    Define an individual futures contract

    """
    def __init__(self, instrument_object, contract_date_object):
        """

        :param instrument_object:
        :param contract_date_object:
        :param kwargs: other arguments to be passed to contractDate and futuresInstrument
        """

        self.instrument = instrument_object
        self.date = contract_date_object

    def __repr__(self):
        return self.ident()

    def ident(self):
        return self.instrument_code + "/"+ self.contract_date

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    @property
    def contract_date(self):
        return self.date.contract_date

    @property
    def expiry_date(self):
        return self.date.expiry_date

    @property
    def rollcycle_string(self):
        return self.date.rollcycle.cyclestring

    @classmethod
    def simple(futuresContract, instrument_code, contract_date, **kwargs):

        return futuresContract(futuresInstrument(instrument_code, **kwargs), contractDate(contract_date, **kwargs))

    @classmethod
    def approx_first_futuresContract_after_date(futuresContract, instrument_code, first_date, rollcycle_string, **kwargs):

        contract_date_object = contractDate.approx_first_contractDate_after_date(first_date, rollcycle_string, **kwargs)
        instrument_object = futuresInstrument(instrument_code, **kwargs)

        return futuresContract(instrument_object, contract_date_object)


    def next_contract(self):

        return futuresContract(self.instrument, self.date.next_contract_date())


    def previous_contract(self):

        return futuresContract(self.instrument, self.date.previous_contract_date())

MAX_CONTRACT_SIZE = 10000

class listOfFuturesContracts(list):
    """
    Ordered list of futuresContracts
    """

    @classmethod
    def series_of_contracts_within_daterange(listOfFuturesContracts, instrument_code, first_date, last_date,
                                             rollcycle_string, **kwargs):

        assert last_date>first_date

        current_contract = futuresContract.approx_first_futuresContract_after_date(instrument_code, first_date,
                                                                                 rollcycle_string, **kwargs)

        list_of_contracts = [current_contract]

        ## note the same instrument_object will be shared by all in the list so we can modify it directly if needed
        date_still_valid = True

        while date_still_valid:
            print(current_contract)
            current_contract = current_contract.next_contract()
            list_of_contracts.append(current_contract)

            if current_contract.date.check_if_contract_signature_after_date(last_date):
                date_still_valid = False

            if len(list_of_contracts)>MAX_CONTRACT_SIZE:
                raise Exception("too man contracts")

        return listOfFuturesContracts(list_of_contracts)

class futuresData(pd.DataFrame):
    """
    simData frame in specific format
    """

    def __init__(self, data):

        data_present = list(data.columns)
        data_present.sort()

        try:
            assert data_present == ['OPEN', 'CLOSE', 'HIGH', 'LOW', 'SETTLE', 'VOLUME', 'OPEN_INTEREST']
        except AssertionError:
            raise Exception("futuresData has to conform to pattern")

        super().__init__(data)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
