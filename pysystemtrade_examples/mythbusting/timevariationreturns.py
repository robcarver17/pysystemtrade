from systems.provided.futures_chapter15.basesystem import *
import pandas as pd
import numpy as np
from matplotlib.pyplot import show, plot, scatter, gca
from syscore.pdutils import align_to_joint, uniquets, divide_df_single_column
from syscore.dateutils import generate_fitting_dates
from syscore.algos import robust_vol_calc

from systems.portfolio import Portfolios
config = Config("systems.provided.futures_chapter15.futuresconfig.yaml")

rulename = ["ewmac64_256"]
rule_name = rulename[0]

# so we use all the markets we have, equal weighted
del (config.instrument_weights)
config.notional_trading_capital = 10000000
config.forecast_weights = dict([(rule, 1.0) for rule in rulename])
config.use_instrument_weight_estimates = True
config.notional_trading_capital = 10000000

system = System([
    Account(), Portfolios(), PositionSizing(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules()
], csvFuturesData(), config)
system.set_logging_level("on")

a2 = system.accounts.portfolio()

# autocorrelation
pd.concat([a2.weekly.as_df(), a2.weekly.as_df().shift(1)], axis=1).corr()
pd.concat([a2.monthly.as_df(), a2.monthly.as_df().shift(1)], axis=1).corr()
pd.concat([a2.annual.as_df(), a2.annual.as_df().shift(1)], axis=1).corr()

# recent volatility (market by market...)
instrument_code = "EDOLLAR"
return_period = int((250 / 7.5))
days = 256


def get_scatter_data_for_code_vol(system,
                                  instrument_code,
                                  rule_name,
                                  return_period=5,
                                  days=64):

    denom_price = system.rawdata.daily_denominator_price(instrument_code)
    x = system.rawdata.daily_returns(instrument_code)
    vol = robust_vol_calc(x, days)
    perc_vol = 100.0 * divide_df_single_column(vol, denom_price.shift(1))

    volavg = pd.rolling_median(perc_vol, 1250, min_periods=10)
    vol_qq = (perc_vol - volavg) / volavg

    # work out return for the N days after the forecast

    norm_data = system.accounts.pandl_for_instrument_forecast(
        instrument_code, rule_name)

    (vol_qq, norm_data) = align_to_joint(
        vol_qq, norm_data, ffill=(True, False))

    period_returns = pd.rolling_sum(norm_data, return_period, min_periods=1)

    ex_post_returns = period_returns.shift(-return_period)
    lagged_vol = vol_qq.shift(1)

    return (list(ex_post_returns.iloc[:, 0].values),
            list(lagged_vol.iloc[:, 0].values))


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

    # no zeros

    return (binlimits, x_values_to_plot, fit_y, err_y)


instrument_list = system.get_instrument_list()

all_scatter = dict(returns=[], vol=[])

for instrument_code in instrument_list:
    this_instrument_data = get_scatter_data_for_code_vol(
        system, instrument_code, rule_name, return_period, days)
    all_scatter['returns'] = all_scatter['returns'] + this_instrument_data[0]
    all_scatter['vol'] = all_scatter['vol'] + this_instrument_data[1]

(returns, forecast) = clean_data(all_scatter['returns'], all_scatter['vol'])

(binlimits, x_values_to_plot, fit_y, err_y) = bin_fit(forecast, returns)

# this time we multiply the forecast by the fitted Value
