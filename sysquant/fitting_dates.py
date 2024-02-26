from dataclasses import dataclass
import pandas as pd
import datetime

from syscore.pandas.list_of_df import listOfDataFrames


@dataclass
class fitDates(object):
    fit_start: datetime.datetime
    fit_end: datetime.datetime
    period_start: datetime.datetime
    period_end: datetime.datetime
    no_data: bool = False

    def __repr__(self):
        if self.no_data:
            return "Fit without data, use from %s to %s" % (
                self.period_start,
                self.period_end,
            )
        else:
            return "Fit from %s to %s, use in %s to %s" % (
                self.fit_start,
                self.fit_end,
                self.period_start,
                self.period_end,
            )


class listOfFittingDates(list):
    def list_of_starting_periods(self) -> list:
        return [period.period_start for period in self]

    def index_of_most_recent_period_before_relevant_date(
        self, relevant_date: datetime.datetime
    ):
        list_of_start_periods = self.list_of_starting_periods()
        if relevant_date < list_of_start_periods[0]:
            raise Exception("Date %s is before first fitting date" % str(relevant_date))

        ## Assumes they are sorted
        for index, start_date in enumerate(list_of_start_periods):
            if relevant_date < start_date:
                return index - 1

        return index


IN_SAMPLE = "in_sample"
ROLLING = "rolling"
EXPANDING = "expanding"

POSSIBLE_DATE_METHODS = [IN_SAMPLE, ROLLING, EXPANDING]


def generate_fitting_dates(
    data: pd.DataFrame,
    date_method: str,
    rollyears: int = 20,
    interval_frequency: str = "12M",
) -> listOfFittingDates:
    """
    generate a list 4 tuples, one element for each year in the data
    each tuple contains [fit_start, fit_end, period_start, period_end] datetime objects
    the last period will be a 'stub' if we haven't got an exact number of years

    date_method can be one of 'in_sample', 'expanding', 'rolling'

    if 'rolling' then use rollyears variable
    """

    start_date, end_date = _get_start_and_end_date(data)

    periods = generate_fitting_dates_given_start_and_end_date(
        start_date=start_date,
        end_date=end_date,
        date_method=date_method,
        rollyears=rollyears,
        interval_frequency=interval_frequency,
    )

    return periods


def generate_fitting_dates_given_start_and_end_date(
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    date_method: str,
    rollyears: int = 20,
    interval_frequency: str = "12M",
) -> listOfFittingDates:
    """
    generate a list 4 tuples, one element for each year in the data
    each tuple contains [fit_start, fit_end, period_start, period_end] datetime objects
    the last period will be a 'stub' if we haven't got an exact number of years

    date_method can be one of 'in_sample', 'expanding', 'rolling'

    if 'rolling' then use rollyears variable
    """

    if date_method not in POSSIBLE_DATE_METHODS:
        raise Exception(
            "don't recognise date_method %s should be one of %s"
            % (date_method, str(POSSIBLE_DATE_METHODS))
        )

    # now generate the dates we use to fit
    if date_method == IN_SAMPLE:
        # single period
        return _in_sample_dates(start_date, end_date)

    # generate list of dates, one year apart, including the final date
    list_of_starting_dates_per_period = _list_of_starting_dates_per_period(
        start_date, end_date, interval_frequency=interval_frequency
    )

    # loop through each perio

    periods = []
    for period_index in range(len(list_of_starting_dates_per_period))[1:-1]:
        fit_date = _fit_dates_for_period_index(
            period_index,
            list_of_starting_dates_per_period=list_of_starting_dates_per_period,
            date_method=date_method,
            rollyears=rollyears,
            start_date=start_date,
        )
        periods.append(fit_date)

    periods = _add_dummy_period_if_required(
        periods,
        date_method=date_method,
        list_of_starting_dates_per_period=list_of_starting_dates_per_period,
        start_date=start_date,
    )

    return listOfFittingDates(periods)


def _get_start_and_end_date(data):
    if isinstance(data, listOfDataFrames):
        start_date = min([dataitem.index[0] for dataitem in data])
        end_date = max([dataitem.index[-1] for dataitem in data])
    else:
        start_date = data.index[0]
        end_date = data.index[-1]

    return start_date, end_date


def _in_sample_dates(start_date: datetime.datetime, end_date: datetime.datetime):
    return listOfFittingDates([fitDates(start_date, end_date, start_date, end_date)])


def _list_of_starting_dates_per_period(
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    interval_frequency: str = "12M",
):
    ## We don't want to do offsets
    if interval_frequency == "W":
        use_interval_frequency = "7D"
    elif interval_frequency == "M":
        use_interval_frequency = "30D"
    elif interval_frequency == "12M" or interval_frequency == "Y":
        use_interval_frequency = "365D"
    else:
        use_interval_frequency = interval_frequency

    results = list(
        pd.date_range(end_date, start_date, freq="-" + use_interval_frequency)
    )

    results.reverse()

    return results


def _fit_dates_for_period_index(
    period_index: int,
    list_of_starting_dates_per_period: list,
    start_date: datetime.datetime,
    date_method: str = "expanding",
    rollyears=20,
):
    period_start = list_of_starting_dates_per_period[period_index]
    period_end = list_of_starting_dates_per_period[period_index + 1]

    if date_method == "expanding":
        fit_start = start_date
    elif date_method == "rolling":
        yearidx_to_use = max(0, period_index - rollyears)
        fit_start = list_of_starting_dates_per_period[yearidx_to_use]
    else:
        raise Exception("date_method %s not known" % date_method)

    fit_end = period_start

    fit_date = fitDates(fit_start, fit_end, period_start, period_end)

    return fit_date


def _add_dummy_period_if_required(
    periods: list,
    date_method: str,
    start_date: datetime.datetime,
    list_of_starting_dates_per_period: list,
):
    if date_method in ["rolling", "expanding"]:
        # add on a dummy date for the first year, when we have no data
        periods = [
            fitDates(
                start_date,
                start_date,
                start_date,
                list_of_starting_dates_per_period[1],
                no_data=True,
            )
        ] + periods

    return periods
