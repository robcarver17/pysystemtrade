import numpy as np
from matplotlib.pyplot import show, legend

from sysdata.csvdata import csvFuturesData
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

## roughly one, two, three weeks; one... twelve months in business days

#WINDOWS_TO_USE=[42,256]
WINDOWS_TO_USE = [10, 14, 20, 28, 40, 57, 80, 113, 160]


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


def random_system_for_regression(config, rules, log_level="on"):

    my_system = System([
        Account(), PortfoliosFixed(), PositionSizing(),
        ForecastCombineEstimated(), ForecastScaleCapEstimated(), rules,
        RawData()
    ], csvFuturesData(), config)

    my_system.set_logging_level(log_level)

    return my_system


rules = create_rules_for_random_system()
config = Config(
    dict(
        use_forecast_scale_estimates=True,
        use_forecast_weight_estimates=True,
        forecast_scalar_estimate=dict(pool_instruments=True),
        instrument_weights=dict(EDOLLAR=.25, US10=.25, CORN=.25, SP500=.25),
        instrument_div_multiplier=1.5))

system = random_system_for_regression(config, rules)

system.accounts.portfolio().cumsum().plot()
show()

ans = system.accounts.pandl_for_all_trading_rules_unweighted()

ans.gross.to_frame().cumsum().plot()
legend()
show()

ans.costs.to_frame().cumsum().plot()
legend()
show()

ans.net.to_frame().cumsum().plot()
legend()
show()

instrument_code = "SP500"
ans = system.combForecast.get_forecast_correlation_matrices(
    instrument_code).corr_list
print(ans[-1])

for instrument_code in system.get_instrument_list():
    for timewindow in WINDOWS_TO_USE:
        rule_name = "regression%d" % timewindow

        scaling = system.forecastScaleCap.get_forecast_scalar(
            instrument_code, rule_name).values[-1]
        turnover = system.accounts.forecast_turnover(instrument_code,
                                                     rule_name)
        cost_sr = system.accounts.get_SR_cost_for_instrument_forecast(
            instrument_code, rule_name)

        print("*** %s Window length %d scalar %.3f turnover %.3f costs %.6f" %
              (instrument_code, timewindow, scaling, turnover, cost_sr))
