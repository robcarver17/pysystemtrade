 

Here is a whistlestop tour of what pysystemtrade can currently do. You'll probably want to read the [users guide](userguide.md) after this.

## A simple trading rule

(code is [here](/examples/introduction/asimpletradingrule.py) )

As systematic traders we believe that the future will be at least a bit like the past. So first of all we need some past data. In principle past data can come from many places, but to begin with we'll get it from some pre-baked .csv files: 

```python
from sysdata.csvdata import csvFuturesData
data=csvFuturesData()
data
```

```
FuturesData object with 38 instruments
```

What instruments have we got?

```python
data.get_instrument_list()
```

```
['CORN', 'LEANHOG', 'LIVECOW', 'SOYBEAN', 'WHEAT', 'KR10', 'KR3', 'BOBL', 'BTP', 'BUND', 'OAT', 'SHATZ', 'US10', 'US2', 'US20', 'US5', 'V2X', 'VIX', 'KOSPI', 'AEX', 'CAC', 'SMI', 'NASDAQ', 'SP500', 'AUD', 'EUR', 'GBP', 'JPY', 'MXP', 'NZD', 'COPPER', 'GOLD', 'PALLAD', 'PLAT', 'CRUDE_W', 'GAS_US', 'EDOLLAR', 'EUROSTX']
```

And what kind of data can we get for them?

```python
data.get_instrument_price("EDOLLAR").tail(5)
```

```
              price
2015-04-16  97.9350
2015-04-17  97.9400
2015-04-20  97.9250
2015-04-21  97.9050
2015-04-22  97.8325
```

This is old data, but it's sufficient for playing with.  

*I'll update the data at some point, as well as including methods for you to get your own data*

*Technical note: This is the 'back-adjusted' price for the future, formed from stiching adjacent contracts together using the 'panama' method*

**data** objects behave a bit like dicts (though they don't formally inherit from them). So these both work:

```python
data.keys() ## equivalent to data.get_instrument_list
data['SP500'] ## equivalent to data.get_instrument_price
```

Price data is useful, but is there any other data available? For futures, yes, we can get the data we need to implement a carry rule:

```python
data.get_instrument_raw_carry_data("US10").tail(5)
```

```
                 PRICE       CARRY CARRY_CONTRACT PRICE_CONTRACT
2015-04-16  129.250000  129.656250         201509         201506
2015-04-17  129.437500  129.718750         201509         201506
2015-04-20  129.109375  129.562500         201509         201506
2015-04-21  129.000000  129.390625         201509         201506
2015-04-22         NaN  128.867188         201509         201506
```

Let's create a simple trading rule. 


```python

import pandas as pd
from syscore.algos import robust_vol_calc
from syscore.pdutils import divide_df_single_column

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
    
    return divide_df_single_column(raw_ewmac, vol)

```
Let's run it and look at the output

```python
instrument_code='EDOLLAR'
price=data.get_instrument_price(instrument_code)
ewmac=calc_ewmac_forecast(price, 4, 16)
ewmac.tail(5)

from matplotlib.pyplot import show
ewmac.plot()
show()
```

```
               price
2015-04-16  0.919245
2015-04-17  1.003627
2015-04-20  0.939076
2015-04-21  0.768698
2015-04-22  0.268149
```

Did we make any money?

```python
from syscore.accounting import pandl
account=pandl(price, forecast=ewmac)
account.stats()
```

```
[[('min', '-0.02341'),
  ('max', '0.0363'),
  ('median', '0'),
  ('mean', '5.227e-05'),
  ('std', '0.001847'),
  ('skew', '0.8685'),
  ('ann_daily_mean', '0.01338'),
  ('ann_daily_std', '0.02955'),
  ('sharpe', '0.4529'),
  ('sortino', '0.4986'),
  ('avg_drawdown', '-0.02341'),
  ('time_in_drawdown', '0.9782'),
  ('calmar', '0.155'),
  ('avg_return_to_drawdown', '0.5717'),
  ('avg_loss', '-0.001168'),
  ('avg_gain', '0.001216'),
  ('gaintolossratio', '1.041'),
  ('profitfactor', '1.12'),
  ('hitrate', '0.5183')],
 ('You can also plot:', ['rolling_ann_std', 'drawdown', 'curve']),
 ('You can also print:', ['weekly', 'monthly', 'annual'])]
```


Looks like we did. **account**, by the way inherits from a pandas data frame. Here are some other things we can do with it:

```python
account.sharpe() ## get the Sharpe Ratio (annualised), and any other statistic from stats
account.curve().plot() ## plot the cumulative account curve
account.drawdown().plot() ## see the drawdowns
account.weekly() ## weekly returns (also monthly, annual)
```


## A simple system

(code is [here](/examples/introduction/simplesystem.py) )

This is all very well, but what we probably want to do is build a trading **system** composed of several trading rules, and a few more instruments.

A system consists of some data (which we've already seen), a number of processing *stages*, and optionally a configuration to modify each of the stages behaves.

A full list of stages would include:

1. Preprocessing some raw data
2. Running some trading rules over it to generate forecasts
3. Scaling and capping those forecasts 
4. Combining forecasts together
5. Position sizing
6. Creating a portfolio of instruments
7. Working out the p&l

For now let's start with the simplest possible system, one which contains only a trading rules stage. Let's just setup our enviroment again:

```python
from sysdata.csvdata import csvFuturesData
data=csvFuturesData()

from systems.provided.example.rules import ewmac_forecast_with_defaults as ewmac
```

This is a slightly different version of the rule we defined before, which has default values for Lfast and Lslow. Now there are many ways to create a set of trading rules; here is the simplest:

```python
from systems.forecasting import Rules
my_rules=Rules(ewmac)
my_rules
```

```
{'rule0': TradingRule; function: <function ewmac_forecast_with_defaults at 0xb727fa4c>, data:  and other_args: }
```

This won't make much sense now, but bear with me (and don't worry if you get a different hexadecimal number). Suffice to say we've created a dict of trading rules with one element, which has been given the thrilling name of 'rule0'. Rule0 isn't especially meaningful, so let's come up with a better name:

```python
my_rules=Rules(dict(ewmac=ewmac))
my_rules
```

```
{'ewmac': TradingRule; function: <function ewmac_forecast_with_defaults at 0xb72bca4c>, data:  and other_args: }
```

The next stage is to create a system incorporating our **data** object, and the my_rules stage.

```python
from systems.basesystem import System
my_system=System([my_rules], data)
my_system
```

```
System with subsystems: rules
```

We can now get forecasts:

```python
my_system.rules.get_raw_forecast("EDOLLAR", "ewmac").tail(5)
```

```
               ewmac
2015-04-16  0.999120
2015-04-17  1.057726
2015-04-20  1.085446
2015-04-21  1.082781
2015-04-22  0.954941
```

This might be a good time to introduce a **config** object.

Configuration objects can be created by reading in files written in yaml, or directly from a dictionary. The former approach is useful for running live systems, or repeating a backtest. To make life easier let's just use the dictionary approach for now. 

```python
from sysdata.configdata import Config
my_config=Config(dict(trading_rules=dict(ewmac=ewmac)))
my_config
```

```
Config with elements: trading_rules
```

This next line of code will reproduce what we've already done, but rather than using **my_rules** we'll use an 'empty' Rules() stage, and let the config tell the system what to do.

```python
my_system=System([Rules()], data, my_config)
my_system.rules.get_raw_forecast("EDOLLAR", "ewmac").tail(5)
``` 

What about if we want more than one trading rule, say a couple of variations of the ewmac rule? To define two different flavours of ewmac we're going to need to learn a little bit more about trading rules. Remember when we had `my_rules=Rules(dict(ewmac=ewmac))`? Well this is an equivalent way of doing it:

```python
from systems.forecasting import TradingRule
ewmac_rule=TradingRule(ewmac)
my_rules=Rules(dict(ewmac=ewmac_rule))
ewmac_rule
```

```
TradingRule; function: <function ewmac_forecast_with_defaults at 0xb734ca4c>, data:  and other_args: 
```

Time to reveal what the mysterious object is. A **TradingRule** contains 3 elements - a function, a list of any data the function needs, and a dict of any other arguments that can be passed to the function. So the function is just the ewmac function that we imported earlier, and in this trivial case there is no data, and no arguments. Having no data is fine, because the code assumes that you'd normally want to pass the price of an instrument to a trading rule if you don't tell it otherwise. Furthermore on this occassion having no arguments is also no problem since the ewmac function we're using includes some defaults.

*If you're familiar with the concept of *args, **kwargs; `data` is a bit like *args - we always pass a list of positional arguments to `function`; and `other_args` are a bit like **kwargs - we always pass in a dict of named arguments to `function`*

There are a few different ways to define trading rules complete. I'll use a couple of different ones here:

```python
ewmac_8=TradingRule((ewmac, [], dict(Lfast=8, Lslow=32)))
ewmac_32=TradingRule(dict(function=ewmac, other_args=dict(Lfast=32, Lslow=128)))
my_rules=Rules(dict(ewmac8=ewmac_8, ewmac32=ewmac_32))
my_rules.trading_rules()['ewmac32']
```

```
TradingRule; function: <function ewmac_forecast_with_defaults at 0xb7252a4c>, data:  and other_args: Lfast, Lslow
```

We can do a similar thing with a config. 

Now these trading rules aren't producing forecasts that are correctly scaled (with an average absolute value of 10), and they don't have the cap of 20 that I recommend. To fix this we need to add another stage to our system. In future versions of this project we'll be able to estimate forecast scalars on a rolling out of sample basis; but for now we'll just use the fixed values from Appendix B of my book.

```python
from systems.forecast_scale_cap import ForecastScaleCapFixed

fcs=ForecastScaleCapFixed(forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65))
my_system=System([fcs, my_rules], data, my_config)
my_system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac32")
```

Again we could do this with a config change if we wanted.



## A pre-baked system

Let's now see how we might use a 'pre-baked' system, in this case the staunch systems trader example definied in chapter 15 of my book ["Systematic Trading"](http:/www.systematictrading.org).



You'll probably want to read the [users guide](userguide.md) after this.
