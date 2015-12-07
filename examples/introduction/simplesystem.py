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
Another approach is to create a config file 
"""

from sysdata.configdata import Config
my_config=Config(dict(trading_rules=dict(ewmac=ewmac)))
print(my_config)

my_system=System([Rules()], data, my_config)
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
my_system=System([fcs, my_rules], data, my_config)

print(my_system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac32"))