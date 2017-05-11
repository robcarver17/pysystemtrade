from systems.provided.futures_chapter15.basesystem import *
import pandas as pd
import numpy as np
from matplotlib.pyplot import show, plot, scatter, gca
from syscore.pdutils import align_to_joint, uniquets
from syscore.dateutils import generate_fitting_dates


def clean_data(x, y, maxstd=6.0):

    xcap = np.nanstd(x) * maxstd
    ycap = np.nanstd(y) * maxstd

    def _cap(xitem, cap):
        if np.isnan(xitem):
            return xitem
        if xitem > cap:
            return cap
        if xitem < -cap:
            return -cap
        return xitem

    x = [_cap(xitem, xcap) for xitem in x]
    y = [_cap(yitem, ycap) for yitem in y]

    return (x, y)


def bin_fit(x, y, buckets=3):

    assert buckets in [3, 25]

    xstd = np.nanstd(x)

    if buckets == 3:
        binlimits = [np.nanmin(x), -xstd / 2.0, xstd / 2.0, np.nanmax(x)]
    elif buckets == 25:

        steps = xstd / 4.0
        binlimits = np.arange(-xstd * 3.0, xstd * 3.0, steps)

        binlimits = [np.nanmin(x)] + list(binlimits) + [np.nanmax(x)]

    fit_y = []
    err_y = []
    x_values_to_plot = []
    for binidx in range(len(binlimits))[1:]:
        lower_bin_x = binlimits[binidx - 1]
        upper_bin_x = binlimits[binidx]

        x_values_to_plot.append(np.mean([lower_bin_x, upper_bin_x]))

        y_in_bin = [
            y[idx] for idx in range(len(y))
            if x[idx] >= lower_bin_x and x[idx] < upper_bin_x
        ]

        fit_y.append(np.nanmedian(y_in_bin))
        err_y.append(np.nanstd(y_in_bin))

    # Adjust for intercept error
    y_shift = float(np.interp(0.0, x_values_to_plot, fit_y))

    fit_y = [y_value - y_shift for y_value in fit_y]

    return (binlimits, x_values_to_plot, fit_y, err_y)


def get_scatter_data_for_code_forecast(system,
                                       instrument_code,
                                       rule_name,
                                       startdate=None,
                                       enddate=None,
                                       return_period=5):

    norm_data = system.rawdata.norm_returns(instrument_code)
    forecast = system.rules.get_raw_forecast(instrument_code, rule_name)

    if startdate is None:
        startdate = forecast.index[0]
    if enddate is None:
        enddate = forecast.index[-1]

    (forecast, norm_data) = align_to_joint(
        forecast[startdate:enddate],
        norm_data[startdate:enddate],
        ffill=(True, False))

    # work out return for the N days after the forecast
    period_returns = pd.rolling_sum(norm_data, return_period, min_periods=1)

    ex_post_returns = period_returns.shift(-return_period)
    lagged_forecast = forecast.shift(1)

    return (list(ex_post_returns.iloc[:, 0].values),
            list(lagged_forecast.iloc[:, 0].values))


def do_a_little_plot(system):

    rule_name = "carry"
    return_period = 20
    instrument_list = system.get_instrument_list()

    all_scatter = dict(returns=[], forecast=[])
    for instrument_code in instrument_list:
        this_instrument_data = get_scatter_data_for_code_forecast(
            system, instrument_code, rule_name, return_period)
        all_scatter[
            'returns'] = all_scatter['returns'] + this_instrument_data[0]
        all_scatter[
            'forecast'] = all_scatter['forecast'] + this_instrument_data[1]

    (returns, forecast) = clean_data(all_scatter['returns'],
                                     all_scatter['forecast'])

    (binlimits, x_values_to_plot, fit_y, err_y) = bin_fit(forecast, returns)

    scatter(
        all_scatter['forecast'],
        all_scatter['returns'],
        alpha=0.05,
        color="black")
    ax = gca()
    ax.errorbar(x_values_to_plot, fit_y, yerr=err_y)
    show()


def fit_a_filter_datewise(system,
                          rule_name,
                          instrument_code=None,
                          return_period=5,
                          date_method="expanding",
                          rollyears=999,
                          buckets=3):
    """

    if instrument_code is None, fits across all instruments
    """

    if instrument_code is None:
        instrument_list = system.get_instrument_list()
    else:
        instrument_list = [instrument_code]

    fit_dates = generate_fitting_dates([
        system.rules.get_raw_forecast(instrument_code, rule_name)
        for instrument_code in instrument_list
    ], date_method, rollyears)

    filter_data = []
    for fit_period in fit_dates:
        system.log.msg("Estimating fitting from %s to %s" %
                       (fit_period.period_start, fit_period.period_end))

        if fit_period.no_data:
            data = [None, None]
        else:

            data = fit_a_filter(system, rule_name, instrument_list,
                                fit_period.fit_start, fit_period.fit_end,
                                return_period, buckets)

        filter_data.append(data)

    return (fit_dates, filter_data)


def fit_a_filter(system,
                 rule_name,
                 instrument_list,
                 start_date=None,
                 end_date=None,
                 return_period=5,
                 buckets=3):

    all_scatter = dict(returns=[], forecast=[])
    for instrument_code in instrument_list:
        this_instrument_data = get_scatter_data_for_code_forecast(
            system, instrument_code, rule_name, start_date, end_date,
            return_period)
        all_scatter[
            'returns'] = all_scatter['returns'] + this_instrument_data[0]
        all_scatter[
            'forecast'] = all_scatter['forecast'] + this_instrument_data[1]

    (returns, forecast) = clean_data(all_scatter['returns'],
                                     all_scatter['forecast'])

    (binlimits, x_values_to_plot, fit_y, err_y) = bin_fit(
        forecast, returns, buckets)

    return (x_values_to_plot, fit_y)


def filtering_function(raw_forecast,
                       x_bins=None,
                       fit_y=None,
                       startdate=None,
                       enddate=None):
    """
    This is an additional stage that sits between raw forecast and forecast scaling

    x_bins: defines upper and lower limits of ranges
    y_points: defines y values

    We then interpolate to get the appropriate forecast value

    Note that this will screw up any forecast scaling - this needs to be re-done

    """
    if x_bins is None:
        x_bins = [-100.0, 100.0]

    if fit_y is None:
        fit_y = [-100.0, 100.0]

    if startdate is None:
        startdate = raw_forecast.index[0]
    if enddate is None:
        enddate = raw_forecast.index[-1]

    sub_forecast = raw_forecast[startdate:enddate]

    new_values = np.interp(sub_forecast.iloc[:, 0].values, x_bins, fit_y)

    return pd.DataFrame(new_values, index=sub_forecast.index)


from systems.forecast_scale_cap import ForecastScaleCapEstimated, ALL_KEYNAME, str2Bool

from copy import copy


class newfsc(ForecastScaleCapEstimated):
    def get_raw_forecast(self, instrument_code, rule_name):
        """
        override method to filter
        """
        return self.get_filtered_forecast(instrument_code, rule_name)

    def get_filtered_forecast(self, instrument_code, rule_variation_name):
        """
        Filter the forecast
        """

        def _get_filtered_forecast(system, instrument_code,
                                   rule_variation_name, this_stage):

            raw_forecast = this_stage.get_actual_raw_forecast(
                instrument_code, rule_variation_name)

            (fit_dates, filter_data) = this_stage.get_fitted_values(
                instrument_code, rule_variation_name)

            filtered_list = []
            for (fit_period, data_this_period) in zip(fit_dates, filter_data):
                (x_bins, fit_y) = data_this_period

                filtered_list.append(
                    filtering_function(
                        raw_forecast,
                        startdate=fit_period.period_start,
                        enddate=fit_period.period_end,
                        x_bins=x_bins,
                        fit_y=fit_y))

            filtered_forecast = pd.concat(filtered_list, axis=0)

            return uniquets(filtered_forecast)

        filtered_forecast = self.parent.calc_or_cache_nested(
            "get_filtered_forecast", instrument_code, rule_variation_name,
            _get_filtered_forecast, self)

        return filtered_forecast

    def get_fitted_values(self, instrument_code, rule_variation_name):
        def _get_fitted_values(system, instrument_code, rule_variation_name,
                               this_stage, **kwargs):
            this_stage.log.terse("Fitting mapping for %s %s " %
                                 (instrument_code, rule_variation_name))
            if instrument_code == ALL_KEYNAME:
                instrument_code = None

            (fit_dates, filter_data) = fit_a_filter_datewise(
                system, rule_variation_name, instrument_code, **kwargs)

            return (fit_dates, filter_data)

        instrument_fit_config = copy(system.config.instrument_fit)
        pool_instruments = str2Bool(
            instrument_fit_config.pop("pool_instruments"))

        if pool_instruments:
            # pooled, same for all instruments
            instrument_code_key = ALL_KEYNAME

        else:
            ## not pooled
            instrument_code_key = instrument_code

        fitted_values = self.parent.calc_or_cache_nested(
            "get_fitted_values", instrument_code_key, rule_variation_name,
            _get_fitted_values, self, **instrument_fit_config)

        return fitted_values

    def get_actual_raw_forecast(self, instrument_code, rule_variation_name):
        """
        Old method for raw forecast, keep so we can pipe this in
        """
        raw_forecast = self.parent.rules.get_raw_forecast(
            instrument_code, rule_variation_name)

        return raw_forecast


rulename = "ewmac64_256"
return_period = 30

from systems.portfolio import Portfolios
config = Config("systems.provided.futures_chapter15.futuresconfig.yaml")

config.use_forecast_scale_estimates = True
config.instrument_fit = dict(
    pool_instruments=True,
    return_period=return_period,
    buckets=3,
    date_method="in_sample")
config.forecast_weights = dict([(rule, 1.0) for rule in [rulename]])
# so we use all the markets we have, equal weighted
del (config.instrument_weights)
config.notional_trading_capital = 10000000
config.forecast_cap = 40.0

system = System([
    Account(), Portfolios(), PositionSizing(), FuturesRawData(),
    ForecastCombine(), newfsc(), Rules()
], csvFuturesData(), config)

system.set_logging_level("on")

a1 = system.accounts.portfolio()

from systems.portfolio import Portfolios
config = Config("systems.provided.futures_chapter15.futuresconfig.yaml")

config.forecast_weights = dict([(rule, 1.0) for rule in [rulename]])
# so we use all the markets we have, equal weighted
del (config.instrument_weights)
config.notional_trading_capital = 10000000
system.config.forecast_weights = dict([(rule, 1.0) for rule in rulename])
config.use_forecast_scale_estimates = True

system.config.notional_trading_capital = 10000000

system = System([
    Account(), Portfolios(), PositionSizing(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules()
], csvFuturesData(), config)
system.set_logging_level("on")

a2 = system.accounts.portfolio()

from syscore.accounting import account_test

print("Filtered:")
print(a1.stats())
print("")
print("No filter")
print(a2.stats())

print("Test")
print(account_test(a1, a2))

a3 = pd.concat([a1.curve(), a2.curve()], axis=1)
a3.columns = ["filter", "nofilter"]
a3.plot()
show()
