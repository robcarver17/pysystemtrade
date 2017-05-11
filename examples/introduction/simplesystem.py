"""
Let's recap:

We got some data and created a trading rule
"""
from sysdata.csvdata import csvFuturesData
data = csvFuturesData()

from systems.provided.example.rules import ewmac_forecast_with_defaults as ewmac
"""
Okay, I wonder how this would work for a number of instruments?

For this we need to build a system

A system is made up of SystemStages - essentially stages in the process, and it
needs data, and perhaps a configuration

The minimum stage you would have would be Rules - which is where you put
trading rules
"""

from systems.forecasting import Rules
"""
We can create rules in a number of different ways

Note that to make our rule work it needs to have
"""
my_rules = Rules(ewmac)
print(my_rules.trading_rules())

my_rules = Rules(dict(ewmac=ewmac))
print(my_rules.trading_rules())

from systems.basesystem import System
my_system = System([my_rules], data)
print(my_system)

print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac").tail(5))
"""
Define a TradingRule
"""

from systems.forecasting import TradingRule
ewmac_rule = TradingRule(ewmac)
my_rules = Rules(dict(ewmac=ewmac_rule))
ewmac_rule
"""
... or two...
"""

ewmac_8 = TradingRule((ewmac, [], dict(Lfast=8, Lslow=32)))
ewmac_32 = TradingRule(
    dict(function=ewmac, other_args=dict(Lfast=32, Lslow=128)))
my_rules = Rules(dict(ewmac8=ewmac_8, ewmac32=ewmac_32))
print(my_rules.trading_rules()['ewmac32'])

my_system = System([my_rules], data)
my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5)

from sysdata.configdata import Config
my_config = Config()
my_config

empty_rules = Rules()
my_config.trading_rules = dict(ewmac8=ewmac_8, ewmac32=ewmac_32)
my_system = System([empty_rules], data, my_config)
my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5)

from systems.forecast_scale_cap import ForecastScaleCap

# we can estimate these ourselves
my_config.instruments = ["US10", "EDOLLAR", "CORN", "SP500"]
my_config.use_forecast_scale_estimates = True

fcs = ForecastScaleCap()
my_system = System([fcs, my_rules], data, my_config)
print(
    my_system.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac32").tail(
        5))

# or we can use the values from the book
my_config.forecast_scalars = dict(ewmac8=5.3, ewmac32=2.65)
my_config.use_forecast_scale_estimates = False
fcs = ForecastScaleCap()
my_system = System([fcs, my_rules], data, my_config)
print(
    my_system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac32").tail(
        5))
"""
combine some rules
"""

from systems.forecast_combine import ForecastCombine

# defaults
combiner = ForecastCombine()
my_system = System([fcs, my_rules, combiner], data, my_config)
print(my_system.combForecast.get_forecast_weights("EDOLLAR").tail(5))
print(
    my_system.combForecast.get_forecast_diversification_multiplier("EDOLLAR")
    .tail(5))

# estimates:
from systems.account import Account
my_account = Account()
combiner = ForecastCombine()

my_config.forecast_weight_estimate = dict(method="one_period")
my_config.use_forecast_weight_estimates = True
my_config.use_forecast_div_mult_estimates = True

my_system = System([my_account, fcs, my_rules, combiner], data, my_config)

# this is a bit slow, better to know what's going on
my_system.set_logging_level("on")

print(my_system.combForecast.get_forecast_weights("US10").tail(5))
print(
    my_system.combForecast.get_forecast_diversification_multiplier("US10")
    .tail(5))

# fixed:
my_config.forecast_weights = dict(ewmac8=0.5, ewmac32=0.5)
my_config.forecast_div_multiplier = 1.1
my_config.use_forecast_weight_estimates = False
my_config.use_forecast_div_mult_estimates = False

combiner = ForecastCombine()
my_system = System([fcs, empty_rules, combiner], data,
                   my_config)  # no need for accounts if no estimation done
my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5)

# size positions

from systems.positionsizing import PositionSizing
possizer = PositionSizing()
my_config.percentage_vol_target = 25
my_config.notional_trading_capital = 500000
my_config.base_currency = "GBP"

my_system = System([fcs, my_rules, combiner, possizer], data, my_config)

print(my_system.positionSize.get_price_volatility("EDOLLAR").tail(5))
print(my_system.positionSize.get_block_value("EDOLLAR").tail(5))
print(my_system.positionSize.get_instrument_sizing_data("EDOLLAR"))
print(my_system.positionSize.get_instrument_value_vol("EDOLLAR").tail(5))
print(my_system.positionSize.get_volatility_scalar("EDOLLAR").tail(5))
print(my_system.positionSize.get_daily_cash_vol_target())
print(my_system.positionSize.get_subsystem_position("EDOLLAR").tail(5))

# portfolio - estimated
from systems.portfolio import Portfolios
portfolio = Portfolios()

my_config.use_instrument_weight_estimates = True
my_config.use_instrument_div_mult_estimates = True
my_config.instrument_weight_estimate = dict(
    method="shrinkage", date_method="in_sample")

my_system = System([my_account, fcs, my_rules, combiner, possizer, portfolio],
                   data, my_config)

my_system.set_logging_level("on")

print(my_system.portfolio.get_instrument_weights().tail(5))
print(my_system.portfolio.get_instrument_diversification_multiplier().tail(5))

# or fixed
portfolio = Portfolios()
my_config.use_instrument_weight_estimates = False
my_config.use_instrument_div_mult_estimates = False
my_config.instrument_weights = dict(US10=.1, EDOLLAR=.4, CORN=.3, SP500=.2)
my_config.instrument_div_multiplier = 1.5

my_system = System([fcs, my_rules, combiner, possizer, portfolio], data,
                   my_config)

print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))
"""
Have we made some dosh?
"""

my_system = System([fcs, my_rules, combiner, possizer, portfolio, my_account],
                   data, my_config)
profits = my_system.accounts.portfolio()
print(profits.percent().stats())

# have costs data now
print(profits.gross.percent().stats())
print(profits.net.percent().stats())
"""
Another approach is to create a config object
"""
my_config = Config(
    dict(
        trading_rules=dict(ewmac8=ewmac_8, ewmac32=ewmac_32),
        instrument_weights=dict(US10=.1, EDOLLAR=.4, CORN=.3, SP500=.2),
        instrument_div_multiplier=1.5,
        forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65),
        forecast_weights=dict(ewmac8=0.5, ewmac32=0.5),
        forecast_div_multiplier=1.1,
        percentage_vol_target=25.00,
        notional_trading_capital=500000,
        base_currency="GBP"))
print(my_config)
my_system = System([
    Account(), Portfolios(), PositionSizing(), ForecastCombine(),
    ForecastScaleCap(), Rules()
], data, my_config)
print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))
"""
... or to import one
"""
my_config = Config("systems.provided.example.simplesystemconfig.yaml")
print(my_config)
my_system = System([
    Account(), Portfolios(), PositionSizing(), ForecastCombine(),
    ForecastScaleCap(), Rules()
], data, my_config)
print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5))
print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac8").tail(5))
print(
    my_system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac32").tail(
        5))
print(my_system.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac32"))
print(my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5))
print(my_system.combForecast.get_forecast_weights("EDOLLAR").tail(5))

print(my_system.positionSize.get_subsystem_position("EDOLLAR").tail(5))

print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))
