"""
Represent contract dates and expiries
"""

import datetime

from syscore.dateutils import contract_month_from_number

NO_EXPIRY_DATE_PASSED = ""
NO_DAY_PASSED = object()

YEAR_SLICE = slice(0, 4)
MONTH_SLICE = slice(4, 6)
DAY_SLICE = slice(6, 8)
YYYYMM_SLICE = slice(0, 6)


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
            contract_id: str,
            expiry_date: expiryDate=NO_EXPIRY_DATE_PASSED,
            approx_expiry_offset: int=0):
        """

        :param contract_id: string of numbers length 6 or 8 eg '201008' or '201008515'
        :param expiry_date:  string of numbers length 8 be passed eg '20101218'
        """

        try:
            assert isinstance(contract_id, str)
            assert int(contract_id)

            if len(contract_id) == 6:
                self._init_with_yymm(contract_id)
            elif len(contract_id) == 8:
                self._init_with_yymmdd(contract_id)
            else:
                raise Exception()

        except Exception:
            raise Exception(
                "contractDate(contract_date) needs to be defined as a str, yyyymm or yyyymmdd"
            )

        self._set_expiry_date(expiry_date, approx_expiry_offset)


    def __repr__(self):
        return self.contract_date

    def _init_with_yymm(self, contract_id:str):
        """
        Initialise class with length 6 str eg '201901'

        :param contract_id: str
        :return: None
        """

        self.contract_date = contract_id + "00"
        self._only_has_month = True


    def _init_with_yymmdd(self, contract_id: str):
        """
        Initialise class with length 8 str eg '20190115'

        :param contract_id: str
        :return: None
        """

        if contract_id[DAY_SLICE] == "00":
            self._init_with_yymm(contract_id[YYYYMM_SLICE])
        else:
            self.contract_date = contract_id
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

    # not using a setter as shouldn't be done casually
    def update_expiry_date(self, expiry_date: expiryDate):
        self._expiry_date = expiry_date

    def as_dict(self):
        ## safe, db independent way of storing expiry dates
        expiry_date = self.expiry_date.as_tuple()

        # we do this so that we can init the object again from this with the
        # correct length of contract_date
        contract_date = self._contract_date_with_no_trailing_zeros()

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
        return int(self.contract_date[YEAR_SLICE])

    def month(self):
        return int(self.contract_date[MONTH_SLICE])

    def day(self):
        if not self.is_day_defined():
            return 0

        return int(self.contract_date[DAY_SLICE])

    def is_day_defined(self):
        if self._only_has_month:
            return False
        else:
            return True

    def letter_month(self):
        return contract_month_from_number(self.month())

    def _as_date(self):

        tuple_of_dates = self._as_date_tuple()

        return datetime.datetime(*tuple_of_dates)

    def _as_date_tuple(self):
        if self._only_has_month:
            day = 1
        else:
            day = self.day()

        return (self.year(), self.month(), day)

    def _contract_date_with_no_trailing_zeros(self):
        if self._only_has_month:
            # remove trailing zeros
            contract_date = self.contract_date[YYYYMM_SLICE]
        else:
            contract_date = self.contract_date

        return contract_date

class contractDate(object):
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
            contract_id,
            expiry_date=NO_EXPIRY_DATE_PASSED,
            approx_expiry_offset=0):
        """

        :param contract_id: string of numbers length 6 or 8 eg '201008' or '201008515'
        :param expiry_date:  string of numbers length 8 be passed eg '20101218'
        """

        ## TEMP REFACTORING
        inner_contract_date = singleContractDate(contract_id, expiry_date=expiry_date, approx_expiry_offset=approx_expiry_offset)
        self.inner_contract_date = inner_contract_date

    def __repr__(self):
        return self.inner_contract_date.contract_date

    def _only_has_month(self):
        ## FIND WHO IS USING THIS METHOD AND KILL THEM
        return self.inner_contract_date._only_has_month

    @property
    ## KEEP
    def expiry_date(self):
        return self.inner_contract_date.expiry_date

    @property
    def contract_date(self):
        ##
        return self.inner_contract_date.contract_date

    # not using a setter as shouldn't be done casually
    ## KEEP
    def update_expiry_date(self, expiry_date: expiryDate):
        self.inner_contract_date.update_expiry_date(expiry_date)

    def as_dict(self):
        return self.inner_contract_date.as_dict()

    @classmethod
    def create_from_dict(contractDate, results_dict):
        ## KEEP
        # needs to match output from as_dict

        expiry_date = results_dict.get("expiry_date", NO_EXPIRY_DATE_PASSED)

        if expiry_date is not NO_EXPIRY_DATE_PASSED:
            expiry_date = expiryDate(*expiry_date)

        contract_id = results_dict["contract_date"]

        return contractDate(
            contract_id,
            expiry_date=expiry_date)

    def year(self):
        return self.inner_contract_date.year()

    def month(self):
        return self.inner_contract_date.month()

    def day(self):
        return self.inner_contract_date.day()

    def is_day_defined(self):
        return self.inner_contract_date.is_day_defined()

    def letter_month(self):
        return self.inner_contract_date.letter_month()
