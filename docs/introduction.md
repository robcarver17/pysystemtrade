 

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

*I'll update the data at some point, as well as including methods for you to get your own data from different sources*

*Technical note: This is the 'back-adjusted' price for the future, formed from stiching adjacent contracts together using the 'panama' method*

`data` objects behave a bit like dicts (though they don't formally inherit from them). So these both work:

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
ewmac=calc_ewmac_forecast(price, 32, 128)
ewmac.tail(5)

from matplotlib.pyplot import show
ewmac.plot()
show()
```

```
               price
2015-04-16  3.742889
2015-04-17  3.918523
2015-04-20  4.062661
2015-04-21  4.179868
2015-04-22  4.041079
```

Did we make any money?

```python
from syscore.accounting import pandl
account=pandl(price, forecast=ewmac)
account.stats()
```

```
[[('min', '-0.07944'),
  ('max', '0.05662'),
  ('median', '0'),
  ('mean', '0.0001884'),
  ('std', '0.005823'),
  ('skew', '-0.8771'),
  ('ann_daily_mean', '0.04823'),
  ('ann_daily_std', '0.09317'),
  ('sharpe', '0.5177'),
  ('sortino', '0.5248'),
  ('avg_drawdown', '-0.1392'),
  ('time_in_drawdown', '0.9703'),
  ('calmar', '0.1221'),
  ('avg_return_to_drawdown', '0.3465'),
  ('avg_loss', '-0.003849'),
  ('avg_gain', '0.003871'),
  ('gaintolossratio', '1.006'),
  ('profitfactor', '1.135'),
  ('hitrate', '0.5302')],
 ('You can also plot:', ['rolling_ann_std', 'drawdown', 'curve']),
 ('You can also print:', ['weekly', 'monthly', 'annual'])]
```


Looks like we did make a few bucks. `account`, by the way inherits from a pandas data frame. Here are some other things we can do with it:

```python
account.sharpe() ## get the Sharpe Ratio (annualised), and any other statistic which is in the stats list
account.curve().plot() ## plot the cumulative account curve (equivalent to account.cumsum().plot() inicidentally)
account.drawdown().plot() ## see the drawdowns
account.weekly() ## weekly returns (also monthly, annual)
```


## A simple system

(code is [here](/examples/introduction/simplesystem.py) )

This is all very well, but what we probably want to do is build a trading **system** composed of several trading rules, and a few more instruments.

A system consists of some data (which we've already seen), a number of processing *stages*, and optionally a configuration to modify each of the stages behaves.

A full list of stages would include:

1. Preprocessing some raw data (which we don't cover in this introduction)
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

This is a slightly different version of the rule we defined before, which has default values for `Lfast` and `Lslow`. Now there are many ways to create a set of trading rules; here is the simplest:

```python
from systems.forecasting import Rules
my_rules=Rules(ewmac)
my_rules.trading_rules()
```

```
{'rule0': TradingRule; function: <function ewmac_forecast_with_defaults at 0xb727fa4c>, data:  and other_args: }
```

This won't make much sense now, but bear with me (and don't worry if you get a different hexadecimal number). Suffice to say we've created a dict of trading rules with one variation, which has been given the thrilling name of `rule0`. `rule0` isn't especially meaningful, so let's come up with a better name:

```python
my_rules=Rules(dict(ewmac=ewmac))
my_rules.trading_rules()
```

```
{'ewmac': TradingRule; function: <function ewmac_forecast_with_defaults at 0xb72bca4c>, data:  and other_args: }
```

The next stage is to create a system incorporating our `data` object, and the `my_rules` stage.

```python
from systems.basesystem import System
my_system=System([my_rules], data)
my_system
```

```
System with stages: rules
```

We can now get forecasts:

```python
my_system.rules.get_raw_forecast("EDOLLAR", "ewmac").tail(5)
```

```
               ewmac
2015-04-16  3.742889
2015-04-17  3.918523
2015-04-20  4.062661
2015-04-21  4.179868
2015-04-22  4.041079
```

This is exactly what we got in the simple example above; but with far more work. Don't worry, it will be worth it.

We'll see this pattern of `my_system...stage name...get_something()` a lot. The `Rules` object has become an attribute of the parent system, with name `rules`. Notice that the names used for each stage are fixed regardless of exactly what the stage class or instance is called, so we can always find what we need.

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

Time to reveal what the mysterious object is. A `TradingRule` contains 3 elements - a function, a list of any data the function needs, and a dict of any other arguments that can be passed to the function. So the function is just the `ewmac` function that we imported earlier, and in this trivial case there is no data, and no arguments. Having no data is fine, because the code assumes that you'd normally want to pass the price of an instrument to a trading rule if you don't tell it otherwise. Furthermore on this occassion having no arguments is also no problem since the ewmac function we're using includes some defaults.

*If you're familiar with the concept in python of args and kwargs; `data` is a bit like args - we always pass a list of positional arguments to `function`; and `other_args` are a bit like kwargs - we always pass in a dict of named arguments to `function`*

There are a few different ways to define trading rules completely. I'll use a couple of different ones here:

```python
ewmac_8=TradingRule((ewmac, [], dict(Lfast=8, Lslow=32))) ## as a tuple (function, data, other_args) notice the empty element in the middle
ewmac_32=TradingRule(dict(function=ewmac, other_args=dict(Lfast=32, Lslow=128)))  ## as a dict
my_rules=Rules(dict(ewmac8=ewmac_8, ewmac32=ewmac_32))
my_rules.trading_rules()['ewmac32']
```

```
TradingRule; function: <function ewmac_forecast_with_defaults at 0xb7252a4c>, data:  and other_args: Lfast, Lslow
```

Again, let's check that ewmac32 is the same as the ewmac we have before (it should be, since 32, 128 are the default arguments for the underlying trading rule function):

```python
my_system=System([my_rules], data)
my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5)
```

```
               ewmac
2015-04-16  3.742889
2015-04-17  3.918523
2015-04-20  4.062661
2015-04-21  4.179868
2015-04-22  4.041079
```


Now let's introduce the idea of **config** objects. A config or configuration object allows us to control the behaviour of the various stages in the system. 

Configuration objects can be created on the fly or by reading in files written in yaml (which we'll talk about below). A configuration object is just a collection of attributes. We create them interactively like so:

```python
from sysdata.configdata import Config
my_config=Config()
my_config
```

```
Config with elements: 
```

So far, not exciting. Let's see how we'd use a config to define our trading rules:

```python
empty_rules=Rules()
my_config.trading_rules=dict(ewmac8=ewmac_8, ewmac32=ewmac_32)
my_system=System([empty_rules], data, my_config)
```

Notice the differences from before:

1. We pass in an 'empty' instance of rules that contains no arguments
2. We create an element in config: trading_rules, that contains our dictionary of trading rules
3. The system uses the config.trading_rules

*Note if you'd passed the dict of trading rules into Rules()* **and** *into the config, only the former would be used*

Now these trading rules aren't producing forecasts that are correctly scaled (with an average absolute value of 10), and they don't have the cap of 20 that I recommend. In future versions of this project we'll be able to estimate forecast scalars on a rolling out of sample basis; but for now we'll just use the fixed values from Appendix B of my book ["Systematic Trading"](http:/www.systematictrading.org). To fix this we need to add another stage to our system: forecast scaling and capping. 


```python
my_config.forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65)

from systems.forecast_scale_cap import ForecastScaleCapFixed

fcs=ForecastScaleCapFixed()
my_system=System([fcs, empty_rules], data, my_config)
my_system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac32")
```

*Note that the order of stages in the list passed to `System([...], ...)` isn't relevant*


```
              ewmac32
2015-04-16   9.918656
2015-04-17  10.384086
2015-04-20  10.766051
2015-04-21  11.076651
2015-04-22  10.708858
```

*We didn't have to pass the forecast cap of 20.0, since the system was happy to use the default value (this is defined in the system defaults file, which the full [users guide](userguide.md) will tell you more about).*

Since we have two trading rule variations we're naturally going to want to combine them (chapter 8 of my book). For a very quick and dirty exercise running this code will use equal forecast weights across instruments, and use no diversification multiplier:

```python
from systems.forecast_combine import ForecastCombineFixed
combiner=ForecastCombineFixed()
my_system=System([fcs, empty_rules, combiner], data, my_config)
my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5)
```

```
WARNING: No forecast weights  - using equal weights of 0.5000 over all 2 trading rules in system
            comb_forecast
2015-04-16       9.162660
2015-04-17       9.668552
2015-04-20       9.907909
2015-04-21       9.906067
2015-04-22       8.842466
```


Let's come up with some arbitrary forecast weights and diversification multiplier for now:


```python
my_config.forecast_weights=dict(ewmac8=0.5, ewmac32=0.5)
my_config.forecast_div_multiplier=1.1
my_system=System([fcs, empty_rules, combiner], data, my_config)
my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5)
```


```
            comb_forecast
2015-04-16      10.078925
2015-04-17      10.635408
2015-04-20      10.898699
2015-04-21      10.896673
2015-04-22       9.726712
```

If you're working through my book you'd know the next stage is deciding what level of risk to target (chapter 9) and position sizing (chapter 10). 
Let's do the position scaling:

```python
from systems.positionsizing import PositionSizing
possizer=PositionSizing()

my_config.percentage_vol_target=25
my_config.notional_trading_capital=500000
my_config.base_currency="GBP"

my_system=System([ fcs, empty_rules, combiner, possizer], data, my_config)

my_system.positionSize.get_subsystem_position("EDOLLAR").tail(5)
```




```
            ss_position
2015-04-16    75.048813
2015-04-17    82.175489
2015-04-20    86.984346
2015-04-21    89.209027
2015-04-22    77.713056
```

We're almost there. The final stage we need to get positions is to combine everything into a portfolio (chapter 11). Again I'm going to make up some instrument weights, and diversification multiplier.

*Again if we couldn't be bothered, this would default to equal weights and 1.0 respectively*

```python
from systems.portfolio import PortfoliosFixed
portfolio=PortfoliosFixed()
my_config.instrument_weights=dict(US10=.1, EDOLLAR=.4, CORN=.3, SP500=.8)
my_config.instrument_div_multiplier=1.5
my_system=System([ fcs, empty_rules, combiner, possizer, portfolio], data, my_config)

my_system.portfolio.get_notional_position("EDOLLAR").tail(5)
```

```                 
                  pos
2015-04-16  45.029288
2015-04-17  49.305294
2015-04-20  52.190608
2015-04-21  53.525416
2015-04-22  46.627833
```

Although this is fine and dandy, we're probably going to be curious about whether this made money or not. So we'll need to add just one more stage, to count our virtual profits:

```python
from systems.account import Account
account=Account()
my_system=System([ fcs, empty_rules, combiner, possizer, portfolio, account], data, my_config)
profits=my_system.account.portfolio()
profits.stats()
```

```
FIX ME - OUTPUT GOES HERE
```

Once again we have the now familiar accounting object.


## Getting config from dictionaries and files

To speed things up you can also pass a dictionary to Config. To reproduce the setup we had above we'd make a dict like so:

```python
from sysdata.configdata import Config
my_config=Config(dict(trading_rules=dict(ewmac8=ewmac_8, ewmac32=ewmac_32), instrument_weights=dict(US10=.1, EDOLLAR=.4, CORN=.3, SP500=.2), instrument_div_multiplier=1.5, forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65), forecast_weights=dict(ewmac8=0.5, ewmac32=0.5), forecast_div_multiplier=1.1
,percentage_vol_target=25, notional_trading_capital=500000, base_currency="GBP"))
my_config
```

```
Config with elements: base_currency, forecast_div_multiplier, forecast_scalars, forecast_weights, instrument_div_multiplier, instrument_weights, notional_trading_capital, percentage_vol_target, trading_rules
```

Alternatively we could get the same result from reading a [yaml](http://pyyaml.org) file ( [this one to be precise](/systems/provided/example/simplesystemconfig.yaml) ). Don't worry if you're not familiar with yaml; it's just a nice way of creating nested dicts, lists and other python objects in plain text. Just be aware that indentations are important, just in like python.

```python
my_config=Config("systems.provided.example.simplesystemconfig.yaml")
```

(Notice we don't put filenames in; rather a python style reference within the project)

If you look at the YAML file you'll notice that the trading rule function has been specified as a string `systems.provided.example.rules.ewmac_forecast_with_defaults`. This is because we can't easily create a function in a YAML text file (*we can in theory; but it's quite a bit of work and creates a potential security risk*). Instead we specify where the relevant function can be found in the project directory structure. 

Similarly for the ewmac8 rule we've specified a data source `data.get_instrument_price` which points to system.data.get_instrument_price. This is the default, which is why we haven't needed to specify it before, and it isn't included in the specification for the ewmac32 rule. Equally we could specify any attribute and method within the system object, as long as it takes the argument `instrument_code`. We can also have a list of data inputs. This means you can configure almost any trading rule quite easily through configuration changes.



## A simple pre-baked system

Normally we wouldn't create a system by adding each stage manually (importing and creating long lists of stage objects). Instead you can use a 'pre baked' system, and then modify it as required. 

For example here is a pre-baked version of the previous example (code is [here](prebakedsystem.spy) ):

```python
from systems.provided.example.simplesystem import simplesystem
my_system=simplesystem()
my_system
```

```
System with stages: accounts, portfolio, positionSize, combForecast, forecastScaleCap, rules
```

Everything will now work as before:

```python
my_system.portfolio.get_notional_position("EDOLLAR").tail(5)
```



By default this has loaded the same data and read the config from the same yaml file. However we can also do this manually, allowing us to use new data and a modified config with a pre-baked system.

```python
from sysdata.configdata import Config
from sysdata.csvdata import csvFuturesData

my_config=Config("systems.provided.example.simplesystemconfig.yaml")
my_data=csvFuturesData()

## I could change my_config, and my_data here if I wanted to
my_system=simplesystem(config=my_config, data=my_data)
```

For the vast majority of the time this will be how you create new systems.


## A complete pre-baked system

Let's now see how we might use another 'pre-baked' system, in this case the staunch systems trader example definied in chapter 15 of my book. Here again we default to using csv data.

(Code is [here](prebakedsystem.spy) )

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
system.portfolio.get_notional_position("EUROSTX").tail(5)
```

```
                 pos
2015-04-16  2.929976
2015-04-17  2.038499
2015-04-20  1.897126
2015-04-21  1.981541
2015-04-22  2.119637
```

It's worth looking at the config for this system [here](/systems/futures/futuresconfig.yaml), and comparing it to what you see in chapter 15.

You'll probably want to read the [users guide](userguide.md) next.
