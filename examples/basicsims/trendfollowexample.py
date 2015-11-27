"""

Work up a minimum example of a trend following system

"""

## Get some data

from sysdata.legacy import csvFuturesData
from syscore.algos import robust_vol_calc
from systems.defaultfutures import full_futures_system
from matplotlib.pyplot import show
from sysdata.configdata import configData

import pandas as pd

""""
Let's get some data

We can get data from various places; however for now we're going to use prepackaged 'legacy' data stored
   in csv files
   
"""

data=csvFuturesData()

print data

"""
We get stuff out of data with methods

"""
print(data.get_instrument_list())
print(data.get_instrument_price("EDOLLAR"))

"""
data can also behave in a dict like manner (though it's not a dict)
"""

print(data['SP500'])
print(data.keys())

"""

... however this will only access prices
(note these prices have already been backadjusted for rolls)

We have extra futures data here

"""

print(data.get_instrument_rawcarrydata("US10"))

"""
Technical note: csvFuturesData inherits from FuturesData which itself inherits from Data
The chain is 'data specific' <- 'asset class specific' <- 'generic'

So there are also

In principal there could be an equities data
"""


"""
Let's create a simple trading rule

No capping or scaling

"""

def calc_ewmac_forecast(price, Lfast, Lslow=None):
    
    
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback
    
    Assumes that 'price' is daily data
    """
    ## price: This is the stitched price series
    ## We can't use the price of the contract we're trading, or the volatility will be jumpy
    ## And we'll miss out on the rolldown. See http://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html

    if Lslow is None:
        Lslow=4*Lfast
    
    ## We don't need to calculate the decay parameter, just use the span directly
    
    fast_ewma=pd.ewma(price, span=Lfast)
    slow_ewma=pd.ewma(price, span=Lslow)
    raw_ewmac=fast_ewma - slow_ewma
    
    vol=robust_vol_calc(price.diff())    
    
    return raw_ewmac/vol

"""
Try it out

(this isn't properly scaled at this stage of course)
"""
instrument_code='EDOLLAR'
price=data.get_instrument_price(instrument_code)
ewmac=calc_ewmac_forecast(price, 4, 16)

"""
[FIX ME at this point we'd illustrate how to use 'quick and dirty' p&l tools]
"""

"""
Okay, I wonder how this would work for a number of instruments?

For this we need to build a system

A system is made up of subsystems - essentially stages in the process, and it needs data, and perhaps a configuration


The minimum subsystem you would have would be Rules - which is where you put trading rules
"""

from systems.forecasting import Rules, tradingRule

"""
We can create rules in a number of different ways

Note that to make our rule work it needs to have 
"""
our_rule=Rules(calc_ewmac_forecast)



"""
Another approach is to create a config file 
"""


"""
This isn't a very exciting config
"""


"""
Fortunately we don't have to build a system from scratch, we can use some pre-made versions

'easy-system' will ... (simpler than full_futures)
"""


system=full_futures_system(data, config)


ans=system.rawdata.smoothed_rolldown(instrument_code)
from syscore.objects import resolve_data_method
print(ans)
print(resolve_data_method(system,"rawdata.smoothed_rolldown")(instrument_code))

ans.plot()
show()

"""
Create raw and cross sectional data

Perhaps rather than a seperate step should be 'pulled / cached' as needed

This rather implies we have a datablob approach, and everything is do_stuff(datablob)

some stuff in datablob will be cached (raw data)

once datablob is saved it can be retreived and interrogated

perhaps we use this approach also for forecasts... etc through each stage.


General notes:

Need to be able to do quick and dirty stuff

The 'data' object once built can be pickled or json'd; as can the config object

config objects can be built from yaml

Now the actual 'system' is going to be a heiracrchal object that operates on data and config

That too can be json'd or pickled in.

When done it builds a 'simulation' object that incorporates the data, config and intermediate steps.

[also an 'optimal position writer' to write positions]


"""