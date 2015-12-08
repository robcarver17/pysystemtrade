"""
Let's recap:

We got some data and created a trading rule
"""
from sysdata.csvdata import csvFuturesData
data=csvFuturesData()

from systems.provided.example.rules import ewmac_forecast_with_defaults as ewmac


"""
Okay, I wonder how this would work for a number of instruments?

For this we need to build a system

A system is made up of SystemStages - essentially stages in the process, and it needs data, and perhaps a configuration


The minimum stage you would have would be Rules - which is where you put trading rules
"""



from systems.forecasting import Rules

"""
We can create rules in a number of different ways

Note that to make our rule work it needs to have 
"""
my_rules=Rules(ewmac)
print(my_rules.trading_rules())

my_rules=Rules(dict(ewmac=ewmac))
print(my_rules.trading_rules())

from systems.basesystem import System
my_system=System([my_rules], data)
print(my_system)


print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac").tail(5))



"""
Define a TradingRule
"""

from systems.forecasting import TradingRule
ewmac_rule=TradingRule(ewmac)
my_rules=Rules(dict(ewmac=ewmac_rule))
ewmac_rule


"""
... or two...
"""

ewmac_8=TradingRule((ewmac, [], dict(Lfast=8, Lslow=32)))
ewmac_32=TradingRule(dict(function=ewmac, other_args=dict(Lfast=32, Lslow=128)))
my_rules=Rules(dict(ewmac8=ewmac_8, ewmac32=ewmac_32))
print(my_rules.trading_rules()['ewmac32'])

from systems.forecast_scale_cap import ForecastScaleCapFixed

fcs=ForecastScaleCapFixed(forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65))
my_system=System([fcs, my_rules], data)
print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5))
print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac8").tail(5))
print(my_system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac32").tail(5))

"""
combine some rules
"""

from systems.forecast_combine import ForecastCombineFixed

combiner=ForecastCombineFixed(forecast_weights=dict(ewmac8=0.5, ewmac32=0.5), forecast_div_multiplier=1.1)
my_system=System([fcs, my_rules, combiner], data)
print(my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5))

## size positions
## first raw data
from systems.futures.rawdata import FuturesRawData
rawdata=FuturesRawData()

from systems.positionsizing import PositionSizing
possizer=PositionSizing(percentage_vol_target=10.0, notional_trading_capital=50000, base_currency="GBP")
my_system=System([rawdata, fcs, my_rules, combiner, possizer], data)

print(my_system.positionSize.get_price_volatility("EDOLLAR").tail(5))
print(my_system.positionSize.get_block_value("EDOLLAR").tail(5))
print(my_system.positionSize.get_instrument_sizing_data("EDOLLAR"))
print(my_system.positionSize.get_instrument_value_vol("EDOLLAR").tail(5))
print(my_system.positionSize.get_volatility_scalar("EDOLLAR").tail(5))
print(my_system.positionSize.get_daily_cash_vol_target())
print(my_system.positionSize.get_subsystem_position("EDOLLAR").tail(5))

## portfolio
from systems.portfolio import PortfoliosFixed
portfolio=PortfoliosFixed(instrument_weights=dict(US10=.1, EDOLLAR=.4, CORN=.3, SP500=.2), instrument_div_multiplier=1.5)
my_system=System([rawdata, fcs, my_rules, combiner, possizer, portfolio], data)

print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))

from systems.account import Account


"""
Another approach is to create a config file 
"""

from sysdata.configdata import Config
my_config=Config(dict(trading_rules=dict(ewmac8=ewmac_8, ewmac32=ewmac_32), 
                      instrument_weights=dict(US10=.1, EDOLLAR=.4, CORN=.3, SP500=.2), 
                      instrument_div_multiplier=1.5, forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65), 
                      forecast_weights=dict(ewmac8=0.5, ewmac32=0.5), forecast_div_multiplier=1.1,
                      percentage_vol_target=10.00, notional_trading_capital=50000, base_currency="GBP"))
print(my_config)
my_system=System([Account(), PortfoliosFixed(), PositionSizing(), FuturesRawData(), ForecastCombineFixed(), ForecastScaleCapFixed(), Rules()
], data, my_config)
print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5))
print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac8").tail(5))
print(my_system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac32").tail(5))
print(my_system.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac32"))
print(my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5))
print(my_system.combForecast.get_forecast_weights("EDOLLAR").tail(5))
print(my_system.positionSize.get_subsystem_position("EDOLLAR").tail(5))

print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))

"""
... or to import one
"""
from syscore.fileutils import get_pathname_for_package
my_config=Config(get_pathname_for_package("systems", ["provided", "example", "simplesystemconfig.yaml"]))
print(my_config)
my_system=System([Account(), PortfoliosFixed(), PositionSizing(), FuturesRawData(), ForecastCombineFixed(), ForecastScaleCapFixed(), Rules()
], data, my_config)
print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5))
print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac8").tail(5))
print(my_system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac32").tail(5))
print(my_system.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac32"))
print(my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5))
print(my_system.combForecast.get_forecast_weights("EDOLLAR").tail(5))

print(my_system.positionSize.get_subsystem_position("EDOLLAR").tail(5))

print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))

my_account=Account()
my_system=System([rawdata, fcs, my_rules, combiner, possizer, portfolio, my_account], data)
profits=my_system.account.portfolio()
profits.stats()

