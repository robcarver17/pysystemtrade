"""
Represent contract dates and expiries
"""

import datetime

from syscore.dateutils import contract_month_from_number
from syscore.genutils import list_of_items_seperated_by_underscores

NO_EXPIRY_DATE_PASSED = ""
NO_DAY_PASSED = object()

YEAR_SLICE = slice(0, 4)
MONTH_SLICE = slice(4, 6)
DAY_SLICE = slice(6, 8)
YYYYMM_SLICE = slice(0, 6)

class needSingleLegDate(Exception):
    pass

def from_contract_numbers_to_contract_string(
    new_year_number, new_month_number, new_day_number=NO_DAY_PASSED
):
    new_month_str = "{0:02d}".format(new_month_number)
    new_year_str = str(new_year_number)

    if new_day_number is NO_DAY_PASSED or new_day_number == 0:
        new_day_str = ""
    else:
        new_day_str = "{0:02d}".format(new_day_number)

    new_contract_date_as_string = new_year_str + new_month_str + new_day_str

    return new_contract_date_as_string

EXPIRY_DATE_FORMAT = "%Y%m%d"

class expiryDate(datetime.datetime):
    def as_tuple(self):
        return (self.year, self.month, self.day)

    @classmethod
    def from_str(expiryDate, date_as_str: str):
        try:
            as_date = datetime.datetime.strptime(date_as_str, EXPIRY_DATE_FORMAT)
        except:
            raise Exception("Expiry date %s not in format %s" % date_as_str, EXPIRY_DATE_FORMAT)

        return expiryDate(as_date.year, as_date.month, as_date.day)

    def as_str(self) ->str:
        return self.strftime(EXPIRY_DATE_FORMAT)


class singleContractDate(object):
    """
    A single contract date; either in the form YYYYMM or YYYYMMDD
    *or* specified as a list

    Use cases:
    - normal contract eg 201712 and expiry date like 20171214
    - VIX where contract needs to be defined as 20171214 because of weekly expiries
    - Gas where contract month and expiry date are in different months

    We store the expiry date separately

    Representation is eithier 20171200 or 20171214 so always yyyymmdd

    Either:

    - we know the expiry date precisely and it's passed when we create the object
    - OR we have to approximate by using the 1st of the month when the object is created
    - OR we can make a better approximation by applying an offset to the approximate date
    """

    def __init__(
            self,
            date_str: str,
            expiry_date: expiryDate=NO_EXPIRY_DATE_PASSED,
            approx_expiry_offset: int=0):
        """

        :param date_str: string of numbers length 6 or 8 eg '201008' or '201008515'
        :param expiry_date:  string of numbers length 8 be passed eg '20101218'
        """

        try:
            assert isinstance(date_str, str)
            assert int(date_str)

            if len(date_str) == 6:
                self._init_with_yymm(date_str)
            elif len(date_str) == 8:
                self._init_with_yymmdd(date_str)
            else:
                raise Exception("Can't parse %s as YYYYMM or YYYYMMDD" % str(date_str))

        except Exception:
            raise Exception(
                "contractDate(contract_date) needs to be defined as a str, yyyymm or yyyymmdd"
            )

        self._set_expiry_date(expiry_date, approx_expiry_offset)


    def __repr__(self):
        return self.date

    def __eq__(self, other):
        return self.expiry_date == other.expiry_date

    @property
    def date(self):
        return self._date_str

    def _init_with_yymm(self, date_str:str):
        """
        Initialise class with length 6 str eg '201901'

        :param date_str: str
        :return: None
        """

        self._date_str = date_str + "00"
        self._only_has_month = True


    def _init_with_yymmdd(self, date_str: str):
        """
        Initialise class with length 8 str eg '20190115'

        :param date_str: str
        :return: None
        """

        if date_str[DAY_SLICE] == "00":
            self._init_with_yymm(date_str[YYYYMM_SLICE])
        else:
            self._date_str = date_str
            self._only_has_month = False


    # Hidden setter only used in init
    def _set_expiry_date(self, expiry_date: expiryDate, approx_expiry_offset: int=0):

        if expiry_date is NO_EXPIRY_DATE_PASSED:
            expiry_date = self._get_expiry_date_from_approx_expiry(approx_expiry_offset)

        self._expiry_date = expiry_date

    def _get_expiry_date_from_approx_expiry(self, approx_expiry_offset):
        # guess from the contract date - we can always correct this later

        approx_expiry_date = self._as_date()
        new_expiry_date = approx_expiry_date + datetime.timedelta(
            days=approx_expiry_offset
        )
        expiry_date_tuple = (
            new_expiry_date.year,
            new_expiry_date.month,
            new_expiry_date.day,
        )

        expiry_date = expiryDate(*expiry_date_tuple)

        return expiry_date

    @property
    def expiry_date(self):
        return self._expiry_date

    @property
    def only_has_month(self):
        return self._only_has_month

    # not using a setter as shouldn't be done casually
    def update_expiry_date(self, expiry_date: expiryDate):
        self._expiry_date = expiry_date

    def as_dict(self):
        ## safe, db independent way of storing expiry dates
        expiry_date = self.expiry_date.as_tuple()

        # we do this so that we can init the object again from this with the
        # correct length of contract_date
        contract_date = self._date_str_with_no_trailing_zeros()

        return dict(
            expiry_date=expiry_date,
            contract_date=contract_date,
        )

    @classmethod
    def create_from_dict(contractDate, results_dict):
        # needs to match output from as_dict

        expiry_date = results_dict.get("expiry_date", NO_EXPIRY_DATE_PASSED)

        if expiry_date is not NO_EXPIRY_DATE_PASSED:
            expiry_date = expiryDate(*expiry_date)

        contract_id = results_dict["contract_date"]

        return contractDate(
            contract_id,
            expiry_date=expiry_date)

    def year(self):
        return int(self.date[YEAR_SLICE])

    def month(self):
        return int(self.date[MONTH_SLICE])

    def day(self):
        if not self.is_day_defined():
            return 0

        return int(self.date[DAY_SLICE])

    def is_day_defined(self):
        if self.only_has_month:
            return False
        else:
            return True

    def letter_month(self):
        return contract_month_from_number(self.month())

    def _as_date(self):

        tuple_of_dates = self._as_date_tuple()

        return datetime.datetime(*tuple_of_dates)

    def _as_date_tuple(self):
        if self.only_has_month:
            day = 1
        else:
            day = self.day()

        return (self.year(), self.month(), day)

    def _date_str_with_no_trailing_zeros(self):
        if self.only_has_month:
            # remove trailing zeros
            date_str = self.date[YYYYMM_SLICE]
        else:
            date_str = self.date

        return date_str

CONTRACT_DATE_LIST_ENTRY_KEY = "contract_list"

class contractDate(object):
    """


    A single contract date; either in the form YYYYMM or YYYYMMDD
    *or* a list of contract dates

    Typically

    Use cases:
    - normal contract eg 201712 and expiry date like 20171214
    - VIX where contract needs to be defined as 20171214 because of weekly expiries
    - Gas where contract month and expiry date are in different months

    We store the expiry date separately

    Representation is eithier 20171200 or 20171214 so always yyyymmdd

    Either:

    - we know the expiry date precisely and it's passed when we create the object
    - OR we have to approximate by using the 1st of the month when the object is created
    - OR we can make a better approximation by applying an offset to the approximate date
    """

    def __init__(
            self,
            date_str,
            expiry_date=NO_EXPIRY_DATE_PASSED,
            approx_expiry_offset=0):
        """
        Vanilla
        contractDate("202003")
        contractDate("20200300")
        contractDate("20200302")

        contractDate("202003", expiry_date = expiryDate(2020,3,1)) # approx offset will be ignored
        contractDate("202003", approx_expiry_offset = 2)

        Spreads
        contractDate(["202003", "202006"])
        contractDate("202003_202006")
        contractDate("202003_202006", approx_expiry_offset = 2) ## offset applied to everything
        contractDate("202003_202006", expiry_date = [expiryDate(2020,3,1), expiryDate(2020,6,2)])
        contractDate(dict(contract_list = [dict(contract_date = '20230300', expiry_date = (2023,3,1)),
                                            dict(contract_date = '20230600', expiry_date = (2023,6,2))]))

        :param date_str: string of numbers length 6 or 8 eg '201008' or '201008515', or a list of those, or underscore
        :param expiry_date:  expiryDate object, or list same length as contract date list
        :param approx_expiry_offset: int (applied to all expiry dates if a spread)
        """

        contract_date_list = resolve_date_string_into_list_of_single_contract_dates(date_str, expiry_date=expiry_date, approx_expiry_offset=approx_expiry_offset)
        self._list_of_single_contract_dates = contract_date_list

    def __repr__(self):
        return self.key

    def __eq__(self, other):
        my_list_of_single_contract_dates = self.list_of_single_contract_dates
        other_list_of_single_contract_dates = other.list_of_single_contract_dates
        if len(my_list_of_single_contract_dates)!=len(other_list_of_single_contract_dates):
            return False

        equal_for_each_item = [item == other_item for item, other_item in
                               zip(my_list_of_single_contract_dates,
                                   other_list_of_single_contract_dates)]

        return all(equal_for_each_item)


    @property
    def list_of_single_contract_dates(self):
        return self._list_of_single_contract_dates

    @property
    def key(self):
        return self.date

    @property
    def is_spread_contract(self):
        if len(self.list_of_single_contract_dates)>1:
            return True
        else:
            return False

    @property
    def first_contract(self):
        if self.is_spread_contract:
            raise needSingleLegDate("Can't use this method or property with multiple leg contractDate %s" % str(self))

        return self.list_of_single_contract_dates[0]

    def first_contract_as_contract_date(self):
        first_contract_as_single_contract = self.first_contract
        first_contract_as_dict = {CONTRACT_DATE_LIST_ENTRY_KEY: first_contract_as_single_contract.as_dict()}

        return contractDate(first_contract_as_dict)


    @property
    def only_has_month(self):
        return self.first_contract.only_has_month

    @property
    def expiry_date(self):
        return self.first_contract.expiry_date

    @property
    def date(self):
        return "_".join([str(x) for x in self.list_of_single_contract_dates])


    # not using a setter as shouldn't be done casually
    def update_expiry_date(self, expiry_date: expiryDate):
        self.first_contract.update_expiry_date(expiry_date)

    def as_dict(self):
        return {CONTRACT_DATE_LIST_ENTRY_KEY:
                    [contract_date.as_dict() for contract_date in self.list_of_single_contract_dates]}

    @classmethod
    def create_from_dict(contractDate, results_dict):
        # needs to match output from as_dict
        # Have 'old style' storage for legacy data
        if CONTRACT_DATE_LIST_ENTRY_KEY in results_dict.keys():
            ## new style
            return contractDate(results_dict)
        else:
            ## old style
            return create_contract_date_from_old_style_dict(contractDate, results_dict)

    def year(self):
        return self.first_contract.year()

    def month(self):
        return self.first_contract.month()

    def day(self):
        return self.first_contract.day()

    def is_day_defined(self):
        return self.first_contract.is_day_defined()

    def letter_month(self):
        return self.first_contract.letter_month()

def resolve_date_string_into_list_of_single_contract_dates(date_str, expiry_date=NO_EXPIRY_DATE_PASSED, approx_expiry_offset=0) -> list:
    if type(date_str) is dict:
        contract_date_list = get_contract_date_object_list_from_dict(date_str)
    else:
        contract_date_list = \
            get_contract_date_object_list_from_date_str_and_expiry_date(date_str, expiry_date,
                                                                            approx_expiry_offset=approx_expiry_offset)

    return contract_date_list

def get_contract_date_object_list_from_dict(date_str: dict)-> list:
    try:
        contract_dates_as_list = date_str[CONTRACT_DATE_LIST_ENTRY_KEY]
    except:
        raise Exception("Need to pass dict with single key %s" % CONTRACT_DATE_LIST_ENTRY_KEY)

    contract_date_list = [singleContractDate.create_from_dict(dict_in_list)
                            for dict_in_list in contract_dates_as_list]

    return contract_date_list


def get_contract_date_object_list_from_date_str_and_expiry_date(date_str, expiry_date,
                                                                     approx_expiry_offset=0) ->list:
    date_str_list = resolve_date_string_into_list_of_date_str(date_str)
    expiry_date_list = resolve_expiry_date_into_list_of_expiry_dates(expiry_date, date_str_list)
    contract_date_list = [singleContractDate(date_str_this_date,
                                             expiry_date = expiry_date_this_str,
                                             approx_expiry_offset = approx_expiry_offset,
                                             ) for date_str_this_date, expiry_date_this_str
                                                in zip(date_str_list, expiry_date_list)]

    return contract_date_list


def get_date_str_list_and_expiry_date_list_from_date_str_and_expiry_date(date_str, expiry_date):
    date_str_list = resolve_date_string_into_list_of_date_str(date_str)
    expiry_date_list = resolve_expiry_date_into_list_of_expiry_dates(expiry_date, date_str_list)

    return date_str_list, expiry_date_list

def resolve_date_string_into_list_of_date_str(date_str) -> list:
    """
    str with no underscores becomes [str]

    str with underscores becomes [str1, str2,...]

    list remains list

    :param date_str: str or list
    :return: list
    """
    if type(date_str) is list:
        return date_str

    date_str_as_list = list_of_items_seperated_by_underscores(date_str)
    return date_str_as_list

def resolve_expiry_date_into_list_of_expiry_dates(expiry_date, date_str_as_list):
    if expiry_date is NO_EXPIRY_DATE_PASSED:
        return [NO_EXPIRY_DATE_PASSED] * len(date_str_as_list)

    if type(expiry_date) is list:
        try:
            assert len(expiry_date) == len(date_str_as_list)
        except:
            raise Exception("Length of expiry date list has to match length of date strings")

        return expiry_date

    if type(expiry_date) is expiryDate:
        try:
            assert len(date_str_as_list)==1
        except:
            raise Exception("Passing a single expiry date but there is more than one contract date")

        return [expiry_date]

    raise Exception("Don't know how to handle expiry date %s of type %s" % (str(expiry_date), str(type(expiry_date))))


def create_contract_date_from_old_style_dict(contractDate, results_dict: dict):
    ## for compatibility with original format
    expiry_date = results_dict.get("expiry_date", NO_EXPIRY_DATE_PASSED)

    if expiry_date is not NO_EXPIRY_DATE_PASSED:
        expiry_date = expiryDate(*expiry_date)

    contract_id = results_dict["contract_date"]

    return contractDate(
        contract_id,
        expiry_date=expiry_date)
