"""
Represent and read/write contract dates and expiries
"""

import datetime

from syscore.dateutils import contract_month_from_number

NO_EXPIRY_DATE_PASSED = object()
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


class expiryDate(datetime.datetime):
    def as_tuple(self):
        return (self.year, self.month, self.day)

    @classmethod
    def from_str(expiryDate, date_as_str, date_format="%Y%m%d"):
        as_date = datetime.datetime.strptime(date_as_str, date_format)

        return expiryDate(as_date.year, as_date.month, as_date.day)

    def as_str(self):
        return self.strftime("%Y%m%d")


class contractDate(object):
    """
    A single contract date; either in the form YYYYMM or YYYYMMDD

    Use cases:
    - normal contract eg 201712 and expiry date like 20171214
    - VIX where contract needs to be defined as 20171214 because of weekly expiries
    - Gas where contract month and expiry date are in different months

    We store the expiry date separately

    Either:

    - we know the expiry date precisely and it's passed when we create the object
    - OR we have to approximate by using the 1st of the month when the object is created
    - OR we can make a better approximation by applying an offset to the approximate date
    """

    def __init__(
            self,
            contract_date,
            expiry_date=NO_EXPIRY_DATE_PASSED,
            approx_expiry_offset=0):
        """

        :param contract_date: string of numbers length 6 or 8 eg '201008' or '201008515'
        :param expiry_date:  tuple which can be passed to datetime.datetime eg (2008,1,1)
        """

        try:
            assert isinstance(contract_date, str)
            assert int(contract_date)

            if len(contract_date) == 6:
                self._init_with_month(contract_date)
            elif len(contract_date) == 8:
                self._init_with_day(contract_date)
            else:
                raise Exception()

        except BaseException:
            raise Exception(
                "contractDate(contract_date) needs to be defined as a str, yyyymm or yyyymmdd"
            )

        # The approx expiry offset must be set first before we try and define
        # the expiry
        self._approx_expiry_offset = approx_expiry_offset

        # set expiry date
        self.expiry_date = expiry_date

    @property
    def expiry_date(self):
        return self._expiry_date

    @expiry_date.setter
    def expiry_date(self, expiry_date):

        if expiry_date is NO_EXPIRY_DATE_PASSED:
            # guess from the contract date - we can always correct this later
            offset_in_days = self._approx_expiry_offset

            approx_expiry_date = self.as_date()
            new_expiry_date = approx_expiry_date + datetime.timedelta(
                days=offset_in_days
            )
            expiry_date = (
                new_expiry_date.year,
                new_expiry_date.month,
                new_expiry_date.day,
            )

        expiry_date = expiryDate(*expiry_date)

        self._expiry_date = expiry_date

    def as_dict(self):
        # we do this so that we can init the object again from this with the
        # correct length of contract_date
        if self._only_has_month:
            # remove trailing zeros
            contract_date = self.contract_date[YYYYMM_SLICE]
        else:
            contract_date = self.contract_date

        expiry_date = self.expiry_date.as_tuple()

        return dict(
            expiry_date=expiry_date,
            contract_date=contract_date,
            approx_expiry_offset=self._approx_expiry_offset,
        )

    @classmethod
    def create_from_dict(contractDate, results_dict):
        # needs to match output from as_dict

        if "expiry_date" in results_dict.keys():
            expiry_date = results_dict["expiry_date"]

            if expiry_date == "":
                expiry_date = NO_EXPIRY_DATE_PASSED
        else:
            expiry_date = NO_EXPIRY_DATE_PASSED

        if "approx_expiry_offset" in results_dict.keys():
            approx_expiry_offset = results_dict["approx_expiry_offset"]
        else:
            approx_expiry_offset = 0

        return contractDate(
            results_dict["contract_date"],
            expiry_date=expiry_date)

    def _init_with_month(self, contract_date):
        """
        Initialise class with length 6 str eg '201901'

        :param contract_date: str
        :return: None
        """

        self.contract_date = contract_date + "00"
        self._only_has_month = True

    def _init_with_day(self, contract_date):
        """
        Initialise class with length 8 str eg '20190115'

        :param contract_date: str
        :return: None
        """

        if contract_date[DAY_SLICE] == "00":
            self._init_with_month(contract_date[YYYYMM_SLICE])
        else:
            self.contract_date = contract_date
            self._only_has_month = False

    def __repr__(self):
        return self.contract_date

    def year(self):
        return int(self.contract_date[YEAR_SLICE])

    def month(self):
        return int(self.contract_date[MONTH_SLICE])

    def is_day_defined(self):
        if self._only_has_month:
            return False
        else:
            return True

    def day(self):
        if self._only_has_month:
            return 0

        return int(self.contract_date[DAY_SLICE])

    def letter_month(self):
        return contract_month_from_number(self.month())

    def as_date_tuple(self):
        if self._only_has_month:
            day = 1
        else:
            day = self.day()

        return (self.year(), self.month(), day)

    def as_date(self):

        tuple_of_dates = self.as_date_tuple()

        return datetime.datetime(*tuple_of_dates)

    @classmethod
    def contract_date_from_numbers(
        contractDate,
        new_year_number,
        new_month_number,
        new_day_number=NO_DAY_PASSED,
        expiry_date=NO_EXPIRY_DATE_PASSED,
        approx_expiry_offset=0,
    ):
        """
        Create a contract date but using numbers rather than a string

        :param new_year_number: int
        :param new_month_number: int
        :param new_day: int
        Other params as __init__
        :return: contractDate
        """

        new_contract_date_as_string = from_contract_numbers_to_contract_string(
            new_year_number, new_month_number, new_day_number
        )

        return contractDate(
            new_contract_date_as_string,
            expiry_date=expiry_date,
            approx_expiry_offset=approx_expiry_offset,
        )

    def check_if_expiry_after_date(self, date_to_check):
        """
        Check to see if the expiry date falls after a given date;

        :param date_to_check: datetime.datetime
        :return: bool
        """

        return self.expiry_date > date_to_check
