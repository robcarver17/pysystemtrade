from dataclasses import dataclass
import pandas as pd
import  datetime

@dataclass
class fitDates(object):
    fit_start: datetime.datetime
    fit_end: datetime.datetime
    period_start: datetime.datetime
    period_end: datetime.datetime
    no_data: bool=False

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
    pass

# FIX ME REFACTOR
def generate_fitting_dates(data: pd.DataFrame, date_method: str, rollyears: int=20) -> listOfFittingDates:
    """
    generate a list 4 tuples, one element for each year in the data
    each tuple contains [fit_start, fit_end, period_start, period_end] datetime objects
    the last period will be a 'stub' if we haven't got an exact number of years

    date_method can be one of 'in_sample', 'expanding', 'rolling'

    if 'rolling' then use rollyears variable
    """

    if date_method not in ["in_sample", "rolling", "expanding"]:
        raise Exception(
            "don't recognise date_method %s should be one of in_sample, expanding, rolling" %
            date_method)

    if isinstance(data, list):
        start_date = min([dataitem.index[0] for dataitem in data])
        end_date = max([dataitem.index[-1] for dataitem in data])
    else:
        start_date = data.index[0]
        end_date = data.index[-1]

    # now generate the dates we use to fit
    if date_method == "in_sample":
        # single period
        return listOfFittingDates([fitDates(start_date, end_date, start_date, end_date)])

    # generate list of dates, one year apart, including the final date
    yearstarts = list(
        pd.date_range(
            start_date,
            end_date,
            freq="12M")) + [end_date]

    # loop through each period
    periods = []
    for tidx in range(len(yearstarts))[1:-1]:
        # these are the dates we test in
        period_start = yearstarts[tidx]
        period_end = yearstarts[tidx + 1]

        # now generate the dates we use to fit
        if date_method == "expanding":
            fit_start = start_date
        elif date_method == "rolling":
            yearidx_to_use = max(0, tidx - rollyears)
            fit_start = yearstarts[yearidx_to_use]
        else:
            raise Exception(
                "don't recognise date_method %s should be one of in_sample, expanding, rolling" %
                date_method)

        if date_method in ["rolling", "expanding"]:
            fit_end = period_start
        else:
            raise Exception("don't recognise date_method %s " % date_method)

        periods.append(
            fitDates(
                fit_start,
                fit_end,
                period_start,
                period_end))

    if date_method in ["rolling", "expanding"]:
        # add on a dummy date for the first year, when we have no data
        periods = [
            fitDates(
                start_date, start_date, start_date, yearstarts[1], no_data=True
            )
        ] + periods

    return listOfFittingDates(periods)

