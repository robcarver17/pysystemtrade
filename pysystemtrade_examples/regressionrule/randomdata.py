import numpy as np
from matplotlib.pyplot import show

from syscore.dateutils import BUSINESS_DAYS_IN_YEAR

from sysdata.randomdata import RandomData
from sysdata.configdata import Config

from systems.forecasting import Rules
from systems.forecasting import TradingRule

from systems.basesystem import System

from systems.rawdata import RawData
from systems.forecast_combine import ForecastCombineFixed, ForecastCombineEstimated
from systems.forecast_scale_cap import ForecastScaleCapFixed, ForecastScaleCapEstimated
from systems.positionsizing import PositionSizing
from systems.portfolio import PortfoliosFixed
from systems.account import Account

from examples.regressionrule.tradingrule import regression_rule

VOLS_TO_USE = [0.05]

## roughly one, three, six, nine, twelve months in business days
LENGTHS_TO_USE = [64]
## roughly one, two, three weeks; one... twelve months in business days
WINDOWS_TO_USE = [10, 14, 20, 28, 40, 57, 80, 113, 160, 226]


def create_data_for_random_system():
    data = RandomData()

    ## 20 year periods
    Nlength = int(BUSINESS_DAYS_IN_YEAR * 20)

    ## arbitrary to make scaling nice
    Xamplitude = 50.0

    print("creating random data")
    for Volscale in VOLS_TO_USE:
        for Tlength in LENGTHS_TO_USE:

            instrument_code = "fake_T%.2fV_%d" % (Volscale, Tlength)
            print(instrument_code)
            data.generate_random_data(instrument_code, Nlength, Tlength,
                                      Xamplitude, Volscale)

    return data


def create_rules_for_random_system():
    ## create a series of regression trading rules different lookbacks

    rules_dict = dict()
    for timewindow in WINDOWS_TO_USE:
        rule_name = "regression%d" % timewindow

        min_periods = max(2, int(np.ceil(timewindow / 4.0)))

        new_rule = TradingRule((regression_rule, [
            "rawdata.get_daily_prices", "rawdata.daily_returns_volatility"
        ], dict(timewindow=timewindow, min_periods=min_periods)))

        rules_dict[rule_name] = new_rule

    my_rules = Rules(rules_dict)

    return my_rules


def random_system_for_regression(data, config, rules, log_level="on"):

    my_system = System([
        Account(), PortfoliosFixed(), PositionSizing(),
        ForecastCombineEstimated(), ForecastScaleCapEstimated(), rules,
        RawData()
    ], data, config)

    my_system.set_logging_level(log_level)

    return my_system


data = create_data_for_random_system()
rules = create_rules_for_random_system()
config = Config(dict(use_forecast_scale_estimates=True))

system = random_system_for_regression(data, config, rules)

Volscale = 0.05
Tlength = 64
print("Correlation for Vol scale %.2f Trend length %d" % (Volscale, Tlength))

instrument_code = "fake_T%.2fV_%d" % (Volscale, Tlength)

ans = system.combForecast.get_forecast_correlation_matrices(
    instrument_code).corr_list
print(ans[-1])

for Volscale in VOLS_TO_USE:
    for Tlength in LENGTHS_TO_USE:
        instrument_code = "fake_T%.2fV_%d" % (Volscale, Tlength)

        for timewindow in WINDOWS_TO_USE:
            rule_name = "regression%d" % timewindow

            sr = system.accounts.pandl_for_instrument_forecast(
                instrument_code, rule_name).sharpe()
            turnover = system.accounts.forecast_turnover(
                instrument_code, rule_name)

            print(
                "*** Vol scale %.2f Trend length %d Window length %d SR %.3f turnover %.3f"
                % (Volscale, Tlength, timewindow, sr, turnover))
