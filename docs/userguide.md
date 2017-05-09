
This guide is divided into four parts. The first ['How do I?'](#how_do_i) explains how to do many common tasks. The second part ['Guide'](#guide) details the relevant parts of the code, and explains how to modify or create new parts. The third part ['Processes'](#Processes) discusses certain processes that cut across multiple parts of the code in more detail. The final part ['Reference'](#reference) includes lists of methods and parameters.


<a name="how_do_i">
</a>

# How do I?

## How do I.... Experiment with a single trading rule and instrument

Although the project is intended mainly for working with trading systems, it's possible to do some limited experimentation without building a system. See [the introduction](introduction.md) for an example.

## How do I....Create a standard futures backtest

This creates the staunch systems trader example defined in chapter 15 of my book, using the csv data that is provided, and gives you the position in the Eurodollar market:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
system.portfolio.get_notional_position("EDOLLAR")
```
See [standard futures system](#futures_system) for more.


## How do I....Create a futures backtest which estimates parameters

This creates the staunch systems trader example defined in chapter 15 of my book, using the csv data that is provided, and estimates forecast scalars, instrument and forecast weights, and instrument and forecast diversification multipliers:

```python
from systems.provided.futures_chapter15.estimatedsystem import futures_system
system=futures_system()
system.set_logging_level("on")
system.portfolio.get_notional_position("EDOLLAR")
```

See [estimated futures system](#futures_system).



## How do I....See intermediate results from a backtest

This will give you the raw forecast (before scaling and capping) of one of the EWMAC rules for Eurodollar futures in the standard futures backtest:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
system.rules.get_raw_forecast("EDOLLAR", "ewmac64_256")
```

For a complete list of possible intermediate results, use `print(system)` to see the names of each stage, and then `stage_name.methods()`. Or see [this table](#table_system_stage_methods) and look for rows marked with **D** for diagnostic. Alternatively type `system` to get a list of stages, and `system.stagename.methods()` to get a list of methods for a stage (insert the name of the stage, not stagename).


## How do I....See how profitable a backtest was

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
system.accounts.portfolio().stats() ## see some statistics
system.accounts.portfolio().curve().plot() ## plot an account curve
system.accounts.portfolio().percent().curve().plot() ## plot an account curve in percentage terms
system.accounts.pandl_for_instrument("US10").percent().stats() ## produce % statistics for a 10 year bond
system.accounts.pandl_for_instrument_forecast("EDOLLAR", "carry").sharpe() ## Sharpe for a specific trading rule variation
```

For more information on what statistics are available, see the [relevant guide section](#standard_accounts_stage).


 
<a name="change_backtest_parameters">
</a>

## How do I....Change backtest parameters

The backtest looks for its configuration information in the following places:

1. Elements in the configuration object
2. If not found, in: Project defaults 

Configuration objects can be loaded from [yaml](http://pyyaml.org/) files, or created with a dictionary. This suggests that you can modify the systems behaviour in any of the following ways:

1. Change or create a configuration yaml file, read it in, and create a new system
2. Change a configuration object in memory, and create a new system with it.
3. Change a configuration object within an existing system (advanced)
4. Change the project defaults (definitely not recommended)

For a list of all possible configuration options, see [this table](#Configuration_options).

If you use options 2 or 3, you can [save the config](#save_config) to a yaml file.

### Option 1: Change the configuration file

Configurations in this project are stored in [yaml](http://pyyaml.org) files. Don't worry if you're not familiar with yaml; it's just a nice way of creating nested dicts, lists and other python objects in plain text. Just be aware that indentations are important, just in like python, to create nesting.

You can make a new config file by copying this [one](/systems/provided/futures_chapter15/futuresconfig.yaml), and modifying it. Best practice is to save this as `pysystemtrade/private/this_system_name/config.yaml` (you'll need to create a couple of directories first).

You should then create a new system which points to the new config file:

```python
from sysdata.configdata import Config
from systems.provided.futures_chapter15.basesystem import futures_system

my_config=Config("private.this_system_name.config.yaml"))
system=futures_system(config=my_config)
```

### Option 2: Change the configuration object; create a new system

We can also modify a configuration object from a loaded system directly, and then create a new system with it:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
new_config=system.config

new_idm=1.1 ## new IDM

new_config.instrument_div_multiplier=new_idm

## Heres an example of how you'd change a nested parameter
## If the element doesn't yet exist in your config:

system.config.volatility_calculation=dict(days=20)

## If it does exist:
system.config.volatility_calculation['days']=20


system=futures_system(config=new_config)
```

This is useful if you're experimenting interactively 'on the fly'.


### Option 3: Change the configuration object within an existing system (not recommended - advanced)

If you opt for (3) you will need to understand about [system caching](#caching) and [how defaults are handled](#defaults_how). To modify the configuration object in the system directly:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()

## Anything we do with the system may well be cached and will need to be cleared before it sees the new value...


new_idm=1.1 ## new IDM
system.config.instrument_div_multiplier=new_idm

## If we change anything that is nested, we need to change just one element to avoid clearing the defaults:
# So, do this:
system.config.volatility_calculation['days']=20

# Do NOT do this - it will wipe out all the other elements in the volatility_calculation dictionary:
# system.config.volatility_calculation=dict(days=20)


## The config is updated, but to reiterate anything that uses it will need to be cleared from the cache
```

Because we don't create a new system and have to recalculate everything from scratch, this can be useful for testing isolated changes to the system **if** you know what you're doing.

### Option 4: Change the project defaults (definitely not recommended)

I don't recommend changing the defaults - a lot of tests will fail for a start - but should you want to more information is given [here](#defaults).


## How do I....Run a backtest on a different set of instruments

Fixed instrument weights: You need to change the instrument weights in the configuration. Only instruments with weights have positions produced for them. 
Estimated instrument weights: You need to change the instruments section of the configuration.

There are two easy ways to do this - change the config file, or the config object already in the system (for more on changing config parameters see ['change backtest parameters'](#change_backtest_parameters) ). You also need to ensure that you have the data you need for any new instruments. See ['use my own data'](#create_my_own_data) below.


### Change instruments: Change the configuration file

You should make a new config file by copying this [one](/systems/provided/futures_chapter15/futuresconfig.yaml). Best practice is to save this as `pysystemtrade/private/this_system_name/config.yaml` (you'll need to create this directory).

For fixed weights, you can then change this section of the config:

```
instrument_weights:
    EDOLLAR: 0.117
    US10: 0.117
    EUROSTX: 0.20
    V2X: 0.098
    MXP: 0.233
    CORN: 0.233
instrument_div_multiplier: 1.89
```

You may also have to change the forecast_weights, if they're instrument specific:

```
forecast_weights:
   EDOLLAR:
     ewmac16_64: 0.21
     ewmac32_128: 0.08
     ewmac64_256: 0.21
     carry: 0.50
```


*At this stage you'd also need to recalculate the diversification multiplier (see chapter 11 of my book). See [estimating the forecast diversification multiplier](#divmult).

For estimated instrument weights you'd change this section:

```
instruments: ["EDOLLAR", "US10", "EUROSTX", "V2X", "MXP", "CORN"]
```

(The IDM will be re-estimated automatically)

You may also need to change this section, if you have different rules for each instrument:

```
rule_variations:
     EDOLLAR: ['ewmac16_64','ewmac32_128', 'ewmac64_256', 'carry']
```

You should then create a new system which points to the new config file:

```python
from sysdata.configdata import Config

my_config=Config("private.this_system_name.config.yaml")

from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system(config=my_config)
```

### Change instruments: Change the configuration object

We can also modify the configuration object in the system directly:

For fixed weights:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
new_config=system.config

new_weights=dict(SP500=0.5, KR10=0.5) ## create new weights
new_idm=1.1 ## new IDM

new_config.instrument_weights=new_weights
new_config.instrument_div_multiplier=new_idm

system=futures_system(config=new_config)

```

For estimated weights:

```python
from systems.provided.futures_chapter15.estimatedsystem import futures_system
system=futures_system()
new_config=system.config

new_config.instruments=["SP500", "KR10"]

del(new_config.rule_variations) ## means all instruments will use all trading rules

# this stage is optional if we want to give different instruments different sets of rules
new_config.rule_variations=dict(SP500=['ewmac16_64','carry'], KR10=['ewmac32_128', 'ewmac64_256', 'carry'])

system=futures_system(config=new_config)

```


<a name="how_do_i_write_rules">
</a>

## How do I....Create my own trading rule

At some point you should read the relevant guide section ['rules'](#TradingRules) as there is much more to this subject than I will explain briefly here.


### Writing the function


A trading rule consists of:

- a function
- some data (specified as positional arguments) 
- some optional control arguments (specified as key word arguments)


So the function must be something like these:

```python
def trading_rule_function(data1):
   ## do something with data1

def trading_rule_function(data1, arg1=default_value):
   ## do something with data1
   ## controlled by value of arg1

def trading_rule_function(data1, data2):
   ## do something with data1 and data2

def trading_rule_function(data1, data2, arg1=default_value, arg2=default_value):
   ## do something with data1
   ## controlled by value of arg1 and arg2

```
... and so on.

Functions must return a Tx1 pandas dataframe. 
 
### Adding the trading rule to a configuration

We can either modify the YAML file or the configuration object we've already loaded into memory. See ['changing backtest parameters'](change_backtest_parameters) for more details. If you want to use a YAML file you need to first save the function into a .py module, so it can be referenced by a string (we can also use this method for a config object in memory).

For example the rule imported like this:

```python
from systems.futures.rules import ewmac
```

Can also be referenced like so: `systems.futures.rules.ewmac`

Also note that the list of data for the rule will also be in the form of string references to methods in the system object. So for example to get the daily price we'd use the method `system.rawdata.daily_prices(instrument_code)` (for a list of all the data methods in a system see [stage methods](#table_system_stage_methods) or type `system.rawdata.methods()` and `system.rawdata.methods()). In the trading rule specification this would be shown as "rawdata.daily_prices". 

If no data is included, then the system will default to passing a single data item - the price of the instrument. Finally if any or all the `other_arg` keyword arguments are missing then the function will use its own defaults.
 
At this stage we can also remove any trading rules that we don't want. We also ought to modify the forecast scalars (See [forecast scale estimation](#scalar_estimate]), forecast weights and probably the forecast diversification multiplier ( see [estimating the forecast diversification multiplier](#divmult)). If you're estimating weights and scalars (i.e. in the pre-baked estimated futures system provided) this will be automatic.

*If you're using fixed values (the default) then if you don't include a forecast scalar for the rule, it will use a value of 1.0. If you don't include forecast weights in your config then the system will default to equally weighting. But if you include forecast weights, but miss out the new rule, then it won't be used to calculate the combined forecast.*

Here's an example for a new variation of the EWMAC rule. This rule uses two types of data - the price (stitched for futures), and a precalculated estimate of volatility.

YAML: (example) 
```
trading_rules:
  .... existing rules ...
  new_rule:
     function: systems.futures.rules.ewmac
     data:
         - "rawdata.daily_prices"
         - "rawdata.daily_returns_volatility"
     other_args: 
         Lfast: 10
         Lslow: 40
#
#
## Following section is for fixed scalars, weights and div. multiplier:
#
forecast_scalars: 
  ..... existing rules ....
  new_rule=10.6
#
forecast_weights:
  .... existing rules ...
  new_rule=0.10
#
forecast_div_multiplier=1.5
#
#
## Alternatively if you're estimating these quantities use this section:
#
use_forecast_weight_estimates: True
use_forecast_scale_estimates: True
use_forecast_div_mult_estimates: True

rule_variations:
     EDOLLAR: ['ewmac16_64','ewmac32_128', 'ewmac64_256', 'new_rule']
#
# OR if all variations are the same for all instruments
#
rule_variations: ['ewmac16_64','ewmac32_128', 'ewmac64_256', 'new_rule']
#
```



Python (example - assuming we already have a config object loaded to modify)

```python
from systems.forecasting import TradingRule

# method 1
new_rule=TradingRule(dict(function="systems.futures.rules.ewmac", data=["rawdata.daily_prices", "rawdata.daily_returns_volatility"], other_args=dict(Lfast=10, Lslow=40)))

# method 2 - good for functions created on the fly
from systems.futures.rules import ewmac
new_rule=TradingRule(dict(function=ewmac, data=["rawdata.daily_prices", "rawdata.daily_returns_volatility"], other_args=dict(Lfast=10, Lslow=40)))

## both methods - modify the configuration
config.trading_rules['new_rule']=new_rule

## If you're using fixed weights and scalars

config.forecast_scalars['new_rule']=7.0
config.forecast_weights=dict(.... , new_rule=0.10)  ## all existing forecast weights will need to be updated
config.forecast_div_multiplier=1.5

## If you're using estimates

config.use_forecast_scale_estimates=True
config.use_forecast_weight_estimates=True
use_forecast_div_mult_estimates: True

config.rule_variations=['ewmac16_64','ewmac32_128', 'ewmac64_256', 'new_rule']
# or to specify different variations for different instruments
config.rule_variations=dict(SP500=['ewmac16_64','ewmac32_128', 'ewmac64_256', 'new_rule'], US10 =['new_rule',....)
```

Once we've got the new config, by which ever method, we just use it in our system, eg:

```python
## put into a new system

from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system(config=config)
```


<a name="create_my_own_data">
</a>

## How do I....Use different data or instruments

Currently the only data that is supported is .csv files for futures stitched prices (eg US10_price.csv), fx (eg AUDUSDfx.csv), and futures specific (eg AEX_carrydata.csv), data. A set of data is provided in [pysystem/sys/data/legacycsv](/sysdata/legacycsv). It's my intention to update this and try to keep it reasonably current with each release.

You can update that data, if you wish. Be careful to save it as a .csv with the right formatting, or pandas will complain. Check that a file is correctly formatted like so:

```python
import pandas as pd
test=pd.read_csv("filename.csv")
test
```
You can also add new files for new instruments. Be sure to keep the file format and header names consistent.

You can create your own directory for .csv files such as `pysystemtrade/private/system_name/data/'. Here is how you'd use it:

```python
from sysdata.csvdata import csvFuturesData
from systems.provided.futures_chapter15.basesystem import futures_system

data=csvFuturesData("private.system_name.data"))
system=futures_system(data=data)
```
Notice that we use python style "." internal references within a project, we don't give actual path names.

There is more detail about using .csv files [here](#csv).

If you want to get data from a different place (eg a database, yahoo finance, broker, quandl...) you'll need to [create your own Data object](#create_data). Note that I intend to add support for sqlite database, HDF5, Interactive brokers and quandl data in the future.

If you want to use a different set of data values (eg equity EP ratios, interest rates...) you'll need to [create your own Data object](#create_data).


## How do I... Save my work

To remain organised it's good practice to save any work into a directory like `pysystemtrade/private/this_system_name/` (you'll need to create a couple of directories first). If you plan to contribute to github, just be careful to avoid adding 'private' to your commit ( [you may want to read this](https://24ways.org/2013/keeping-parts-of-your-codebase-private-on-github/) ). 

You can save the contents of a system cache to avoid having to redo calculations when you come to work on the system again (but you might want to read about [system caching and pickling](#caching) before you reload them). 

```python
from systems.provided.futures_chapter15.basesystem import futures_system

system = futures_system(log_level="on")
system.accounts.portfolio().sharpe() ## does a whole bunch of calculations that will be saved in the cache

system.cache.pickle("private.this_system_name.system.pck") ## use any file extension you like

## In a new session
from systems.provided.futures_chapter15.basesystem import futures_system

system = futures_system(log_level="on")
system.cache.unpickle("private.this_system_name.system.pck")

## this will run much faster and reuse previous calculations
# only complex accounting p&l objects aren't saved in the cache
system.accounts.portfolio().sharpe()

```

You can also save a config object into a yaml file - see [saving configuration](#save_config).


<a name="guide">
</a>

# Guide


The guide section explains in more detail how each part of the system works: 

1. [Data](#data) objects
2. [Config](#config) objects and yaml files
3. [System](#system) objects, 
4. [Stages](#stage_general) within a system. 

Each section is split into parts that get progressively trickier; varying from using the standard objects that are supplied up to writing your own.

<a name="data">
</a>

## Data

A data object is used to feed data into a system. Data objects work with a particular **kind** of data (normally asset class specific, eg futures) from a particular **source** (for example .csv files, databases and so on).

### Using the standard data objects

Only one kind of specific data object is provided with the system in the current version - `csvFutures`. 

#### Generic data objects

You can get use data objects directly:

*These commands will work with all data objects - the `csvFutures` version is used as an example.*

```python
from sysdata.csvdata import csvFuturesData

data=csvFuturesData()

## getting data out
data.methods() ## list of methods

data.get_raw_price(instrument_code)
data[instrument_code] ## does the same thing as get_raw_price

data.get_instrument_list()
data.keys() ## also gets the instrument list

data.get_value_of_block_price_move(instrument_code)
data.get_instrument_currency(instrument_code)
data.get_fx_for_instrument(instrument_code, base_currency) # get fx rate between instrument currency and base currency

```

Or within a system:

```python
## using with a system
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system(data=data)

system.data.get_instrument_currency(instrument_code) # and so on
```

(Note that when specifying a data item within a trading [rule](#rules) you should omit the system eg `data.get_raw_price`)



<a name="csvdata">
</a>

#### The [csvFuturesData](/sysdata/csvdata.py) object

The `csvFuturesData` object works like this:

```python
from sysdata.csvdata import csvFuturesData

## with the default folder
data=csvFuturesData()

## OR with a particular folder
data=csvFuturesData("private.system_name.data")  ## assuming you've created data in pysystemtrade/private/system_name/data/

## getting data out
data.methods() ## will list any extra methods
data.get_instrument_raw_carry_data(instrument_code) ## specific data for futures

## using with a system
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system(data=data)
system.data.get_instrument_raw_carry_data(instrument_code)
```

The pathname must contain .csv files of the following four types (where code is the instrument_code):

1. Static data- `instrument_config.csv` headings: Instrument, Pointsize, AssetClass, Currency
2. Price data- `code_price.csv` (eg SP500_price.csv) headings: DATETIME, PRICE
3. Futures data - `code_carrydata.csv` (eg AEX_carrydata.csv): headings: DATETIME, PRICE,CARRY,CARRY_CONTRACT PRICE_CONTRACT
4. Currency data - `ccy1ccy2fx.csv` (eg AUDUSDfx.csv) headings: DATETIME, FXRATE
5. Cost data - 'costs_analysis.csv' headings: Instrument, Slippage, PerBlock, Percentage, PerTrade. See ['costs'](#costs) for more detail.

DATETIME should be something that `pandas.to_datetime` can parse. Note that the price in (2) is the continously stitched price (see [volatility calculation](#vol_calc) ), whereas the price in (3) is the price of the contract we're currently trading. 

At a minimum we need to have a currency file for each instrument's currency against the default (defined as "USD"); and for the currency of the account we're trading in (i.e. for a UK investor you'd need a `GBPUSDfx.csv` file). If cross rate files are available they will be used; otherwise the USD rates will be used to work out implied cross rates.

See [pysystem/sysdata/legacycsv](/sysdata/legacycsv) for files you can modify.


### Creating your own data objects

You should be familiar with the python object orientated idiom before reading this section.

The [`Data()`](/sysdata/data) object is the base class for data. From that we inherit data type specific classes such as the [`FuturesData`](/sysdata/futuresdata) object. These in turn are inherited from for specific data sources, such as [`csvFuturesData`](/sysdata/csvdata).

So the FuturesData object is defined `class FuturesData(Data)`, and csvFuturesData as `class csvFuturesData(FuturesData)`. It would also be helpful if this naming scheme was adhered to: sourceTypeData. For example if we had some single equity data stored in a database we'd do `class EquitiesData(Data)`, and `class dbEquitiesData(EquitiesData)`.

So, you should consider whether you need a new type of data, a new source of data or both. You may also wish to extend an existing class. For example if you wished to add some fundamental data for futures you might define: `class FundamentalFutures(FuturesData)`. You'd then need to inherit from that for a specific source.

This might seem a hassle, and it's tempting to skip and just inherit from `Data()` directly, however once your system is up and running it is very convenient to have the possibility of multiple data sources and this process ensures they keep a consistent API for a given data type.

#### The Data() class

Methods that you'll probably want to override:

- `get_raw_price` Returns Tx1 pandas data frame
- `get_instrument_list` Returns list of str
- `get_value_of_block_price_move` Returns float
- 'get_raw_cost_data' Returns a dict cost data
- `get_instrument_currency`: Returns str
- `_get_fx_data(currency1, currency2)`  Returns Tx1 pandas data frame of exchange rates

You should not override `get_fx_for_instrument`, or any of the other private fx related methods. Once you've created a `_get_fx_data method`, then the methods in the `Data` base class will interact to give the correct fx rate when external objects call `get_fx_for_instrument()`; handling cross rates and working them out as needed.

Neither should you override 'daily_prices'.
 
Finally data methods should not do any caching. [Caching](#caching) is done within the system class.

#### Creating a new type of data (or extending an existing one)

Here is an annotated extract of the `FuturesData` class illustrating how it extends `Data`:

```python

class FuturesData(Data):

    def get_instrument_raw_carry_data(self, instrument_code):
	### a method to get data specific for this asset class
        ### normally we'd override this in the inherited method for a particular data source
        ###

        raise Exception("You have created a FuturesData() object; you probably need to replace this method to do anything useful")



    def __repr__(self):
        ### modify this method so we can tell what type of data we have
        return "FuturesData object with %d instruments" % len(self.get_instrument_list())    
```

#### Creating a new data source (or extending an existing one)

Here is an annotated extract of the `csvFuturesData` class, illustrating how it extends `FuturesData` and `Data` for a specific source:

```python
class csvFuturesData(FuturesData):
    """
        Get futures specific data from legacy csv files
        
        Extends the FuturesData class for a specific data source 
    
    """
    
    def __init__(self, datapath=None):
        
        if datapath is None:            
            datapath=get_pathname_for_package(LEGACY_DATA_MODULE, LEGACY_DATA_DIR)

        """
        Most Data objects that read data from a specific place have a 'source' of some kind
        Here it's a directory
	We need to store it for future reference
        """
        setattr(self, "_datapath", datapath)
    
    
    def get_raw_price(self, instrument_code):
        """
        Get instrument price. Overrides Data() method
        """

        ### This method will get the instrument price from self._datapath, for a specific 

    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

	Overrides FuturesData method
        """

    def _get_instrument_data(self):
        """
        Get a data frame of interesting information about instruments
        Private method used by other methods wanting static data
        """

    def get_instrument_list(self):
        """
        list of instruments in this data set. Overrides Data() method
        """


    def get_value_of_block_price_move(self, instrument_code):
        """
        How much is a $1 move worth in value terms?
        Overrides Data() method
        """
        
    def get_instrument_currency(self, instrument_code):
        """
        What is the currency that this instrument is priced in?
        Overrides Data() method
        """

        
    def _get_fx_data(self, currency1, currency2):
        ##Overrides Data() method
	## Note that we don't include any other fx methods here; the one's in the data class should do just fine
```

<a name="config">
</a>

## Configuration

Configuration (`config`) objects determine how a system behaves. Configuration objects are very simple; they have attributes which contain either parameters, or nested groups of parameters.

### Creating a configuration object

There are three main ways to create a configuration object:

1. Interactively from a dictionary
2. By pulling in a YAML file
3. From a 'pre-baked' system
4. By joining together multiple configurations in a list

#### 1) Creating a configuration object with a dictionary

```python
from sysdata.configdata import Config

my_config_dict=dict(optionone=1, optiontwo=dict(a=3.0, b="beta", c=["a", "b"]), optionthree=[1.0, 2.0])
my_config=Config(my_config_dict)
```

There are no restrictions on what is nested in the dictionary, but if you include arbitrary items like the above they won't be very useful!. The section on [configuration options](#Configuration_options) explains what configuration options would be used by a system.

#### 2) Creating a configuration object from a file

This simple file will reproduce the useless config we get from a dictionary in the example above.

```
optionone: 1
optiontwo:
   a: 3.0
   b: 
        - "a"
        - "b"
optionthree:
   - 1.0
   - 2.0
```

Note that as with python the indentation in a yaml file shows how things are nested. If you want to learn more about yaml check [this out.](http://pyyaml.org/wiki/PyYAMLDocumentation#YAMLsyntax).

```python
from sysdata.configdata import Config
my_config=Config("private.filename.yaml") ## assuming the file is in "pysystemtrade/private/filename.yaml"
```

In theory there are no restrictions on what is nested in the dictionary (but the top level must be a dict); although it is easier to use str, float, int, lists and dicts, and the standard project code only requires those (if you're a PyYAML expert you can do other python objects like tuples, but it won't be pretty).

You should respect the structure of the config with respect to nesting, as otherwise [the defaults](#defaults_how) won't be properly filled in. 

The section on [configuration options](#Configuration_options) explains what configuration options are available.


#### 3) Creating a configuration object from a pre-baked system

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
new_config=system.config
```

Under the hood this is effectively getting a configuration from a .yaml file - [this one](/systems/provided/futures_chapter15/futuresconfig.yaml).

Configs created in this way will include all [the defaults populated](#defaults_how).


#### 4) Creating a configuration object from a list

We can also pass a list into `Config()`, where each item of the list contains a dict or filename. For example we could do this with the simple filename example above:

```python
from sysdata.configdata import Config

my_config_dict=dict(optionfour=1, optionfive=dict(one=1, two=2.0))
my_config=Config(["filename.yaml", my_config_dict])
```

Note that if there are overlapping keynames, then those in latter parts of the list of configs will override earlier versions. 

This can be useful if, for example, we wanted to change the instrument weights 'on the fly' but keep the rest of the configuration unchanged.

<a name="defaults">
</a>

### Project defaults

Many (but not all) configuration parameters have defaults which are used by the system if the parameters are not in the object. These can be found in the [defaults.yaml file](/systems/provided/defaults.yaml). The section on [configuration options](#Configuration_options) explains what the defaults are, and where they are used.

I recommend that you do not change these defaults. It's better to use the settings you want in each system configuration file. 

<a name="config_function_defaults">
</a>

#### Handling defaults when you change certain functions

In certain places you can change the function used to do a particular calculation, eg volatility estimation (This does *not* include trading rules - the way we change the functions for these is quite different). This is straightforward if you're going to use the same arguments as the original argument. However if you change the arguments you'll need to change the project defaults .yaml file. I recommend keeping the original parameters, and adding new ones with different names, to avoid accidentally breaking the system.


<a name="defaults_how">
</a>

#### How the defaults work


When added to a system the config class fills in parameters that are missing from the original config object, but are present in the default .yaml file. For example if forecast_scalar is missing from the config, then the default value of 1.0 will be used. This works in a similar way for top level config items that are lists, str, int and float. 

This will also happen if you miss anything from a dict within the config (eg if `config.forecast_div_mult_estimate` is a dict, then any keys present in this dict in the default .yaml, but not in the config will be added). Finally it will work for nested dicts, eg if any keys are missing from `config.instrument_weight_estimate['correlation_estimate']` then they'll filled in from the default file. If something is a dict, or a nested dict, in the config but not in the default (or vice versa) then values won't be replaced and bad things could happen. It's better to keep your config files, and the default file, with matching structures. Again this is a good argument for adding new parameters, and retaining the original ones.

This stops at two levels, and only works for dicts and nested dicts.

Note this means that the config before, and after, it goes into a system object will probably be different; the latter will be populated with defaults.

```python
from sysdata.configdata import Config
my_config=Config()
print(my_config) ## empty config
```

```
 Config with elements: 
```

Now within a system:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system(config=my_config)

print(system.config) ## full of defaults. 
print(my_config) ## same object
```

```
 Config with elements: average_absolute_forecast, base_currency, buffer_method, buffer_size, buffer_trade_to_edge, forecast_cap, forecast_correlation_estimate, forecast_div_mult_estimate, forecast_div_multiplier, forecast_scalar, forecast_scalar_estimate, forecast_weight_estimate, instrument_correlation_estimate, instrument_div_mult_estimate, instrument_div_multiplier, instrument_weight_estimate, notional_trading_capital, percentage_vol_target, use_SR_costs, use_forecast_scale_estimates, use_forecast_weight_estimates, use_instrument_weight_estimates, volatility_calculation
```

Note this isn't enough for a working trading system as trading rules aren't populated by the defaults:


```python
system.accounts.portfolio()
```

```
# deleted full error trace
Exception: A system config needs to include trading_rules, unless rules are passed when object created
```


### Viewing configuration parameters

Regardless of whether we create the dictionary using a yaml file or interactively, we'll end up with a dictionary. The keys in the top level dictionary will become attributes of the config. We can then use dictionary keys or list positions to access any nested data. For example using the simple config above:

```python
my_config.optionone
my_config.optiontwo['a']
my_config.optionthree[0]
```


### Modifying configuration parameters

It's equally straightforward to modify a config. For example using the simple config above:

```python
my_config.optionone=1.0
my_config.optiontwo['d']=5.0
my_config.optionthree.append(6.3)
```

You can also add new top level configuration items:

```python
my_config.optionfour=20.0
setattr(my_config, "optionfour", 20.0) ## if you prefer
```

Or remove them:

```python
del(my_config.optionone)
```

With real configs you need to be careful with nested parameters:


```python
config.instrument_div_multiplier=1.1 ## not nested, no problem

## Heres an example of how you'd change a nested parameter
## If the element doesn't yet exist in your config
## If the element did exist, then obviously doing this would overwrite all other parameters in the config

config.volatility_calculation=dict(days=20)

## If it does exist you can do this instead:
config.volatility_calculation['days']=20
```

This is especially true if you're changing the config within a system, which will already include all the defaults:

```python
system.config.instrument_div_multiplier=1.1 ## not nested, no problem

## If we change anything that is nested, we need to change just one element to avoid clearing the defaults:
# So, do this:
system.config.volatility_calculation['days']=20

# Do NOT do this:
# system.config.volatility_calculation=dict(days=20)
```


### Using configuration in a system

Once we're happy with our configuration we can use it in a system:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system(config=my_config)
```
Note it's only when a config is included in a system that the defaults are populated.


### Including your own configuration options

If you develop your own stages or modify existing ones you might want to include new configuration options. Here's what your code should do:


```python

## Assuming your config item is called my_config_item; in the relevant method:

	parameter=system.config.my_config_item

	## You can also use nested configuration items, eg dict keyed by instrument_code (or nested lists)
	parameter=system.config.my_config_dict[instrument_code]

	## Lists also work. 

	parameter=system.config.my_config_list[1]

	## (Note: it's possible to do tuples, but the YAML is quite messy. So I don't encourage it.)
        

```

You would then need to add the following kind of thing to your config file:

```
my_config_item: "ni"
my_config_dict:
   US10: 45.0
   US5: 0.10
my_config_list:
   - "first item"
   - "second item"
```

Similarly if you wanted to use project defaults for your new parameters you'll also need to include them in the [defaults.yaml file](/systems/provided/defaults.yaml). Make sure you understand [how the defaults work](#defaults_how).


<a name="save_config">
</a>

### Saving configurations

You can also save a config object into a yaml file:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
import yaml
from syscore.fileutils import get_filename_for_package

system=futures_system()
my_config=system.config

## make some changes to my_config here

filename=get_filename_for_package("private.this_system_name.config.yaml")

with open(filename, 'w') as outfile:
    outfile.write( yaml.dump(my_config, default_flow_style=True) )
```

This is useful if you've been playing with a backtest configuration, and want to record the changes you've made. Note this will save trading rule functions as functions; this may not work and it will also be ugly. So you should use strings to define rule functions (see [rules](#rules) for more information)

A future version of this project will allow you to save the final optimised weights for instruments and forecasts into fixed weights for live trading.

### Modifying the configuration class

It shouldn't be neccessary to modify the configuration class since it's deliberately lightweight and flexible.

<a name="system">
</a>

## System

An instance of a system object consists of a number of **stages**, some **data**, and normally a **config** object.


### Pre-baked systems

We can create a system from an existing 'pre-baked system'. These include a ready made set of data, a list of stages, and a config.

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
```

We can override what's provided, and include our own data, and / or configuration, in such a system:

```python
system=futures_system(data=my_data)
system=futures_system(config=my_config)
system=futures_system(data=my_data, config=my_config)
```

Finally we can also create our own [trading rules object](#rules), and pass that in. This is useful for interactive model development. If for example we've just written a new rule on the fly:

```python
my_rules=dict(rule=a_new_rule) 
system=futures_system(trading_rules=my_rules) ## we probably need a new configuration as well here if we're using fixed forecast weights
```


<a name="futures_system">
</a>

#### [Futures system for chapter 15](/systems/provided/futures_chapter15/basesystem.py)

This system implements the framework in chapter 15 of my book.

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
```


Effectively it implements the following; 

```python
data=csvFuturesData() ## or the data object that has been passed
config=Config("systems.provided.futures_chapter15.futuresconfig.yaml") ## or the config object that is passed

## Optionally the user can provide trading_rules (something which can be parsed as a set of trading rules); however this defaults to None in which case
##     the rules in the config will be used.

system=System([Account(), PortfoliosFixed(), PositionSizing(), FuturesRawData(), ForecastCombine(), 
                   ForecastScaleCap(), Rules(trading_rules)], data, config)
```

<a name="estimated_system">
</a>

#### [Futures system for chapter 15](/systems/provided/futures_chapter15/estimatedsystem.py)


This system implements the framework in chapter 15 of my book, but includes estimation of forecast scalars, instrument and forecast diversification multiplier, instrument and forecast weights.


```python
from systems.provided.futures_chapter15.estimatedsystem import futures_system
system=futures_system()
```


Effectively it implements the following; 

```python
data=csvFuturesData() ## or the data object that has been passed
config=Config("systems.provided.futures_chapter15.futuresconfig.yaml") ## or the config object that is passed

## Optionally the user can provide trading_rules (something which can be parsed as a set of trading rules); however this defaults to None in which case
##     the rules in the config will be used.

system=System([Account(), PortfoliosEsimated(), PositionSizing(), FuturesRawData(), ForecastCombine(), 
                   ForecastScaleCap(), Rules(trading_rules)], data, config)
```

The key configuration differences from the standard system are that the estimation parameters:
 - `use_forecast_scale_estimates`,
 - `use_forecast_weight_estimates`
 - `use_instrument_weight_estimates`
-  `use_forecast_div_mult_estimates`
-  `use_instrument_div_mult_estimates`

 ... are all set to `True`.

Warning: Be careful about changing a system from estimated to non estimated 'on the fly' by varying the estimation parameters (in the form use_*_estimates). See [persistence of 'switched' stage objects](#switch_persistence) for more information.


### Using the system object

The system object doesn't do very much in itself, except provide access to its 'child' stages, its cache, and a limited number of methods. The child stages are all attributes of the parent system.

#### Accessing child stages, data, and config within a system


For example to get the final portfolio level 'notional' position, which is in the child stage named `portfolio`:

```python
system.portfolio.get_notional_position("EDOLLAR")
```

We can also access the methods in the data object that is part of every system:

```python
system.data.get_raw_price("EDOLLAR")
```

For a list of all the methods in a system and it's stages see [stage methods](#table_system_stage_methods). Alternatively:
```python
system ## lists all the stages
system.accounts.methods() ## lists all the methods in a particular stage
system.data.methods() ## also works for data
```



We can also access or change elements of the config object:

```python
system.config.trading_rules
system.config.instrument_div_multiplier=1.2
```

#### System methods

Currently system only has two methods of it's own (apart from those used for caching, described below): 

`system.get_instrument_list()` This will get the list of instruments in the system, either from the config object if it contains instrument weights, or from the data object.

`system.log` and `system.set_logging_level()` provides access to the system's log. See [logging](#logging) for more details.

<a name="caching">
</a>

### System Caching and pickling

Pulling in data and calculating all the various stages in a system can be a time consuming process. So the code supports caching. When we first ask for some data by calling a stage method, like `system.portfolio.get_notional_position("EDOLLAR")`, the system first checks to see if it has already pre-calculated this figure. If not then it will calculate the figure from scratch. This in turn may involve calculating preliminary figures that are needed for this position, unless they've already been pre-calculated. So for example to get a combined forecast, we'd already need to have all the individual forecasts from different trading rule variations for a particular instrument. Once we've calculated a particular data point, which could take some time, it is stored in the system object cache (along with any intermediate results we also calculated). The next time we ask for it will be served up immediately. 

Most of the time you shouldn't need to worry about caching. If you're testing different configurations, or updating or changing your data, you just have to make sure you recreate the system object from scratch after each change. A new system object will have an empty cache.

Cache labels 

```python
from copy import copy
from systems.provided.futures_chapter15.basesystem import futures_system

system=futures_system()
system.combForecast.get_combined_forecast("EDOLLAR")

## What's in the cache?
system.cache.get_cache_refs_for_instrument("EDOLLAR")

   [_get_forecast_scalar_fixed in forecastScaleCap for instrument EDOLLAR [carry] , get_raw_forecast in rules for instrument EDOLLAR [ewmac32_128]  ...


## Let's make a change to the config:
system.config.forecast_div_multiplier=0.1

## This will produce the same result, as we've cached the result
system.combForecast.get_combined_forecast("EDOLLAR")

## but if we make a new system with the new config...
system=futures_system(config=system.config)

## check the cache is empty:
system.cache.get_cache_refs_for_instrument("EDOLLAR")

## ... we get a different result
system.combForecast.get_combined_forecast("EDOLLAR")

## We can also turn caching off
## First clear the cache
system.cache.clear()

## ... should be nothing here
system.cache.get_cache_refs_for_instrument("EDOLLAR")

## Now turn off caching
system.cache.set_caching_off()

## Now after getting some data:
system.combForecast.get_combined_forecast("EDOLLAR")

##.... the cache is still empty
system.cache.get_cache_refs_for_instrument("EDOLLAR")

## if we change the config
system.config.forecast_div_multiplier=100.0

## ... then the result will be different without neeting to create a new system
system.combForecast.get_combined_forecast("EDOLLAR")
```

### Pickling and unpickling saved cache data

It can take a while to backtest a large system. It's quite useful to be able to save the contents of the cache and reload it later. I use the python pickle module to do this.

For boring python related reasons not all elements in the cache will be saved. The accounting information, and the optimisation functions used when estimating weights, will be excluded and won't be reloaded.


```python
from systems.provided.futures_chapter15.basesystem import futures_system

system = futures_system(log_level="on")
system.accounts.portfolio().sharpe() ## does a whole bunch of calculations that will be saved in the cache. A bit slow...

system.cache.get_itemnames_for_stage("accounts") # includes 'portfolio'

# if I asked for this again, it's superfast
system.accounts.portfolio().sharpe()

## save it down
system.cache.pickle("private.this_system_name.system.pck") ## Using the 'dot' method to identify files in the workspace. use any file extension you like


## Now in a new session
system = futures_system(log_level="on")
system.cache.get_items_with_data() ## check empty cache

system.cache.unpickle("private.this_system_name.system.pck")

system.cache.get_items_with_data() ## Cache is now populated. Any existing data in system instance would have been removed.
system.get_itemnames_for_stage("accounts") ## now doesn't include ('accounts', 'portfolio', 'percentageTdelayfillTroundpositionsT')

system.accounts.portfolio().sharpe() ## Not coming from the cache, but this will run much faster and reuse many previous calculations

```



### Advanced caching

It's also possible to selectively delete certain cached items, whilst keeping the rest of the system intact. You shouldn't do this without understanding  [stage wiring](#stage_wiring). You need to have a good knowledge of the various methods in each stage, to understand the downstream implications of either deleting or keeping a particular data value.

There are four attributes of data stored in the cache:

1. Unprotected data that is deleted from the cache on request
2. Protected data that wouldn't normally be deletable. Outputs of lengthy estimations are usually protected
3. Data specific to a particular instrument (can be protected or unprotected)
4. Data which applies to the whole system; or at least to multiple instruments (can be protected or unprotected)

Protected items and items common across the system wouldn't normally be deleted since they are usually the slowest things to calculate.

For example here are is how we'd check the cache after getting a notional position (which generates a huge number of intermediate results). Notice the way we can filter and process lists of cache keys.


```python
system.portfolio.get_notional_position("EDOLLAR")

system.cache.get_items_with_data() ## this list everything.
system.cache.get_cacherefs_for_stage("portfolio") ## lists everything in a particular stage
system.cache.get_items_with_data().filter_by_stage_name("portfolio") ## more idiomatic way
system.cache._get_protected_items() ## lists protected items
system.cache.get_items_with_data().filter_by_instrument_code("EDOLLAR") ## list items with data for an instrument
system.cache.get_cache_refs_across_system() ## list items that run across the whole system or multiple instruments

system.cache.get_items_with_data().filter_by_itemname('get_capped_forecast').unique_list_of_instrument_codes() ## lists all instruments with a capped forecast

```

Now if we want to selectively clear parts of the cache we could do one of the following:

```python
system.cache.delete_items_for_instrument(instrument_code) ## deletes everything related to an instrument: NOT protected, or across system items
system.cache.delete_items_across_system() ## deletes everything that runs across the system; NOT protected, or instrument specific items
system.cache.delete_all_items() ## deletes all items relating to an instrument or across the system; NOT protected
system.cache.delete_items_for_stage(stagename) ## deletes all items in a particular stage, NOT protected

## Be careful with these:
system.cache.delete_items_for_instrument(instrument_code, delete_protected=True) ## deletes everything related to an instrument including protected; NOT across system items
system.cache.delete_items_across_system(delete_protected=True) ## deletes everything including protected items that runs across the system; NOT instrument specific items
## If you run these you will empty the cache completely:
system.cache.delete_item(itemname) ## delete everything in the cache for a paticluar item - including protected and across system items
system.cache.delete_all_items(delete_protected=True) ## deletes all items relating to an instrument or across the system - including protected items
system.cache.delete_items_for_stage(stagename, delete_protected=True) ## deletes all items in a particular stage - including protected items
system.cache.clear()
```




#### Advanced Caching when backtesting.

Creating a new system might be very slow. For example estimating the forecast scalars, and instrument and forecast weights from scratch will take time, especially if you're bootstrapping. For this reason they're protected from cache deletion.

A possible workflow might be:

1. Create a basic version of the system, with all the instruments and trading rules that you need.
2. Run a backtest. This will optimise the instrument and forecast weights, and estimate forecast scalars (to really speed things up here you could use a faster method like shrinkage. See the section on [optimisation](#optimisation) for more information.).
3. Change and modify the system as desired. Make sure you change the config object that is embedded within the system. Don't create a new system object.
4. After each change, run `system.delete_all_items()` before backtesting the system again. Anything that is protected won't be re-estimated, speeding up the process. 
5. Back to step 3, until you're happy with the results (but beware of implicit overfitting!)
6. run `system.delete_all_items(delete_protected=True)` or equivalently create a new system object
7. Run a backtest. This will re-estimate everything from scratch for the final version of your system.

Another reason to use caching would be if you want to do your initial exploration with just a subset of the data.

1. Create a basic version of the system, with a subset of the instruments and trading rules that you need.
2. .... 6 as before
7. Add the rest of your instruments to your data set.
8. Run a backtest. This will re-estimate everything from scratch for the final version of your system, including the expanded instrument weights.

Here's a simple example of using caching in system development:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()

# step 2
system.accounts.portfolio().curve() ## effectively runs an entire backtest

# step 3
new_idm=1.1 ## new IDM
system.config.instrument_div_multiplier=new_idm

# step 4
system.cache.delete_all_items() ## protected items won't be affected
system.accounts.portfolio().curve() ## re-run the backtest

# Assuming we're happy- move on to step 6 
system.cache.delete_all_items(delete_protected=True)

## or alternatively recreate the system using the modified config:
new_config=system.config
system=futures_system(config=new_config)

## Step 7
system.accounts.portfolio().curve() ## re-run the final backtest

```


#### Advanced caching behaviour with a live trading system

Although the project doesn't yet include a live trading system, the caching behaviour of the system object will make it more suitable for a live system. If we're trading slowly enough, eg every day, we might be want to to do this overnight:

1. Get new prices for all instruments
2. Save these in wherever our data object is looking
3. Create a new system object from scratch
4. Run the system by asking for optimal positions for all instruments

Step 4 might be very involved and slow, but markets are closed so that's fine. 

Then we do the following throughout the day:

5. Wait for a new price to come in (perhaps through a message bus)
6. So we don't subsequently use stale prices delete everything specific to that instrument with `system.delete_items_for_instrument(instrument_code)`
7. Re-calculate the optimal positions for this instrument
8. This is then passed to our trading algo

Because we've deleted everything specific to the instrument we'll recalculate the positions, and all intermediate stages, using the new price. However we won't have to repeat lengthy calculations that cut across instruments, such as correlation estimates, risk overlays, cross sectional data or weight estimation. That can wait till our next overnight run.


### Very advanced: Caching in new or modified code

If you're going to write new methods for stages (or a complete new stage) you need to follow some rules to keep caching behaviour consistent.

The golden rule is a particular value should only be cached once, in a single place.

So the data object methods should never cache; they should just behave like 'pipes' passing data through to system stages on request. This saves the hassle of having to write methods which delete items in the data object cache as well as the system cache.

Similarly most stages contain 'input' methods, which do no calculations but get the 'output' from an earlier stage and then 'serve' it to the rest of the stage. These exist to simplify changing the internal wiring of a stage and reduce the coupling between methods from different stages. These should also never cache; or again we'll be caching the same data multiple times ( see [stage wiring](#stage_wiring) ).

You should cache as early as possible; so that all the subsequent stages that need that data item already have it. Avoid looping back, where a stage uses data from a later stage, as you may end up with infinite recursion. 

The cache 'lives' in the parent system object in the attribute `system.cache`, *not* the stage with the relevant method. There are standard functions which will check to see if an item is cached in the system, and then call a function to calculate it if required (see below). To make this easier when a stage object joins a system it gains an attribute self.parent, which will be the 'parent' system.

Think carefully about wether your method should create data that is protected from casual cache deletion. As a rule anything that cuts across instruments and / or changes slowly should be protected. Here are the current list of protected items:

- Estimated Forecast scalars
- Estimated Forecast weights
- Estimated Forecast diversification multiplier
- Estimated Forecast correlations
- Estimated Instrument diversification multiplier
- Estimated Instrument weights
- Estimated Instrument correlations

To this list I'd add any cross sectional data, and anything that measures portfolio risk (not yet implemented in this project).

Also think about whether you're going to cache any complex objects that `pickle` might have trouble with, like class instances. You need to flag these up as problematic.

Caching is implemeted (as of version 0.14.0 of this project) by python decorators attached to methods in the stage objects. There are four decorators used by the code:

- `@input`        - no caching done, input method see [stage wiring](#stage_wiring)
- `@dont_cache`   - no caching done, used for very trivial calculations that aren't worth caching
- `@diagnostic()`  - caching done within the body of a stage
- `@output()`       - caching done producing an output

Notice the latter two decorators are always used with brackets, the former without. Labelling your code with the `@input` or `@dont_cache` decorators has no effect whatsoever, and is purely a labelling convention.

Similarly the `@diagnostic` and `@output` decorators perform exactly the same way; it's just helpful to label your [stage wiring](#stage_wiring) and make output functions clear.

The latter two decorators take two optional keyword arguments which default to False `@diagnostic(protected=False, not_pickable=False)`. Set `protected=True` if you want to stop casual deletion of the results of a method. Set `not_pickable=True` if the results of a method will be a complex nested object that pickle will struggle with.

Here are some fragments of code from the forecast_combine.py file showing cache decorators in use:

```python

    @dont_cache
    def _use_estimated_weights(self):
        return str2Bool(self.parent.config.use_forecast_weight_estimates)

    @dont_cache
    def _use_estimated_div_mult(self):
        # very simple
        return str2Bool(self.parent.config.use_forecast_div_mult_estimates)

    @input
    def get_forecast_cap(self):
        """
        Get the forecast cap from the previous module

        :returns: float

        KEY INPUT
        """

        return self.parent.forecastScaleCap.get_forecast_cap()

    @diagnostic()
    def get_trading_rule_list_estimated_weights(self, instrument_code):
        # snip

    @diagnostic(protected=True, not_pickable=True)
    def get_forecast_correlation_matrices_from_code_list(self, codes_to_use):
        # snip

```



### Creating a new 'pre-baked' system

It's worth creating a new pre-baked system if you're likely to want to repeat a backtest, or when you've settled on a system you want to paper or live trade.

The elements of a new pre-baked system will be:

1. New stages, or a different choice of existing stages.
2. A set of data (either new or existing)
3. A configuration file
4. A python function that loads the above elements, and returns a system object

To remain organised it's good practice to save your configuration file and any python functions you need into a directory like `pysystemtrade/private/this_system_name/` (you'll need to create a couple of directories first). If you plan to contribute to github, just be careful to avoid adding 'private' to your commit ( [you may want to read this](https://24ways.org/2013/keeping-parts-of-your-codebase-private-on-github/) ). If you have novel data you're using for this system, you may also want to save it in the same directory.

Then it's a case of creating the python function. Here is an extract from the [futuressystem for chapter 15](/systems/provided/futures_chapter15/basesystem.py)

```python
## We probably need these to get our data

from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config

## We now import all the stages we need
from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.forecast_scale_cap import ForecastScaleCap
from systems.futures.rawdata import FuturesRawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.account import Account


def futures_system( data=None, config=None, trading_rules=None,  log_level="on"):
    """
    
    :param data: data object (defaults to reading from csv files)
    :type data: sysdata.data.Data, or anything that inherits from it
    
    :param config: Configuration object (defaults to futuresconfig.yaml in this directory)
    :type config: sysdata.configdata.Config
    
    :param trading_rules: Set of trading rules to use (defaults to set specified in config object)
    :param trading_rules: list or dict of TradingRules, or something that can be parsed to that

    :param log_level: How much logging to do
    :type log_level: str

    """
    
    if data is None:
        data=csvFuturesData()
    
    if config is None:
        config=Config("systems.provided.futures_chapter15.futuresconfig.yaml")
        
    ## It's nice to keep the option to dynamically load trading rules but if you prefer you can remove this and set rules=Rules() here
    rules=Rules(trading_rules)

    ## build the system
    system=System([Account(), Portfolios(), PositionSizing(), FuturesRawData(), ForecastCombine(), 
                   ForecastScaleCap(), rules], data, config)

    system.set_logging_level(log_level) 

    return system
```


### Changing or making a new System class

It shouldn't be neccessary to modify the `System()` class or create new ones.


<a name="stage_general">
</a>

## Stages

A *stage* within a system does part of the multiple steps of calculation that are needed to ultimately come up with the optimal positions, and hence the account curve, for the system. So the backtesting or live trading process effectively happens within the stage objects.

We define the stages in a system when we create it, by passing a list of stage objects as the first argument:

```python
from systems.forecasting import Rules
from systems.basesystem import System
data=None ## this won't do anything useful

my_system=System([Rules()], data)
```

(This step is often hidden when we use 'pre-baked' systems)

We can see what stages are in a system just by printing it:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
system
```

```
System with stages: accounts, portfolio, positionSize, rawdata, combForecast, forecastScaleCap, rules
```

Stages are attributes of the main system:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
system.rawdata
```

```
SystemStage 'rawdata'
```

So we can access the data methods of each stage:

```python
system.rawdata.get_raw_price("EDOLLAR").tail(5)
```

```
              price
2015-04-16  97.9350
2015-04-17  97.9400
2015-04-20  97.9250
2015-04-21  97.9050
2015-04-22  97.8325
```

`system.rawdata.log` provides access to the log for the stage rawdata, and so on. See [logging][#logging] for more details.



<a name="stage_wiring">'
</a>

### Stage 'wiring'

It's worth having a basic understanding of how the stages within a system are 'wired' together. Futhermore if you're going to modify or create new code, or use [advanced system caching](#caching), you're going to need to understand this properly.

What actually happens when we call `system.combForecast.get_combined_forecast("EDOLLAR")` in the pre-baked futures system? Well this in turn will call other methods in this stage, and they will call methods in previous stages,.. and so on until we get back to the underlying data. We can represent this with a diagram:

- `system.combForecast.get_combined_forecast("EDOLLAR")`
  - `system.combForecast.get_forecast_diversification_multiplier("EDOLLAR")`
  - `system.combForecast.get_forecast_weights("EDOLLAR")`
  - `system.combForecast.get_capped_forecast("EDOLLAR", "ewmac2_8"))` etc
    - `system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac2_8"))` etc
      - `system.forecastScaleCap.get_forecast_cap("EDOLLAR", "ewmac2_8")` etc
      - `system.forecastScaleCap.get_scaled_forecast("EDOLLAR", "ewmac2_8")` etc
        - `system.forecastScaleCap.get_forecast_scalar("EDOLLAR",  "ewmac2_8")` etc
        - `system.forecastScaleCap.get_raw_forecast("EDOLLAR",  "ewmac2_8")` etc
          - `system.rules.get_raw_forecast("EDOLLAR",  "ewmac2_8")` etc
            - `system.data.get_raw_price("EDOLLAR")`
            - `system.rawdata.get_daily_returns_volatility("EDOLLAR")`
              - (further stages to calculate volatility omitted)

A system effectively consists of a 'tree' of which the above shows only a small part. When we ask for a particular 'leaf' of the tree, the data travels up the 'branches' of the tree, being cached as it goes. 

The stage 'wiring' is how the various stages communicate with each other. Generally a stage will consist of:

1. *Input* methods that get data from another stage without doing any further calculation
2. Internal *diagnostic* methods that do intermediate calculations within a stage  (these may be private, but are usually left exposed so they can be used for diagnostic purposes)
3. *Output* methods that other stages will use for their inputs.

For example consider the first few items in the list above. Let's label them appropriately:

- **Output (combForecast)**: `system.combForecast.get_combined_forecast("EDOLLAR")`
  - **Internal (combForecast)**: `system.combForecast.get_forecast_diversification_multiplier("EDOLLAR")`
  - **Internal (combForecast)**: `system.combForecast.get_forecast_weights("EDOLLAR")`
  - **Input (combForecast)**: `system.combForecast.get_capped_forecast("EDOLLAR", "ewmac2_8"))` etc
    - **Output (forecastScaleCap)**: `system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac2_8"))` etc

This approach (which you can also think of as the stage "API") is used to make it easier to modify the code -  we can change the way a stage works internally, or replace it with a new stage with the same name, but as long as we keep the output method intact we don't need to mess around with any other stage.



### Writing new stages

If you're going to write a new stage (completely new, or to replace an existing stage) you need to keep the following in mind:

1. New stages should inherit from [`SystemStage`](/systems/stage/SystemStage)
2. Modified stages should inherit from the existing stage you're modifying. For example if you create a new way of calculating forecast weights then you should inherit from [class `ForecastCombine`](/systems/forecast_combine.py), and then override the `get_forecast_weights` method; whilst keeping the other methods unchanged.
3. Completely new stages will need a unique name; this is specified in the object method `_name()`. They can then be accessed with `system.stage_name`
4. Modified stages should use the same name as their parent, or the wiring will go haywire.
5. Think about whether you need to protect part of the system cache for this stage output [system caching](#caching) from casual deletion.
6. Similarly if you're going to cache complex objects that won't pickle easily (like accountCurve objects) you need to put a no_pickable=True in the decorator call.
7. Use non-cached input methods to get data from other stages. Be wary of accessing internal methods in other stages; try to stick to output methods only.
8. Use cached input methods to get data from the system data object (since this is the first time it will be cached). Again only access public methods of the system data object.
9. Use cached methods for internal diagnostic and output methods(see [system caching](#caching) ).
10. If you want to store attributes within a stage, then prefix them with _ and include a method to access or change them. Otherwise the methods() method will return attributes as well as methods.
11. Internal methods should be public if they could be used for diagnostics, otherwise prefix them with _ to make them private.
12. The doc string for input and output methods should clearly identify them as such. This is to make viewing the wiring easier.
13. The doc string at the head of the stage should specify the input methods (and where they take their input from), and the output methods
14. The doc string should also explain what the stage does, and the name of the stage
15. Really big stages should be seperated across multiple classes (and possibly files), using multiple inheritance to glue them together. See the [accounts stage](/systems/account.py) for an example.

New stage code should be included in a subdirectory of the systems package (as for [futures raw data](/systems/futures/) ) or in your [private directory](/private/).

### Specific stages

The standard list of stages is as follows. The default class is given below, as well as the system attribute used to access the stage.

1. [Raw data:](#stage_rawdata) [class RawData](/systems/rawdata.py) `system.rawdata`
2. [Forecasting:](#rules) [class Rules](/systems/forecasting.py) `system.rules` (chapter 7 of my book)
3. [Scale and cap forecasts:](#stage_scale) [class ForecastScaleCap](/systems/forecast_scale_cap.py) `system.forecastScaleCap`(chapter 7)
4. [Combine forecasts:](#stage_combine) [class ForecastCombine](/systems/forecast_combine.py) `system.combForecast` (chapter 8)
5. [Calculate subsystem positions:](#position_scale) [class PositionSizing](/systems/positionsizing.py)  `system.positionSize` (chapters 9 and 10)
6. [Create a portfolio across multiple instruments:](#stage_portfolio) [class Portfolios](/systems/portfolio.py) `system.portfolio` (chapter 11)
7. [Calculate performance:](#accounts_stage) [class Account](/systems/account.py) `system.accounts`

Each of these stages is described in more detail below.

<a name="stage_rawdata">
</a>

### Stage: Raw data

The raw data stage is used to pre-process data for calculating trading rules, scaling positions, or anything else we might. Good reasons to include something in raw data are:

1. If it is used multiple times, eg price volatility
2. To provide better diagnostics and visibility in the system, eg the intermediate steps required to calculate the carry rule for futures

 
#### Using the standard [RawData class](/systems/rawdata.py)

The base RawData class includes methods to get instrument prices, daily returns, volatility, and normalised returns (return over volatility).

<a name="vol_calc">
</a>

##### Volatility calculation

There are two types of volatility in my trading systems:

1. Price difference volatility eg sigma (Pt - Pt-1)
2. Percentage return volatility eg sigma (Pt - Pt -1 / P*t-1)

The first kind is used in trading rules to normalise the forecast into something proportional to Sharpe Ratio. The second kind is used to scale positions. In both cases we use a 'stitched' price to work out price differences. So in futures we splice together futures contracts as we roll, shifting them according to the Panama method. Similarly if the system dealt with cash equities, it would handle ex-dividend dates in the same way. If we didn't do this, but just used the 'natural' price (the raw price of the contract we're trading) to calculate returns, we'd get sharp returns on rolls. 

In fact stitched prices are used by default in the system; since they make more sense for trading rules that usually prefer smoother prices without weird jumps. Nearly all the methods in raw data that mention price are referring to the stitched price.

However when working out percentage returns we absolutely don't want to use the 'stitched' price as the denominator. For positive carry assets stitched prices will increase over time; this means they will be small or even negative in the past and the percentage returns will be large or have the wrong sign.

For this reason there is a special method in the data class called `daily_denominator_price`. This tells the code what price to use for the P* in the calculation above. In the base class this defaults to the stitched price (but in the futures class, described below, it uses the raw price of the current contract).

The other point to note is that the price difference volatility calculation is configurable through `config.volatility_calculation`.

The default function used is a robust EWMA volatility calculator with the following configurable attributes:

- 35 day span
- Needs 10 periods to generate a value
- Will floor any values less than 0.0000000001 
- Applys a further vol floor which:
  - Calculates the 5% percentile of vol using a 500 day moving average (needing 100 periods to generate a value)
  - Floors any vol below that level

YAML: 
```
volatility_calculation:
  func: "syscore.algos.robust_vol_calc"
  days: 35
  min_periods: 10
  vol_abs_min: 0.0000000001 
  vol_floor: True
  floor_min_quant: 0.05
  floor_min_periods: 100
  floor_days: 500

```

If you're considering using your own function please see [configuring defaults for your own functions](#config_function_defaults)


#### Using the [FuturesRawData class](/systems/futures/rawdata.py)

The futures raw data class has some extra methods needed to calculate the carry rule for futures, and to expose the intermediate calculations. It also overrides `daily_denominator_price` with the raw price of the futures contract currently traded (as noted [above](#vol_calc) ).


#### New or modified raw data classes

It would make sense to create new raw data classes for new types of assets, or to get more visibility inside trading rule calculations.

For example:

1. To work out the quality factor for an equity value system, based on raw accounting ratios
2. To work out the moving averages to be used in an EWMAC trading rule, so they can be viewed for diagnostic purposes.

For new asset classes in particular you should think hard about what you should override the `daily_denominator_price` (see discussion on volatility calculation above).

<a name="rules">
</a>

### Stage: Rules

Trading rules are at the heart of a fully systematic trading system. This stage description is different from the others; and will be in the form of a tutorial around creating trading rules.

The base class,  Rules() [is here](/systems/forecasting.py); and it shouldn't be neccessary to modify this class.

<a name="TradingRules">
</a>

### Trading rules

A trading rule consists of:

- a function
- some data (specified as positional arguments) 
- some optional control arguments (specified as key word arguments)

So the function must be something like these:

```python
def trading_rule_function(data1):
   ## do something with data1

def trading_rule_function(data1, arg1=default_value):
   ## do something with data1
   ## controlled by value of arg1

def trading_rule_function(data1, data2):
   ## do something with data1 and data2

def trading_rule_function(data1, data2, arg1=default_value, arg2=default_value):
   ## do something with data1
   ## controlled by value of arg1 and arg2

```
... and so on. 

At a minimum we need to know the function, since other arguments are optional, and if no data is specified the instrument price is used. A rule specified with only the function is a 'bare' rule. It should take only one data argument which is price, and have no other arguments that need new parameter values.

In this project there is a specific [`TradingRule` class](/systems/forecasting.py). A `TradingRule` instance contains 3 elements - a function, a list of any data the function needs, and a dict of any other arguments that can be passed to the function.

The function can either be the actual function, or a relative reference to it eg "systems.provided.futures_chapter15.rules.ewmac" (this is useful when a  configuration is created from a file). Data must always be in the form of references to attributes and methods of the system object, eg 'data.daily_prices' or 'rawdata.get_daily_prices'. Either a single data item, or a list must be passed. Other arguments are in the form a dictionary. 

We can create trading rules in a number of different ways. I've noticed that different people find different ways of defining rules more natural than others, hence the deliberate flexibility here.

Bare rules which only consist of a function can be defined as follows:

```python
from systems.forecasting import TradingRule

TradingRule(ewmac) ## with the actual function
TradingRule("systems.provided.futures_chapter15.rules.ewmac") ## string reference to the function
```

We can also add data and other arguments. Data is always a list of str, or a single str. Other arguments are always a dict.

```python
TradingRule(ewmac, data='rawdata.get_daily_prices', other_args=dict(Lfast=2, Lslow=8)) 
```

Multiple data is fine, and it's okay to omit data or other_args:

```python
TradingRule(some_rule, data=['rawdata.get_daily_prices','data.get_raw_price'])
```

Sometimes it's easier to specify the rule 'en bloc'. You can do this with a 3 tuple. Notice here we're specifying the function with a string, and listing multiple data items:

```python
TradingRule(("systems.provided.futures_chapter15.rules.ewmac", ['rawdata.get_daily_prices','data.get_raw_price'], dict(Lfast=3, Lslow=12)))
```

You can also specify rules with a dict. If using a dict keywords can be omitted (but not `function`).

```python
TradingRule(dict(function="systems.provided.futures_chapter15.rules.ewmac", data=['rawdata.get_daily_prices','data.get_raw_price']))
```

Note if you use an 'en bloc' method, and also include the `data` or `other_args` arguments in your call to `TradingRule`, you'll get a warning.

The dictionary method is used when configuration objects are read from YAML files; these contain the trading rules in a nested dict.

YAML: (example) 
```
trading_rules:
  ewmac2_8:
     function: systems.futures.rules.ewmac
     data:
         - "data.daily_prices"
         - "rawdata.daily_returns_volatility"
     other_args: 
         Lfast: 2
         Lslow: 8
     forecast_scalar: 10.6
```

Note that *`forecast_scalar`* isn't strictly part of the trading rule definition, but if included here will be used instead of the seperate `config.forecast_scalar` parameter (see the [next stage](#stage_scale) ). 


### The Rules class, and specifying lists of trading rules

We can pass a trading rule, or a group of rules, into the class Rules() in a number of ways.

#### Creating lists of rules from a configuration object

Normally we'd pass in the list of rules form a configuration object. Let's have a look at an incomplete version of the pre-baked chapter 15 futures system.

```python
## We probably need these to get our data

from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config
from systems.basesystem import System

## We now import all the stages we need
from systems.forecasting import Rules
from systems.futures.rawdata import FuturesRawData

data=csvFuturesData()
config=Config("systems.provided.futures_chapter15.futuresconfig.yaml")
        
rules=Rules()

## build the system
system=System([rules, FuturesRawData()], data, config)

rules
```

```
Rules object with unknown trading rules [try Rules.tradingrules() ]
```

```python
## Once part of a system we can see the rules
forecast=system.rules.get_raw_forecast('EDOLLAR','ewmac2_8')
rules
```

```
Rules object with rules ewmac32_128, ewmac64_256, ewmac16_64, ewmac8_32, ewmac4_16, ewmac2_8, carry
```

```python
## 
rules.trading_rules()
```

```
{'carry': TradingRule; function: <function carry at 0xb2e0f26c>, data: rawdata.daily_annualised_roll, rawdata.daily_returns_volatility and other_args: smooth_days,
 'ewmac16_64': TradingRule; function: <function ewmac at 0xb2e0f224>, data: rawdata.daily_prices, rawdata.daily_returns_volatility and other_args: Lfast, Lslow,
 'ewmac2_8': TradingRule; function: <function ewmac at 0xb2e0f224>, data: rawdata.daily_prices, rawdata.daily_returns_volatility and other_args: Lfast, Lslow,
 'ewmac32_128': TradingRule; function: <function ewmac at 0xb2e0f224>, data: rawdata.daily_prices, rawdata.daily_returns_volatility and other_args: Lfast, Lslow,
 'ewmac4_16': TradingRule; function: <function ewmac at 0xb2e0f224>, data: rawdata.daily_prices, rawdata.daily_returns_volatility and other_args: Lfast, Lslow,
 'ewmac64_256': TradingRule; function: <function ewmac at 0xb2e0f224>, data: rawdata.daily_prices, rawdata.daily_returns_volatility and other_args: Lfast, Lslow,
 'ewmac8_32': TradingRule; function: <function ewmac at 0xb2e0f224>, data: rawdata.daily_prices, rawdata.daily_returns_volatility and other_args: Lfast, Lslow}
```


What actually happens when we run this? (this is a little complex but worth understanding).

1. The `Rules` class is created with no arguments.
2. We create the `system` object. This means that all the stages can see the system, in particular they can see the configuration
3. When the `Rules` object is first created it is 'empty' - it doesn't have a list of valid *processed* trading rules.
3. `get_raw_forecast` is called, and looks for the trading rule "ewmac2_8". It gets this by calling the method `get_trading_rules`
4. When the method `get_trading_rules` is called it looks to see if there is a *processed* dict of trading rules
5. The first time the method `get_trading_rules` is called there won't be a processed list. So it looks for something to process
6. First it will look to see if anything was passed when the instance rules of the `Rules()` class was created
7. Since we didn't pass anything instead it processes what it finds in `system.config.trading_rules` - a nested dict, keynames rule variation names. 
8. The `Rules` instance now has processed rule names in the form of a dict, keynames rule variation names, each element containing a valid `TradingRule` object



#### Interactively passing a list of trading rules

Often when we're working in development mode we won't have worked up a proper config. To get round this we can pass a single trading rule or a set of trading rules to the `Rules()` instance when we create it. If we pass a dict, then the rules will be given appropriate names, otherwise if a single rule or a list is passed they will be given arbitrary names "rule0", "rule1", ... 

Also note that we don't have pass a single rule, list or dict of rules; we can also pass anything that can be processed into a trading rule.

```python
## We now import all the stages we need
from systems.forecasting import Rules

## Pass a single rule. Any of the following are fine. See [defining TradingRule objects](#TradingRules) for more.
trading_rule=TradingRule(ewmac)
trading_rule=(ewmac, 'rawdata.get_daily_prices', dict(Lfast=2, Lslow=8)) 
trading_rule=dict(function=ewmac, data='rawdata.get_daily_prices', other_args=dict(Lfast=2, Lslow=8)) 

rules=Rules(trading_rule)
## The rulea will be given an arbitrary name

## Pass a list of rules. Each rule can be defined how you like
trading_rule1=(ewmac, 'rawdata.get_daily_prices', dict(Lfast=2, Lslow=8)) 
trading_rule2=dict(function=ewmac, other_args=dict(Lfast=4, Lslow=16)) 

rules=Rules([trading_rule1, tradingrule2])
## The rules will be given arbitrary names

## Pass a dict of rules. Each rule can be defined how you like
trading_rule1=(ewmac, 'rawdata.get_daily_prices', dict(Lfast=2, Lslow=8)) 
trading_rule2=dict(function=ewmac, other_args=dict(Lfast=4, Lslow=16)) 

rules=Rules(dict(ewmac2_8=trading_rule1, ewmac4_16=tradingrule2))


```

#### Creating variations on a single trading rule

A very common development pattern is to create a trading rule with some parameters that can be changed, and then to produce a number of variations. Two functions are provided to make this easier.

```python
from systems.forecasting import create_variations_oneparameter, create_variations, TradingRule

## Let's create 3 variations of ewmac
## The default ewmac has Lslow=128
## Let's keep that fixed and vary Lfast
rule=TradingRule("systems.provided.example.rules.ewmac_forecast_with_defaults")
variations=create_variations_oneparameter(rule, [4,10,100], "ewmac_Lfast")

variations.keys()
```

```
dict_keys(['ewmac_Lfast_4', 'ewmac_Lfast_10', 'ewmac_Lfast_100'])
```


```python
## Now let's vary both Lslow and Lfast
rule=TradingRule("systems.provided.example.rules.ewmac_forecast_with_defaults")

## each seperate rule is specified by a dict. We could use a lambda to produce these automatically
variations=create_variations(rule, [dict(Lfast=2, Lslow=8), dict(Lfast=4, Lslow=16)], key_argname="Lfast")
variations.keys()
   dict_keys(['ewmac_Lfast_4', 'ewmac_Lfast_2'])

variations['Lfast_2'].other_args
   {'Lfast': 4, 'Lslow': 16}

```

We'd now create an instance of `Rules()`, passing variations in as an argument.

#### Using a newly created Rules() instance

Once we have our new rules object we can create a new system with it:

```python
## build the system
system=System([rules, FuturesRawData()], data, config)  

```

It's generally a good idea to put new fixed forecast scalars (see [forecasting scaling and capping](#stage_scale) ) and forecast weights into the config (see [the combining stage](#stage_combine) ); although if you're estimating these parameters automatically this won't be a problem. Or if you're just playing with ideas you can live with the default forecast scale of 1.0, and you can delete the forecast weights so that the system will default to using equal weights:

```python
del(config.forecast_weights)
```



#### Passing trading rules to a pre-baked system function

If we've got a pre-baked system and a new set of trading rules we want to try that aren't in a config, we can pass them into the system when it's created:

```python
from systems.provided.futures_chapter15.basesystem import futures_system

## we now create my_rules as we did above, for example
trading_rule1=(ewmac, 'rawdata.get_daily_prices', dict(Lfast=2, Lslow=8)) 
trading_rule2=dict(function=ewmac, other_args=dict(Lfast=4, Lslow=16)) 

system=futures_system(trading_rules=dict(ewmac2_8=trading_rule1, ewmac4_16=tradingrule2)) ## we may need to change the configuration
```


#### Changing the trading rules in a system on the fly (advanced)

The workflow above has been to create a `Rules` instance (either empty, or passing in a set of trading rules), then create a system that uses it. However sometimes we might want to modify the list of trading rules in the system object. For example you may have loaded a pre-baked system in (which will have an empty `Rules()` instance and so be using the rules from the config). Rather than replace that wholesale, you might want to drop one of the rules, add an additional one, or change a rule that already exists.

To do this we need to directly access the private `_trading_rules` attribute that stores **processed** trading rules in a dict. This means we can't pass in any old rubbish that can be parsed into a trading rule as we did above; we need to pass in actual `TradingRule` objects.

```python
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule

system=futures_system()

## Parse the existing rules in the config (not required if you're going to backtest first as this will call this method doing its normal business)
system.rules.trading_rules()


#############
## add a rule by accessing private attribute
new_rule=TradingRule("systems.provided.futures_chapter15.rules.ewmac") ## any form of [TradingRule](#TradingRule) is fine here
system.rules._trading_rules['new_rule']=new_rule 
#############


#############
## modify a rule with existing key 'ewmac2_8'
modified_rule=system.rules._trading_rules['ewmac2_8']
modified_rule.other_args['Lfast']=10

## We can also do:
## modified_rule.function=new_function
## modified_rule.data='data.get_raw_price'
##

system.rules._trading_rules['ewmac2_8']=modified_rule 
#############


#############
## delete a rule (not recommended)
## Removing the rule from the set of fixed forecast_weights or rule_variations (used for estimating forecast_weights) would have the same effect - and you need to do this anyway
## Rules which aren't in the list of variations or weights are not calculated, so there is no benefit in deleting a rule in terms of speed / space
##
system.rules._trading_rules.pop("ewmac2_8")
#############

```



<a name="stage_scale">
</a>

### Stage: Forecast scale and cap [ForecastScaleCap class](/systems/forecast_scale_cap.py)

This is a simple stage that performs two steps:

1. Scale forecasts so they have the right average absolute value, by multipling raw forecasts by a forecast scalar
2. Cap forecasts at a maximum value


#### Using fixed weights (/systems/forecast_scale_cap.py)

The standard configuration uses fixed scaling and caps. It is included in [standard futures system](#futures_system).

Forecast scalars are specific to each rule. Scalars can either be included in the `trading_rules` or `forecast_scalars` part of the config. The former takes precedence if both are included:

YAML: (example) 
```
trading_rules:
  some_rule_name:
     function: systems.futures.rules.arbitrary_function
     forecast_scalar: 10.6

```

YAML: (example) 
```
forecast_scalars: 
   some_rule_name: 10.6
```


The forecast cap is also configurable, but must be the same for all rules:

YAML: 
```
forecast_cap: 20.0
```

If entirely missing default values of 1.0 and 20.0 are used for the scale and cap respectively.

<a name="scalar_estimate">
</a>

#### Calculating estimated forecasting scaling on the fly(/systems/forecast_scale_cap.py)

See [this blog post](http://qoppac.blogspot.co.uk/2016/01/pysystemtrader-estimated-forecast.html).

You may prefer to estimate your forecast scales from the available data. This is often neccessary if you have a new trading rule and have no idea at all what the scaling should be. To do this you need to turn on estimation `config.use_forecast_scale_estimates=True`. It is included in the pre-baked [estimated futures system](#futures_system).

All the config parameters needed are stored in `config.forecast_scalar_estimate`.

You can either estimate scalars for individual instruments, or using data pooled across instruments. The config parameter `pool_instruments` determines which option is used.

##### Pooled forecast scale estimate (default) 

We do this if `pool_instruments=True`. This defaults to using the function "syscore.algos.forecast_scalar", but this is configurable using the parameter `func`. If you're changing this please see [configuring defaults for your own functions](#config_function_defaults).

I strongly recommend using pooling, since it's always good to get more data. The only reason not to use it is if you've been an idiot and designed a forecast for which the scale is naturally different across instruments (see chapter 7 of my book). 

This function calculates a cross sectional median of absolute values, then works out the scalar to get it 10, using a rolling moving average (so always out of sample). 

I also recommend using the defaults, a `window` size of 250000 (essentially long enough so you're estimating with an expanding window) and `min_periods` of 500 (a couple of years of daily data; less than this and we'll get something too unstable especially for a slower trading rule, more and we'll have to wait too long to get a value). The other parameter of interest is `backfill` which is boolean and defaults to True. This backfills the first scalar value found back into the past so we don't lose any data; strictly speaking this is cheating but we're not selecting the parameter for performance reasons so I for one can sleep at night. 

Note: The pooled estimate is [cached](#caching)cached as an 'across system', non instrument specific, item.

##### Individual instrument forecast scale estimate

We do this if `pool_instruments=False`. Other parameters work in the same way.

Note: The estimate is [cached](#caching) seperately for each instrument.

#### New or modified forecast scaling and capping

Possible changes here could include putting in response functions (as described in [this AHL paper](http://papers.ssrn.com/sol3/papers.cfm?abstract_id=2695101) ).

<a name="stage_combine">
</a>

### Stage: Forecast combine [ForecastCombine class](/systems/forecast_combine.py)

We now take a weighted average of forecasts using instrument weights, and multiply by the forecast diversification multiplier.


#### Using fixed weights and multipliers(/systems/forecast_combine.py)

The default fixed weights and a fixed multiplier. It is included in the pre-baked [standard futures system](#futures_system).

Both weights and multiplier are configurable.

Forecast weights can be (a) common across instruments, or (b) specified differently for each instrument. If not included equal weights will be used.

YAML: (a)  
```
forecast_weights:
     ewmac: 0.50
     carry: 0.50

```

YAML: (b)  
```
forecast_weights:
     SP500:
	  ewmac: 0.50
	  carry: 0.50
     US10:
	  ewmac: 0.10
	  carry: 0.90

```

The diversification multiplier can also be (a) common across instruments, or (b) we use a different one for each instrument (would be normal if instrument weights were also different).


YAML: (a)  
```
forecast_div_multiplier: 1.0

```

YAML: (b)  
```
forecast_div_multiplier:
     SP500: 1.4
     US10:  1.1
```

Note that the `get_combined_forecast` method in the standard fixed base class automatically adjusts forecast weights if different trading rules have different start dates for their forecasts. It does not adjust the multiplier. This means that in the past the multiplier will probably be too high. 

#### Using estimated weights and diversification multiplier(/systems/forecast_combine.py)


This behaviour is included in the pre-baked [estimated futures system](#futures_system). We switch to it by setting `config.use_forecast_weight_estimates=True` and/or `config.use_forecast_div_mult_estimates=True`.

##### Estimating the forecast weights

See [optimisation](#optimisation) for more information.


##### Estimating the forecast diversification multiplier

See [estimating diversification multipliers](#divmult).

#### Writing new or modified forecast combination stages

I have no plans to write new stages here.


<a name="position_scale">
</a>

### Stage: Position scaling

<a name="notional">
We now scale our positions according to our percentage volatility target (chapters 9 and 10 of my book). At this stage we treat our target, and therefore our account size, as fixed. So we ignore any compounding of losses and profits. It's for this reason the I refer to the 'notional' position. Later in the documentation I'll relax that assumption.
</a>

#### Using the standard [PositionSizing class](/systems/positionsizing.py)

The annualised percentage volatility target, notional trading capital and currency of trading capital are all configurable.

YAML:  
```
percentage_vol_target: 16.0
notional_trading_capital: 1000000
base_currency: "USD"
```

Note that the stage code tries to get the percentage volatility of an instrument from the rawdata stage. Since a rawdata stage might be omitted, it can also fall back to calculating this from scratch using the data object and the default volatility calculation method.



<a name="stage_portfolio">
</a>

### Stage: Creating portfolios [Portfolios class](/systems/portfolio.py)

The instrument weights and instrument diversification multiplier are used to combine different instruments together into the final portfolio (chapter eleven of my book).


#### Using fixed weights and instrument diversification multiplier(/systems/portfolio.py)

The default uses fixed weights and multiplier.

Both are configurable. If omitted equal weights will be used, and a multiplier of 1.0

YAML: 
```
instrument_weights:
    EDOLLAR: 0.5
    US10: 0.5
instrument_div_multiplier: 1.2

```

Note that the `get_instrument_weights` method in the standard fixed base class automatically adjusts raw forecast weights if different instruments have different start dates for their price history and forecasts. It does not adjust the multiplier. This means that in the past the multiplier will probably be too high. 



#### Using estimated weights and instrument diversification multiplier(/systems/portfolio.py)

You can estimate the correct instrument diversification multiplier 'on the fly', and also estimate instrument weights. This functionality is included in the pre-baked [estimated futures system](#futures_system). It is accessed by setting `config.use_instrument_weight_estimates=True` and/or `config.use_instrument_div_mult_estimates=True`.

##### Estimating the instrument weights

See [optimisation](#optimisation) for more information.

##### Estimating the forecast diversification multiplier

See [estimating diversification multipliers](#divmult).

<a name="buffer">
</a>

#### Buffering and position intertia

Position inertia, or buffering, is a way of reducing trading costs. The idea is that we avoid trading if our optimal position changes only slightly by applying a 'no trade' buffer around the current position. There is more on this subject in chapter 11 of my book.

There are two methods that I use. *Position* buffering is the same as the position inertia method used in my book. We compare the current position to the optimal position. If it's not within 10% (the 'buffer') then we trade to the optimal position, otherwise we don't bother.

This configuration will implement position intertia as in my book.

YAML: 
```
buffer_trade_to_edge: False
buffer_method: position
buffer_size: 0.10
```

The second method is *forecast* buffering. Here we take a proportion of the average absolute position (what we get with a forecast of 10), and use that to size the buffer width. This is more theoretically correct; since the buffer doesn't shrink as we get to zero. Secondly if outside the buffer we trade to the nearest edge of the buffer, rather than going to the optimal position. This further reduces transaction costs. Here are my recommended settings for forecast buffering:

YAML: 
```
buffer_trade_to_edge: True
buffer_method: forecast
buffer_size: 0.10
```

Note that buffering can work on both rounded and unrounded positions. In the case of rounded positions we round the lower limit of the buffer, and the upper limit. 

These python methods allow you to see buffering in action.

```
system.portfolio.get_notional_position("US10") ## get the position before buffering
system.portfolio.get_buffers_for_position("US10") ## get the upper and lower edges of the buffer
system.accounts.get_buffered_position("US10", roundpositions=True) ## get the buffered position.
```

Note that in a live trading system buffering should be done downstream of the system module, in a process which can also see the actual current positions we hold.

#### Capital correction

If you want to see positions that reflect varying capital, then read the section on [capital correction](#capcorrection).

#### Writing new or modified portfolio stages

I currently have no plans to modify this stage.

<a name="accounts_stage">
</a>

### Stage: Accounting

The final stage is the all important accounting stage, which calculates p&l.

<a name="standard_accounts_stage">
</a>

#### Using the standard [Account class](/systems/account.py)

The standard accounting class includes several useful methods:

- `portfolio`: works out the p&l for the whole system (returns accountCurve)
- `pandl_for_instrument`: the contribution of a particular instrument to the p&l (returns accountCurve)
- `pandl_for_subsystem`: work out how an instrument has done in isolation (returns accountCurve)
- `pandl_across_subsystems`: group together all subsystem p&l (not the same as portfolio! Instrument weights aren't used)  (returns accountCurveGroup)
- `pandl_for_trading_rule`: how a trading rule has done agggregated over all instruments (returns accountCurveGroup)
- `pandl_for_trading_rule_weighted`: how a trading rule has done over all instruments as a proportion of total capital  (returns accountCurveGroup)
- `pandl_for_trading_rule_unweighted`: how a trading rule has done over all instruments, unweighted  (returns accountCurveGroup)
- `pandl_for_all_trading_rules`: how all trading rules have done over all instruments (returns nested accountCurveGroup)
- `pandl_for_all_trading_rules_unweighted`: how all trading rules have done over all instruments, unweighted (returns nested accountCurveGroup)
- `pandl_for_instrument_rules`: how all trading rules have done for a particular instrument  (returns accountCurveGroup)
- `pandl_for_instrument_rules_unweighted`: how all trading rules have done for one instrument, unweighted (returns accountCurveGroup)
- `pandl_for_instrument_forecast`: work out how well a particular trading rule variation has done with a particular instrument (returns accountCurve)
- `pandl_for_instrument_forecast_weighted`: work out how well a particular trading rule variation has done with a particular instrument as a proportion of total capital (returns accountCurve)


(Note that [buffered](#buffer) positions are only used at the final portfolio stage; the positions for forecasts and subsystems are not buffered. So their trading costs may be a little overstated).

(Warning: see [weighted and unweighted account curve groups](#weighted_acg) )

Most of these classes share some useful arguments (all boolean):

- `delayfill`: Assume we trade at the next days closing price. Always defaults to True (more conservative)
- `roundpositions`: Round positions to nearest instrument block. Defaults to True for portfolios and instruments, defaults to False for subsystems. Not used in `pandl_for_instrument_forecast` or `pandl_for_trading_rule` (always False)

All p&l methods return an object of type `accountCurve` (for instruments, subsystems and instrument forecasts) or `accountCurveGroup` (for portfolio and trading rule), or even nested `accountCurveGroup` (`pandl_for_all_trading_rules`, `pandl_for_all_trading_rules_unweighted`). This inherits from a pandas data frame, so it can be plotted, averaged and so on. It also has some special methods. To see what they are use the `stats` method:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
system.accounts.portfolio().stats() 
```

```
[[('min', '-1.997e+05'),
  ('max', '4.083e+04'),
  ('median', '-1.631'),
  ('mean', '156.9'),
  ('std', '5226'),
  ('skew', '-7.054'),
  ('ann_mean', '4.016e+04'),
  ('ann_std', '8.361e+04'),
  ('sharpe', '0.4803'),
  ('sortino', '0.5193'),
  ('avg_drawdown', '-1.017e+05'),
  ('time_in_drawdown', '0.9621'),
  ('calmar', '0.1199'),
  ('avg_return_to_drawdown', '0.395'),
  ('avg_loss', '-3016'),
  ('avg_gain', '3371'),
  ('gaintolossratio', '1.118'),
  ('profitfactor', '1.103'),
  ('hitrate', '0.4968'),
  ('t_stat', '2.852'),
  ('p_value', '0.004349')],
 ('You can also plot / print:',
  ['rolling_ann_std', 'drawdown', 'curve', 'as_percent', 'as_cumulative'])]
```

The `stats` method lists three kinds of output:

1. Statistics which can also be extracted with their own methods eg to extract sortino use `system.accounts.portfolio().sortino()`
2. Methods which can be used to do interesting plots eg `system.accounts.portfolio().drawdown()`
3. Attributes which can be used to get returns over different periods, eg `systems.accounts.portfolio().annual`


#### `accountCurve` 
 
There is a lot more to `accountCurve` and group objects than meets the eye. 

Let's start with `accountCurve`, which is the output you get from `systems.account.pandl_for_subsystem` amongst other things  

```python
acc_curve=system.accounts.pandl_for_subsystem("EDOLLAR")
```

This *looks* like a pandas data frame, where each day is a different return. However it's actually a bit more interesting than that. There's actually three different account curves buried inside this; *gross* p&l without costs, *costs*, and *net* including costs. We can access any of them like so:

```python
acc_curve.gross 
acc_curve.net
acc_curve.costs
acc_curve.to_ncg_frame() ## this method returns a data frame with all 3 elements as columns
```

The *net* version is identical to acc_curve; this is deliberate to encourage you to look at net returns. Each curve defaults to displaying daily returns, however we can also access different frequencies (daily, weekly, monthly, annual):

```python
acc_curve.gross.daily ## equivalent to acc_curve.gross
acc_curve.net.daily ## equivalent to acc_curve and acc_curve.net
acc_curve.net.weekly ## or also acc_curve.weekly
acc_curve.costs.monthly
```

Once you have the frequency you require you can then use any of the statistical methods:

```python
acc_curve.gross.daily.stats() ## Get a list of methods. equivalent to acc_curve.gross.stats()
acc_curve.monthly.sharpe() ## Sharpe ratio based on annual 
acc_curve.gross.weekly.std() ## standard deviation of weekly returns
acc_curve.daily.ann_std() ## annualised std. deviation of daily (net) returns
acc_curve.costs.annual.median() ## median of annual costs

```

... or other interesting methods:

```python
acc_curve.rolling_ann_std() ## rolling annual standard deviation of daily (net) returns
acc_curve.gross.curve() ## cumulated returns = account curve of gross daily returns
acc_curve.net.monthly.drawdown() ## drawdown of monthly net returns
acc_curve.costs.weekly.curve() ## cumulated weekly costs
```

You probably won't need it but acc_curve.calc_data() returns a dict of all the information used to calculate a particular account curve. For example:

```python
acc_curve.calc_data()['trades_to_use'] ## simulated trades
```

Personally I prefer looking at statistics in percentage terms. This is easy. Just use the .percent() method before you use any statistical method:

```python
acc_curve.capital ## tells me the capital I will use to calculate %
acc_curve.percent()
acc_curve.gross.daily.percent()
acc_curve.net.daily.percent() 
acc_curve.costs.monthly.percent()
acc_curve.gross.daily.percent().stats() 
acc_curve.monthly.percent().sharpe() 
acc_curve.gross.weekly.percent().std() 
acc_curve.daily.percent().ann_std() 
acc_curve.costs.annual.percent().median() 
acc_curve.percent().rolling_ann_std() 
acc_curve.gross.percent().curve() 
acc_curve.net.monthly.percent().drawdown() 
acc_curve.costs.weekly.percent().curve() 
```


You may also want to use *cumulated* returns, which use compound interest rather than the simple addition I normally use. See this [blog post](http://qoppac.blogspot.co.uk/2016/06/capital-correction-pysystemtrade.html).

```python
acc_curve.cumulative()
acc_curve.gross.daily.cumulative() 
acc_curve.net.daily.cumulative() 
acc_curve.costs.monthly.cumulative()
acc_curve.gross.daily.cumulative().stats() 
acc_curve.monthly.cumulative().sharpe() 
acc_curve.gross.weekly.cumulative().std() 
acc_curve.daily.cumulative().ann_std() 
acc_curve.costs.annual.cumulative().median() 
acc_curve.cumulative().rolling_ann_std() 
acc_curve.gross.cumulative().curve() 
acc_curve.net.monthly.cumulative().drawdown() 
acc_curve.costs.weekly.cumulative().curve() 
```

Or both
```python
acc_curve.cumulative().percent().stats()
acc_curve.percent().cumulative().stats() ## these are equivalent
```

#### `accountCurveGroup` in more detail

`accountCurveGroup`, is the output you get from `systems.account.portfolio`, `systems.account.pandl_across_subsystems`, pandl_for_instrument_rules_unweighted`, `pandl_for_trading_rule` and `pandl_for_trading_rule_unweighted`. For example:

```python
acc_curve_group=system.accounts.portfolio()
```

Again this *looks* like a pandas data frame, or indeed like an ordinary account curve object. So for example these all work:

```python
acc_curve_group.gross.daily.stats() ## Get a list of methods. equivalent to acc_curve.gross.stats()
acc_curve_group.monthly.sharpe() ## Sharpe ratio based on annual 
acc_curve_group.gross.weekly.std() ## standard deviation of weekly returns
acc_curve_group.daily.ann_std() ## annualised std. deviation of daily (net) returns
acc_curve_group.costs.annual.median() ## median of annual costs

```

These are in fact all giving the p&l for the entire portfolio (the sum of individual account curves across all assets); defaulting to giving the net, daily curve. To find out which assets we use acc_curve_group.asset_columns; to access a particular asset we use acc_curve_group['assetName'].

```python
acc_curve_group.asset_columns
acc_curve_group['US10']
```

*Warning see [weighted and unweighted account curve groups](#weighted_acg)*

The second command returns the account curves *just* for US 10 year bonds. So we can do things like:

```python
acc_curve_group['US10'].gross.daily.stats() ## Get a list of methods. equivalent to acc_curve.gross.stats()
acc_curve_group['US10'].monthly.sharpe() ## Sharpe ratio based on annual 
acc_curve_group['US10'].gross.weekly.std() ## standard deviation of weekly returns
acc_curve_group['US10'].daily.ann_std() ## annualised std. deviation of daily (net) returns
acc_curve_group['US10'].costs.annual.median() ## median of annual costs
acc_curve_group['US10'].calc_data()['trades_to_use'] ## list of trades

acc_curve_group.gross['US10'].weekly.std() ## notice equivalent way of getting account curves
```

Sometimes it's nicer to plot all the individual account curves, so we can get a data frame.


```python
acc_curve_group.to_frame() ## returns net account curves all assets in a frame
acc_curve_group.net.to_frame() ## returns net account curves all assets in a frame
acc_curve_group.gross.to_frame() ## returns net account curves all assets in a frame
acc_curve_group.costs.to_frame() ## returns net account curves all assets in a frame
```
*Warning see [weighted and unweighted account curve groups](#weighted_acg)*


The other thing you can do is get a dictionary of any statistical method, measured across all assets:

```python
acc_curve_group.get_stats("sharpe", "net", "daily") ## get all annualised sharpe ratios using daily data
acc_curve_group.get_stats("sharpe", freq="daily") ## equivalent
acc_curve_group.get_stats("sharpe", curve_type="net") ## equivalent
acc_curve_group.net.get_stats("sharpe", freq="daily") ## equivalent
acc_curve_group.net.get_stats("sharpe", percent=False) ## defaults to giving stats in % terms, this turns it off

```

*Warning see [weighted and unweighted account curve groups](#weighted_acg)

You can get summary statistics for these. These can either be simple averages across all assets, or time weighted by the amount of data each asset has.

```python
acc_curve_group.get_stats("sharpe").mean() ## get simple average of annualised sharpe ratios for net returns using daily data
acc_curve_group.get_stats("sharpe").std(timeweighted=True) ## get time weighted standard deviation of sharpes across assets,
acc_curve_group.get_stats("sharpe").tstat(timeweighted=False) ## t tstatistic for average sharpe ratio
acc_curve_group.get_stats("sharpe").pvalue(tim_weighted=True) ## p value of t statistic of time weighted average sharpe ratio.

```

Sometimes it's useful to "stack" all the returns from different assets together, and perform statistical tests on those:

```python
stack=acc_curve_group.stack() ## looks like a very long history of returns for a single asset
stack.net.weekly.sharpe() ## all this kind of stuff works
boot=stack.bootstrap(no_runs=10) ## produce an accountCurveGroup object containing 10 bootstraps, each the same length as the original portfolio
boot=stack.bootstrap(no_runs=10, length=250)  ## each account curve bootstrapped will be 250 business days long
boot.net.get_stats("sharpe").pvalue() ## all this kind of stuff works. Time weighting isn't neccessary as all the same length
```

Note if you have a large number of instruments this code will probably fail. It's more useful when you have a small number, and are concerned about statistical robustness.


#### A nested `accountCurveGroup` 

A nested `accountCurveGroup`, is the output you get from `pandl_for_all_trading_rules` and `pandl_for_all_trading_rules_unweighted`. For example:

```python
nested_acc_curve_group=system.accounts.pandl_for_all_trading_rules()
```

This is an account curve group, whose elements are the performance of each trading rule eg this kind of thing works:

```python
ewmac64_acc=system.accounts.pandl_for_all_trading_rules()['ewmac64_256']
```

However this is also an accountCurveGroup! So you can, for example display how each instrument within this trading rule contributed to performance as a data frame:

```python
ewmac64_acc.to_frame()
```


<a name="weighted_acg">
</a>

##### Weighted and unweighted account curve groups

There are two types of account curve; weighted and unweighted. Weighted curves include returns for each instrument (or trading rule) as a proportion of the total capital at risk. Unweighted curves show each instrument or trading rule in isolation. 

Weighted:
- `portfolio`: works out the p&l for the whole system (weighted group - elements are `pandl_for_instrument` - effective weights are instrument weights * IDM)
- `pandl_for_instrument`: the contribution of a particular instrument to the p&l  (weighted individual curve for one instrument - effective weight is instrument weight * IDM)
-`pandl_for_instrument_rules`: how all trading rules have done for a particular instrument (weighted group - elements are `pandl_for_instrument_forecast` across trading rules; effective weights are forecast weights * FDM)  
- `pandl_for_instrument_forecast_weighted`: work out how well a particular trading rule variation has done with a particular instrument as a proportion of total capital (weighted individual curve - weights are forecast weight * FDM * instrument weight * IDM)
- `pandl_for_trading_rule_weighted`: how a trading rule has done over all instruments as a proportion of total capital (weighted group -elements are `pandl_for_instrument_forecast_weighted` across instruments - effective weights are risk contribution of instrument to trading rule)
- `pandl_for_all_trading_rules`: how all trading rules have done over all instruments (weighted group -elements are `pandl_for_trading_rule_weighted` across variations - effective weight is risk contribution of each trading rule) 

Partially weighted (see below):
- `pandl_for_trading_rule`: how a trading rule has done over all instruments (weighted group -elements are `pandl_for_instrument_forecast_weighted` across instruments, weights are risk contribution of each instrument to trading rule)

Unweighted:
- `pandl_across_subsystems`: works out the p&l for all subsystems (unweighted group - elements are `pandl_for_subsystem`)
- `pandl_for_subsystem`: work out how an instrument has done in isolation (unweighted individual curve for one instrument)
- `pandl_for_instrument_forecast`: work out how well a particular trading rule variation has done with a particular instrument (unweighted individual curve)
- `pandl_for_instrument_rules_unweighted`: how all trading rules have done for a particular instrument (unweighted group - elements are `pandl_for_instrument_forecast` across trading rules) 
- `pandl_for_trading_rule_unweighted`: how a trading rule has done over all instruments (unweighted group -elements are `pandl_for_instrument_forecast` 
across instruments)
- `pandl_for_all_trading_rules_unweighted`: how all trading rules have done over all instruments (unweighted group -elements are `pandl_for_trading_rule` across instruments - effective weight is risk contribution of each trading rule) 


Note that `pandl_across_subsystems` / `pandl_for_subsystem`  are effectively the unweighted versions of `portfolio` / `pandl_for_instrument`.

The difference is important for a few reasons.

- Firstly the return and risk of individual weighted curves will be lower than the target 
- The returns of individual weighted curves will also be highly non stationary, at least for instruments. This is because the weightings of instruments within a portfolio, or a trading rule, will change over time. Usually there are fewer instruments. This means that the risk profile will show much higher returns earlier in the series. Statistics such as sharpe ratio may be highly misleading. 
- The portfolio level aggregate returns of unweighted group curves will make no sense. They will be equally weighted, whereas we'd normally have different weights. 
- Also for portfolios of unweighted groups risk will usually fall over time as markets are added and diversification effects appear. Again this is more problematic for groups of instruments (within a portfolio, or within a trading rule)

Weighting for trading rules p&l is a *little* complicated. 

*`pandl_for_instrument_forecast`:* If I want the p&l of a single trading rule for one instrument in isolation, then I use `pandl_for_instrument_forecast`. *`pandl_for_trading_rule_unweighted`*: If I aggregate these across instruments then I get `pandl_for_trading_rule_unweighted`. The individiual unweighted curves are instrument p&l for each instrument and forecast.

*`pandl_for_instrument_forecast_weighted`:* The weighted p&l of a single trading rule for one instrument, as a proportion of the *entire system's capital*, will be it's individual p&l in isolation (`pandl_for_instrument_forecast`) multiplied by the product of the instrument and forecast weights, and the IDM and FDM (this ignores the effect of total forecast capping and position buffering or inertia). 

*`pandl_for_trading_rule_weighted`:* The weighted p&l of a single trading rule across individual instruments, as a proportion of the *entire system's capital*, will be the group of `pandl_for_instrument_forecast_weighted` of these for a given rule. You can get this with `pandl_for_trading_rule_weighted`. The individual curves within this will be instrument p&l for the relevant trading rule, effectively weighted by the product of instrument, forecast weights, FDM and IDM. The risk of the total curve will be equal to the risk of the rule as part of the total capital, so will be lower than you'd expect. 

*`pandl_for_all_trading_rules`:* If I group the resulting curves across trading rules, then I get `pandl_for_all_trading_rules`. The individual curves will be individual trading rules, weighted by their contribution to total risk. The total curve is the entire system; it will look close to but not exactly like a `portfolio` account curve because of the non linear effects of combined forecast capping, and position buffering or inertia, and rounding if that's used for the portfolio curve.

*`pandl_for_trading_rule`:*  If I want the performance of a given trading rule across individual instruments in isolation, then I need to take `pandl_for_trading_rule_weighted` and normalise it so that the returns are as a proportion of the sum of all the relevant forecast weight * FDM * instrument weight * IDM; this is equivalent to the rules risk contribution within the system. . This is an unweighted curve in one sense (it's not a proportion of total capital), but it's weighted in another (the indiviaul curves when added up give the group curve). The total account curve will have the same target risk as the entire system. The individual curves within it are for each instrument, weighted by their contribution to risk. 

*`pandl_for_all_trading_rules_unweighted`:* If I group *these* curves together, then I get `pandl_for_all_trading_rules_unweighted`. The individual curves will be individual trading rules but not weighted; so each will have its own risk target. This is an unweighted group in the truest sense; the total curve won't make sense.


To summarise:

- Individual account curves either in, or outside, a weighted group should be treated with caution. But the entire portfolio curve is fine.
- The portfolio level account curve for an unweighted group should be treated with caution. But the individual curves are fine.
- With the exception of `pandl_for_trading_rule` the portfolio level curve for a weighted group is a proportion of the entire system capital.

The attribute `weighted_flag` is set to either True (for weighted curves including `pandl_for_trading_rule`) or False (otherwise). All curve __repr__ methods also show either weighted or unweighted status.

#### Testing account curves

If you want to know how significant the returns for an account curve are (no matter where you got it from), then use the method `accurve.t_test()`. This returns the two sided t-test statistic and p-value for a null hypothesis of a zero mean.

Sometimes you might want to compare the performance of two systems, instruments or trading rules. The function `from syscore.accounting import account_test` can be used for this purpose. The two parameters can be anything that looks like an account curve, no matter where you got it from.

When run it returns a two sided t-test statistic and p-value for the null hypothesis of identical means. This is done on the period of time that both objects are trading.

Warning: The assumptions underlying a t-test may be violated for financial data. Use with care.

<a name="costs">
</a>

#### Costs

I work out costs in two different ways:

- by applying a constant drag calculated according to the standardised cost in Sharpe ratio terms and the estimated turnover (see chapter 12 of my book)
- using the actual costs for each trade.

The former method is always used for costs derived from forecasts (`pandl_for_instrument_forecast`, `pandl_for_instrument_forecast_weighted`, `pandl_for_trading_rule`, `pandl_for_all_trading_rules`, `pandl_for_all_trading_rules_unweighted`, `pandl_for_trading_rule_unweighted`, `pandl_for_trading_rule_weighted`, `pandl_for_instrument_rules_unweighted`, and `pandl_for_instrument_rules`).

The latter method is optional for costs derived from actual positions (everything else). Set `config.use_SR_costs = False` to use it for these methods. It is useful for comparing with live trading history, but I do not recommend it for historical purposes as I don't think it is accurate in the past.

Costs that can be included are:

- Slippage, in price points. Half the bid-ask spread, unless trading in large size or with a long history of trading at a better cost.
- Cost per instrument block, in local currency. This is used for most futures.
- Percentage of value costs (0.01 is 1%). Used for US equities. 
- Per trade costs, in local currency. Common for UK brokers. This won't be applied correctly unless `roundpositions=True` in the accounts call.

To see the turnover that has been estimated use:

```
system.accounts.subsystem_turnover(instrument_code) ### Annualised turnover of subsystem
system.accounts.instrument_turnover(instrument_code) ### Annualised turnover of portfolio level position
system.accounts.forecast_turnover(instrument_code, rule_variation_name) ## Annualised turnover of forecast
```

For calculating forecast costs (`pandl_for_instrument_forecast`... and so on. Note these are used for estimating forecast weights) I offer the option to pool costs across instruments. You can either pool the estimate of turnovers (which I recommend), or pool the average of cost * turnover (which I don't recommend). Averaging in the pooling process is always done with more weight given to instruments that have more history.

```
forecast_cost_estimate:
   use_pooled_costs: False
   use_pooled_turnover: True
```


#### Writing new or modified accounting stages

I plan to include ways of summarising profits over groups of assets (trading rules and instruments) in the account stage.

<a name="Processes">
</a>

# Processes

This section gives much more detail on certain important processes that span multiple stages: logging, estimating correlations and diversification multipliers, optimisation, and capital correction.

<a name="logging">
</a>

## Logging

### Basic logging

The system, data, config and each stage object all have a .log attribute, to allow the system to report to the user; as do the functions provided to estimate correlations and do optimisations.

In the current version this just prints to screen, although in future logging will be able to write to databases and files, and send emails if critical events are happening. 

The pre-baked systems I've included all include a parameter log_level. This can be one of the following:

- Off: No logging, except for warnings and errors
- Terse: Print
- On: Print everything.

Alternatively you can set this yourself:

```python
system.set_logging_level(log_level)
```

If you're writing your own code, and want to inform the user that something is happening you should do one of the following:

```python
## self could be a system, stage, config or data object
#
self.log.msg("this is a normal message, will only be printed if logging is On")
self.log.terse("this message will only be printed if logging is Terse or On")
self.log.warn("this message will always be printed")
self.log.error("this message will always be printed, and an exception will be raised")
```

I strongly encourage the use of logging, rather than printing, since printing on a 'headless' automated trading server will not be visible.
As you can see the log is also currently used for very basic error handling. 


### Advanced logging

In my experience wading through long log files is a rather time consuming experience. On the other hand it's often more useful to use a logging approach to monitor system behaviour than to try and create quantitative diagnostics. For this reason I'm a big fan of logging with *attributes*. Every time a log method is called, it will typically know one or more of the following:

- which 'type' of process owns the logger. For example if it's part of a base_system object, its type will be 'base_system'. Future types will probably include price collection, execution and so on.
- which 'stage' or sub process is involved, such as 'rawdata'.
- which instrument code is involved
- which trading rule variation is involved
- which specific futures contract we're looking at (for the future)
- which order id  (for the future)

Then we'll be able to save the log message with its attributes in a database (in future). We can then query the database to get, for example, all the log activity relating to a particular instrument code or trade, for particular dates.

You do need to keep track of what attributes your logger has. Generally speaking you should use this kind of pattern to write a log item 

```python
# this is from the ForecastScaleCap code
#
# This log will already have type=base_system, and stage=forecastScaleCap
#
self.log.msg("Calculating scaled forecast for %s %s" % (instrument_code, rule_variation_name),
                               instrument_code=instrument_code, rule_variation_name=rule_variation_name)
```
This has the advantage of keeping the original log attributes intact. If you want to do something more complex it's worth looking at the doc string for the logger class [here](/syslogdiag/log.py) which shows how attributes are inherited and added to log instances.


<a name="optimisation">
</a>

## Optimisation

See my blog posts on optimisation: [without](http://qoppac.blogspot.co.uk/2016/01/correlations-weights-multipliers.html) and [with costs](http://qoppac.blogspot.co.uk/2016/05/optimising-weights-with-costs.html).

I use an optimiser to calculate both forecast and instrument weights. The process is almost identical for both. 

### The optimisation function, and data

From the config
```
forecast_weight_estimate: ## can also be applied to instrument weights
   func: syscore.optimisation.GenericOptimiser ## this is the only function provided
   pool_instruments: True ## not used for instrument weights
   frequency: "W" ## other options: D, M, Y

```

I recommend using weekly data, since it speeds things up and doesn't affect out of sample performance. 

### Removing expensive assets (forecast weights only)

Again I recommend you check out this [blog post](http://qoppac.blogspot.co.uk/2016/05/optimising-weights-with-costs.html). 

```
forecast_weight_estimate:
   ceiling_cost_SR: 0.13 ## Max cost to allow for assets, annual SR units.  
```

See ['costs'](#costs) to see how to configure pooling when estimating the costs of forecasts.


### Pooling gross returns (forecast weights only)

Pooling across instruments is only available when calculating forecast weights. Again I recommend you check out this [blog post](http://qoppac.blogspot.co.uk/2016/05/optimising-weights-with-costs.html). Only instruments whose rules have survived the application of a ceiling cost will be included in the pooling process.


```
forecast_weight_estimate:
   pool_gross_returns: True ## pool gross returns for estimation
forecast_cost_estimate:
   use_pooled_costs: False  ### use weighted average of [SR cost * turnover] across instruments with the same set of trading rules
   use_pooled_turnover: True ### Use weighted average of turnover across instruments with the same set of trading rules
```

See ['costs'](#costs) to see how to configure pooling when estimating the costs of forecasts. Notice if pool_gross_returns is True, and use_pooled_costs is True, then a single optimisation will be run across all instruments with a common set of trading rules. Otherwise each instrument is optimised individually, which is slower.


### Working out net costs (both instrument and forecast weights)

Again I recommend you check out this [blog post](http://qoppac.blogspot.co.uk/2016/05/optimising-weights-with-costs.html). 

```
forecast_weight_estimate:  ## can also be applied to instrument weights
   equalise_gross: False ## equalise gross returns so that only costs are used for optimisation
   cost_multiplier: 0.0 ## multiply costs by this number. Zero means grosss returns used. Higher than 1 means costs will be inflated. Use zero if apply_cost_weight=True (see later)
```
Notice if equalise_gross is True, and use_pooled_costs is True, then a single optimisation will be run across all instruments with a common set of trading rules (regardless of the value of pool_gross_returns).


### Time periods


There are three options available for the fitting period - expanding (recommended), in sample (never!) and rolling. See Chapter 3 of my book.

From the config
```
   date_method: expanding ## other options: in_sample, rolling
   rollyears: 20
```

### Moment estimation

To do an optimisation we need estimates of correlations, means, and standard deviations. 

From the config

```
forecast_weight_estimate:  ## can also be applied to instrument weights
   correlation_estimate:
     func: syscore.correlations.correlation_single_period
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      
     floor_at_zero: True

   mean_estimate:
     func: syscore.algos.mean_estimator
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      

   vol_estimate:
     func: syscore.algos.vol_estimator
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      
```

If you're using shrinkage or single period optimisation I'd suggest using an exponential weight for correlations, means, and volatility.

### Methods

There are four methods provided to optimise with in the function I've included. Personally I'd use shrinkage if I wanted a quick answer, then bootstrapping.

#### Equal weights

This will give everything in the optimisation equal weights.

```
   method: equal_weights
```

This differs from the "fixed" flavour of forecast combination which gives equal weight to all trading rules; because here any trading rules that are too expensive for a particular instrument will not be included, and effectively have a zero weight.


#### One period (not recommend)

This is the classic Markowitz optimisation with the option to equalise Sharpe Ratios (makes things more stable) and volatilities. Since we're dealing with things that should have the same volatility anyway the latter is something I recommend doing.

```
   method: one_period
   equalise_SR: True
   ann_target_SR: 0.5  ## Sharpe we head to if we're equalising
   equalise_vols: True
```

Notice that if you equalise Sharpe then this will override the effect of any pooling or changes to cost calculation.

#### Bootstrapping (recommended, but slow)

Here we're bootstrapping, by default drawing 50 weeks of data at a time, 100 times.


```
method: bootstrap
   monte_runs: 100
   bootstrap_length: 50
   equalise_SR: False
   ann_target_SR: 0.5  ## Sharpe we head to if we're shrinking or equalising
   equalise_vols: True

```

Notice that if you equalise Sharpe then this will override the effect of any pooling or changes to cost calculation.

#### Shrinkage

This is a basic shrinkage towards a prior of equal sharpe ratios, and equal correlations; with priors equal to the average of estimates from the data. Shrinkage of 1.0 means we use the priors, 0.0 means we use the empirical estimates.

```
   method: shrinkage 
   shrinkage_SR: 0.90
   ann_target_SR: 0.5  ## Sharpe we head to if we're shrinking 
   shrinkage_corr: 0.50
   equalise_vols: True

```

Notice that if you equalise Sharpe by shrinking with a factor of 1.0, then this will override the effect of any pooling or changes to cost calculation.


### Post processing

If we haven't accounted for costs earlier (eg by setting `cost_multiplier=0`) then we can adjust our portfolio weights according to costs after they've been calculated. See this blog post [blog post](http://qoppac.blogspot.co.uk/2016/05/optimising-weights-with-costs.html). 

If weights are *cleaned*, then in a fitting period when we need a weight, but none has been calculated (due to insufficient data for example), an instrument is given a share of the weight.


```
   apply_cost_weight: True
   cleaning: True
```


<a name="divmult">
</a>

## Estimating correlations and diversification multipliers

See [my blog post](http://qoppac.blogspot.co.uk/2016/01/correlations-weights-multipliers.html)


You can estimate diversification multipliers for both instruments (IDM - see chapter 11) and forecasts (FDM - see chapter 8). 

The first step is to estimate *correlations*. The process is the same, except that for forecasts you have the option to pool instruments together. As the following YAML extract shows I recommend estimating these with an exponential moving average on weekly data:

```
forecast_correlation_estimate:
   pool_instruments: True ## not available for IDM estimation
   func: syscore.correlations.CorrelationEstimator ## function to use for estimation. This handles both pooled and non pooled data
   frequency: "W"   # frequency to downsample to before estimating correlations
   date_method: "expanding" # what kind of window to use in backtest
   using_exponent: True  # use an exponentially weighted correlation, or all the values equally
   ew_lookback: 250 ## lookback when using exponential weighting
   min_periods: 20  # min_periods, used for both exponential, and non exponential weighting
   cleaning: True  # Replace missing values with an average so we don't lose data early on
```

Once we have correlations, and the forecast or instrument weights, it's a trivial calculation. 

```
instrument_div_mult_estimate:
   func: syscore.divmultipliers.diversification_multiplier_from_list ## function to use
   ewma_span: 125   ## smooth to apply 
   floor_at_zero: True ## floor negative correlations
   div_mult: 2.5 ## maximum allowable multiplier
```

I've included a smoothing function, other wise jumps in the multiplier will cause trading in the backtest. Note that the FDM is calculated on an instrument by instrument basis, but if instruments have had their forecast weights and correlations estimated on a pooled basis they'll have the same FDM. It's also a good idea to floor negative correlations at zero to avoid inflation the DM to very high values.


<a name="capcorrection">
</a>

## Capital correction: Varying capital

Capital correction is the process by which we change the capital we have at risk, and thus our positions, according to any profits or losses made. Most of pysystemtrade assumes that capital is *fixed*. This has the advantage that risk is stable over time, and account curves can more easily be interpreted. However a more common method is to use *compounded* capital, where profits are added to capital and losses deducted. If we make money then our capital, and the risk we're taking, and the size of our positions, will all increase over time.

There is much more in this [blog post](http://qoppac.blogspot.co.uk/2016/06/capital-correction-pysystemtrade.html). Capital correction is controlled by the following config parameter which selects the function used for correction using the normal dot argument (the default here being the function `fixed_capital` in the module `syscore.capital`)

YAML:
``` 
capital_multiplier:
   func: syscore.capital.fixed_capital
```

Other functions I've written are `full_compounding` and `half_compounding`. Again see the blog post [blog post](http://qoppac.blogspot.co.uk/2016/06/capital-correction-pysystemtrade.html) for more detail.

To get the varying capital multiplier which the chosen method calculates use `system.accounts.capital_multiplier()`. The multiplier will be 1.0 at a given time if the variable capital is identical to the fixed capital.

Here's a list of methods with their counterparts for both fixed and variable capital:

|                             | Fixed capital | Variable capital       | 
|:-------------------------:|:---------:|:---------------:|
| Get capital at risk | `positionSize.get_daily_cash_vol_target()['notional_trading_capital']`  |  `accounts.get_actual_capital()` |  
| Get position in a system portfolio | `portfolio.get_notional_position` | `portfolio.get_actual_position` |
| Get buffers for a position | `portfolio.get_buffers_for_position` | `portfolio.get_actual_buffers_for_position` |
| Get buffered position | `accounts.get_buffered_position`| `accounts.get_buffered_position_with_multiplier`| 
| Get p&l for instrument at system level |  `accounts.pandl_for_instrument`|  `accounts.pandl_for_instrument_with_multiplier`|
| P&L for whole system |  `accounts.portfolio`|  `accounts.portfolio_with_multiplier`| 

All other methods in pysystemtrade use fixed capital.

<a name="reference">
</a>

# Reference


<a name="table_system_stage_methods">
</a>

## Table of standard system.data and system.stage methods

The tables in this section list all the methods that can be used to get data out of a system and its 'child' stages. You can also use the methods() method:

```python
system.rawdata.methods() ## works for any stage or data
```

### Explanation of columns

For brevity the name of the system instance is omitted from the 'call' column (except where it's the actual system object we're calling directly). So for example to get the instrument price for Eurodollar from the data object, which is marked as *`data.get_raw_price`* we would do something like this:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
name_of_system=futures_system()
name_of_system.data.get_raw_price("EDOLLAR")
```

Standard methods are in all systems. Non standard methods are for stage classes inherited from the standard class, eg the raw data method specific to *futures*; or the *estimate* classes which estimate parameters rather than use fixed versions.

Common arguments are:

- `instrument_code`: A string indicating the name of the instrument
- `rule_variation_name`: A string indicating the name of the trading rule variation

Types are one or more of D, I, O:

- **D**iagnostic: Exposed method useful for seeing intermediate calculations
- Key **I**nput: A method which gets information from another stage. See [stage wiring](#stage_wiring). The description will list the source of the data.
- Key **O**utput: A method whose output is used by other stages. See [stage wiring](#stage_wiring). Note this excludes items only used by specific trading rules (noteably rawdata.daily_annualised_roll)

Private methods are excluded from this table.


### System object

| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `system.get_instrument_list`  | Standard  |                        |  D,O   | List of instruments available; either from config.instrument weights, config.instruments, or from data set|

Other methods exist to access logging and caching.

### Data object


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `data.get_raw_price` | Standard  | `instrument_code`        | D,O  | Intraday prices if available (backadjusted if relevant)|
| `data.daily_prices` | Standard  | `instrument_code`        | D,O  | Default price used for trading rule analysis (backadjusted if relevant)|
| `data.get_instrument_list`  | Standard  |                        |  D,O   | List of instruments available in data set (not all will be used for backtest)|
| `data.get_value_of_block_price_move`| Standard | `instrument_code` | D,O  | How much does a $1 (or whatever) move in the price of an instrument block affect it's value? |
| `data.get_instrument_currency`|Standard | `instrument_code` | D,O | What currency does this instrument trade in? |
| `data.get_fx_for_instrument`  |Standard | `instrument_code, base_currency` | D, O | What is the exchange rate between the currency of this instrument, and some base currency? |
| `data.get_instrument_raw_carry_data` | Futures | `instrument_code` | D, O | Returns a dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT |
| `data.get_raw_cost_data`| Standard | `instrument_code` | D,O  | Cost data (slippage and different types of commission) |



### [Raw data stage](#stage_rawdata)

        
| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `rawdata.get_daily_prices` | Standard |     `instrument_code`     | I |  `data.daily_prices`|
| `rawdata.daily_denominator_price` | Standard | `instrument_code`  |  O | Price used to calculate % volatility (for futures the current contract price) |
| `rawdata.daily_returns` | Standard | `instrument_code` | D, O | Daily returns in price units|
| `rawdata.daily_returns_volatility` | Standard | `instrument_code` | D,O | Daily standard deviation of returns in price units |
| `rawdata.get_daily_percentage_volatility` | Standard | `instrument_code` | D,O | Daily standard deviation of returns in % (10.0 = 10%) |
| `rawdata.norm_returns` | Standard            | `instrument_code` | D | Daily returns normalised by vol (1.0 = 1 sigma) |
| `rawdata.get_instrument_raw_carry_data` | Futures | `instrument_code` | I | data.get_instrument_raw_carry_data | 
| `rawdata.raw_futures_roll`| Futures | `instrument_code` | D |  | 
| `rawdata.roll_differentials` | Futures | `instrument_code` | D |  |
| `rawdata.annualised_roll` | Futures | `instrument_code` | D | Annualised roll |
| `rawdata.daily_annualised_roll` | Futures | `instrument_code` | D | Annualised roll. Used for carry rule. |
 


### [Trading rules stage (chapter 7 of book)](#rules)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `rules.trading_rules` | Standard  |         | D,O  | List of trading rule variations |
| `rules.get_raw_forecast` | Standard | `instrument_code`, `rule_variation_name` | D,O| Get forecast (unscaled, uncapped) |


### [Forecast scaling and capping stage (chapter 7 of book)](#stage_scale)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `forecastScaleCap.get_raw_forecast` | Standard  | `instrument_code`, `rule_variation_name`        | I  | `rules.get_raw_forecast` |
| `forecastScaleCap.get_forecast_scalar` | Standard / Estimate | `instrument_code`, `rule_variation_name`        | D  | Get the scalar to use for a forecast |
| `forecastScaleCap.get_forecast_cap` | Standard | `instrument_code`, `rule_variation_name`        | D,O  | Get the maximum allowable forecast |
| `forecastScaleCap.get_scaled_forecast` | Standard | `instrument_code`, `rule_variation_name`        | D  | Get the forecast after scaling (after capping) |
| `forecastScaleCap.get_capped_forecast` | Standard | `instrument_code`, `rule_variation_name`        | D, O  | Get the forecast after scaling (after capping) |


### [Combine forecasts stage (chapter 8 of book)](#stage_combine)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `combForecast.get_capped_forecast` | Standard  | `instrument_code`, `rule_variation_name`        | I  | `forecastScaleCap.get_capped_forecast` |
| `combForecast.get_trading_rule_list` | Standard  | `instrument_code`        | I | List of trading rules from config or prior stage |
| `combForecast.get_all_forecasts` | Standard  | `instrument_code`, (`rule_variation_name`)        | D | pd.DataFrame of forecast values |
| `combForecast.get_forecast_cap` | Standard | `instrument_code`, `rule_variation_name`        | I  | `forecastScaleCap.get_forecast_cap` |
| combForecast.pandl_for_instrument_rules_unweighted| Estimate | `instrument_code`        | I  | `accounts.pandl_for_instrument_rules_unweighted` |
| `combForecast.calculation_of_raw_forecast_weights | Estimate | `instrument_code`        | D  | Forecast weight calculation objects |
| `combForecast.get_raw_forecast_weights` | Standard / Estimate | `instrument_code`        | D  | Forecast weights |
| `combForecast.get_forecast_weights` | Standard  / Estimate| `instrument_code`        | D  | Forecast weights, adjusted for missing forecasts|
| `combForecast.get_forecast_correlation_matrices` | Estimate  | `instrument_code`       | D  | Correlations of forecasts |
| `combForecast.get_forecast_diversification_multiplier` | Standard / Estimate  | `instrument_code`        | D  | Get diversification multiplier |
| `combForecast.get_combined_forecast` | Standard  | `instrument_code`        | D,O  | Get weighted average of forecasts for instrument |



### [Position sizing stage (chapters 9 and 10 of book)](#position_scale)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `positionSize.get_combined_forecast` | Standard  | `instrument_code`        | I  | `combForecast.get_combined_forecast` |
| `positionSize.get_price_volatility` | Standard | `instrument_code`        | I  | `rawdata.get_daily_percentage_volatility` (or `data.daily_prices`) |
| `positionSize.get_instrument_sizing_data` | Standard | `instrument_code`        | I  | `rawdata.get_rawdata.daily_denominator_price( (or `data.daily_prices`); `data.get_value_of_block_price_move` |
| `positionSize.get_fx_rate` | Standard | `instrument_code` | I | `data.get_fx_for_instrument` |
| `positionSize.get_daily_cash_vol_target` | Standard |  | D | Dictionary of base_currency, percentage_vol_target, notional_trading_capital, annual_cash_vol_target, daily_cash_vol_target |
| `positionSize.get_block_value` | Standard | `instrument_code` | D | Get value of a 1% move in the price |
| `positionSize.get_instrument_currency_vol` | Standard | `instrument_code` |D | Get daily volatility in the currency of the instrument |
| `positionSize.get_instrument_value_vol` | Standard | `instrument_code` |D | Get daily volatility in the currency of the trading account |
| `positionSize.get_volatility_scalar` | Standard | `instrument_code` | D |Get ratio of target volatility vs volatility of instrument in instrument's own currency |
| `positionSize.get_subsystem_position`| Standard | `instrument_code` | D, O |Get position if we put our entire trading capital into one instrument |



### [Portfolio stage (chapter 11 of book)](#stage_portfolio)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `portfolio.get_subsystem_position`| Standard | `instrument_code` | I |`positionSize.get_subsystem_position` |
| `portfolio.get_instrument_list`| Standard |  | I | `system.get_instrument_list` |
| `portfolio.pandl_across_subsystems`| Estimate |  `instrument_code` | I | `accounts.pandl_across_subsystems`|
| `calculation_of_raw_instrument_weights`| Estimate |   | D | Instrument weight calculation objects |
| `portfolio.get_raw_instrument_weights`| Standard / Estimate|  | D |Get instrument weights |
| `portfolio.get_instrument_weights`| Standard / Estimate|  | D |Get instrument weights, adjusted for missing instruments |
| `portfolio.get_instrument_diversification_multiplier`| Standard / Estimate |  | D |Get instrument div. multiplier |
| `portfolio.get_notional_position`| Standard | `instrument_code` | D,O |Get the *notional* position (with constant risk capital; doesn't allow for adjustments when profits or losses are made) |
| `portfolio.get_buffers_for_position`| Standard | `instrument_code` | D,O |Get the buffers around the position |
| `portfolio.get_actual_position`| Standard |  `instrument_code` | D,O | Get position accounting for capital multiplier|
| `portfolio.get_actual_buffers_for_position`| Standard | `instrument_code` | D,O |Get the buffers around the position, accounting for capital multiplier |



### [Accounting stage](#accounts_stage)

Inputs:

| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `accounts.get_notional_position`| Standard |  `instrument_code` | I | `portfolio.get_notional_position`|
| `accounts.get_actual_position`| Standard |  `instrument_code` | I | `portfolio.get_actual_position`|
| `accounts.get_capped_forecast`| Standard | `instrument_code`, `rule_variation_name`  | I | `forecastScaleCap.get_capped_forecast`|
| `accounts.get_instrument_list`| Standard |  | I | `portfolio.get_instrument_list`|
| `accounts.get_notional_capital`| Standard |  | I | `positionSize.get_daily_cash_vol_target`|
| `accounts.get_fx_rate`| Standard |  `instrument_code` | I | `positionSize.get_fx_rate`|
| `accounts.get_value_of_price_move`| Standard |  `instrument_code` | I | `positionSize.get_instrument_sizing_data`|
| `accounts.get_daily_returns_volatility`| Standard |  `instrument_code` | I | `rawdata.daily_returns_volatility` or `data.daily_prices`|
| `accounts.get_raw_cost_data`| Standard | `instrument_code` | I  | `data.get_raw_cost_data` |
| `accounts.get_buffers_for_position`| Standard |  `instrument_code` | I | `portfolio.get_buffers_for_position`|
| `accounts.get_actual_buffers_for_position`| Standard |  `instrument_code` | I | `portfolio.get_actual_buffers_for_position`|
| `accounts.get_instrument_diversification_multiplier`| Standard |   | I | `portfolio.get_instrument_diversification_multiplier`|
| `accounts.get_instrument_weights`| Standard |   | I | `portfolio.get_instrument_weights`|
| `accounts.get_trading_rules_list`| Standard | `instrument_code`  | I | `combForecast.get_trading_rule_list`|
| `accounts.has_same_rules_as_code`| Standard |  `instrument_code` | I | `combForecast._has_same_rules_as_code`|


Diagnostics:

| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `accounts.get_entire_trading_rule_list`| Standard |   | D | All trading rules across instruments|
| `accounts.get_instrument_scaling_factor`| Standard | `instrument_code`  | D | IDM * instrument weight|
| `accounts.get_forecast_scaling_factor`| Standard | `instrument_code`, `rule_variation_name`  | D | FDM * forecast weight|
| `accounts.get_instrument_forecast_scaling_factor`| Standard | `instrument_code`, `rule_variation_name`  | D | IDM * instrument weight * FDM * forecast weight|
| `accounts.get_capital_in_rule`| Standard |  `rule_variation_name`  | D | Sum of `get_instrument_forecast_scaling_factor` for a given trading rule|
| `accounts.get_buffered_position`| Standard |  `instrument_code` | D | Buffered position at portfolio level|
| `accounts.get_buffered_position_with_multiplier`| Standard |  `instrument_code` | D | Buffered position at portfolio level, including capital multiplier|
| `accounts.subsystem_turnover`| Standard | `instrument_code`  | D | Annualised turnover of subsystem|
| `accounts.instrument_turnover`| Standard | `instrument_code`  | D | Annualised turnover of instrument position at portfolio level|
| `accounts.forecast_turnover`| Standard | `instrument_code`, `rule_variation_name`  | D | Annualised turnover of forecast|
| `accounts.get_SR_cost_for_instrument_forecast`| Standard | `instrument_code`, `rule_variation_name`  | D | SR cost * turnover for forecast|
| `accounts.capital_multiplier`| Standard |   | D, O | Capital multiplier, ratio of actual to fixed notional capital|
| `accounts.get_actual_capital`| Standard |  | D | Actual capital (fixed notional capital times multiplier)|


Accounting outputs:

| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| `accounts.pandl_for_instrument`| Standard |  `instrument_code` | D | P&l for an instrument within a system|
| `accounts.pandl_for_instrument_with_multiplier`| Standard |  `instrument_code` | D | P&l for an instrument within a system, using multiplied capital|
| `accounts.pandl_for_instrument_forecast`| Standard | `instrument_code`, `rule_variation_name` | D | P&l for a trading rule and instrument |
| `accounts.pandl_for_instrument_forecast_weighted`| Standard | `instrument_code`, `rule_variation_name` | D | P&l for a trading rule and instrument as a % of total capital |
| `accounts.pandl_for_instrument_rules`| Standard | `instrument_code` | D,O | P&l for all trading rules in an instrument, weighted |
| `accounts.pandl_for_instrument_rules_unweighted`| Standard | `instrument_code` | D,O | P&l for all trading rules in an instrument, unweighted |
| `accounts.pandl_for_trading_rule`| Standard | `rule_variation_name` | D | P&l for a trading rule over all instruments |
| `accounts.pandl_for_trading_rule_weighted`| Standard | `rule_variation_name` | D | P&l for a trading rule over all instruments as % of total capital |
| `accounts.pandl_for_trading_rule_unweighted`| Standard | `rule_variation_name` | D | P&l for a trading rule over all instruments, unweighted |
| `accounts.pandl_for_subsystem`| Standard |  `instrument_code` | D | P&l for an instrument outright|
| `accounts.pandl_across_subsystems`| Standard |  `instrument_code` | O,D | P&l across instruments, outright|
| `accounts.pandl_for_all_trading_rules`| Standard |  | D | P&l for trading rules across whole system |
| `accounts.pandl_for_all_trading_rules_unweighted`| Standard |  | D | P&l for trading rules across whole system |
| `accounts.portfolio`| Standard |  | O,D | P&l for whole system |
| `accounts.portfolio_with_multiplier`| Standard |  | D | P&l for whole system using multiplied capital|



<a name="Configuration_options">
</a>

## Configuration options

Below is a list of all configuration options for the system. The 'Yaml' section shows how they appear in a yaml file. The 'python' section shows an example of how you'd modify a config object in memory having first created it, like this:


```python
## Method one: from an existing system
from systems.provided.futures_chapter15.basesystem import futures_system
system=futures_system()
new_config=system.config

## Method two: from a config file
from syscore.fileutils import get_pathname_for_package
from sysdata.configdata import Config

my_config=Config(get_pathname_for_package("private", "this_system_name", "config.yaml"))

## Method three: with a blank config
from sysdata.configdata import Config
my_config=Config()
```

Each section also shows the project default options, which you could change [here](#defaults).

When modifying a nested part of a config object, you can of course replace it wholesale:

```python
new_config.instrument_weights=dict(SP500=0.5, US10=0.5))
new_config
```

Or just in part:

```python
new_config.instrument_weights['SP500']=0.2
new_config
```
If you do this make sure the rest of the config is consistent with what you've done. In either case, it's a good idea to examine the modified config once it's part of the system (since that will include any defaults) and make sure you're happy with it.



### Raw data stage

#### Volatility calculation
Represented as: dict of str, int, or float. Keywords: Parameter names
Defaults: As below

The function used to calculate volatility, and any keyword arguments passed to it. Note if any keyword is missing then the project defaults will be used. See ['volatility calculation'](#vol_calc) for more information. 

The following shows how to modify the configuration, and also the default values:

YAML: 
```
volatility_calculation:
  func: "syscore.algos.robust_vol_calc"
  days: 35
  min_periods: 10
  vol_abs_min: 0.0000000001 
  vol_floor: True
  floor_min_quant: 0.05
  floor_min_periods: 100
  floor_days: 500

```

Python
```python
config.volatility_calculation=dict(func="syscore.algos.robust.vol.calc", days=35, min_periods=10, vol_abs_min= 0.0000000001, vol_floor=True, floor_min_quant=0.05, floor_min_periods=100, floor_days=500)
```

If you're considering using your own function please see [configuring defaults for your own functions](#config_function_defaults)


### Rules stage

#### Trading rules
Represented as: dict of dicts, each representing a trading rule. Keywords: trading rule variation names.
Defaults: n/a

The set of trading rules. A trading rule definition consists of a dict containing: a *function* identifying string, an optional list of *data* identifying strings, and *other_args* an optional dictionary containing named paramters to be passed to the function. This is the only method that can be used for YAML.

There are numerous other ways to define trading rules using python code. See ['Rules'](#rules) for more detail.

Note that *forecast_scalar* isn't strictly part of the trading rule definition, but if included here will be used instead of the seperate 'config.forecast_scalar' parameter (see the next section). 

YAML: (example) 
```
trading_rules:
  ewmac2_8:
     function: systems.futures.rules.ewmac
     data:
         - "rawdata.daily_prices"
         - "rawdata.daily_returns_volatility"
     other_args: 
         Lfast: 2
         Lslow: 8
     forecast_scalar: 10.6
```

Python (example)
```python
config.trading_rules=dict(ewmac2_8=dict(function="systems.futures.rules.ewmac", data=["rawdata.daily_prices", "rawdata.daily_returns_volatility"], other_args=dict(Lfast=2, Lslow=8), forecast_scalar=10.6))
```

### Forecast scaling and capping stage

Switch between fixed (default) and estimated versions as follows:

YAML: (example) 
```
use_forecast_scale_estimates: True
```

Python (example)
```python
config.use_forecast_scale_estimates=True
```



#### Forecast scalar (fixed)
Represented as: dict of floats. Keywords: trading rule variation names.
Default: 1.0

The forecast scalar to apply to a trading rule, if fixed scaling is being used. If undefined the default value of 1.0 will be used.

Scalars can also be put inside trading rule definitions (this is the first place we look):

YAML: (example) 
```
trading_rules:
  rule_name:
     function: systems.futures.rules.arbitrary_function
     forecast_scalar: 10.6

```

Python (example)
```python
config.trading_rules=dict(rule_name=dict(function="systems.futures.rules.arbitrary_function", forecast_scalar=10.6))
```

If scalars are not found there they can be put in seperately (if you do both then the scalar in the actual rule specification will take precedence):

YAML: (example) 
```
forecast_scalars: 
   rule_name: 10.6
```

Python (example)
```python
config.forecast_scalars=dict(rule_name=10.6)
```

#### Forecast scalar (estimated)
Represented as: dict of str, float and int. Keywords: parameter names
Default: see below

The method used to estimate forecast scalars on a rolling out of sample basis. Any missing config elements are pulled from the project defaults. Compulsory arguments are pool_instruments (determines if we pool estimate over multiple instruments) and func (str function pointer to use for estimation). The remaining arguments are passed to the estimation function. 

See [forecast scale estimation](#scalar_estimate] for more detail.

If you're considering using your own function please see [configuring defaults for your own functions](#config_function_defaults)


YAML: 
```
# Here is how we do the estimation. These are also the *defaults*.
use_forecast_scale_estimates: True
forecast_scalar_estimate:
   pool_instruments: True
   func: "syscore.algos.forecast_scalar"
   window: 250000
   min_periods: 500
   backfill: True


```

Python (example)
```python
## pooled example
config.trading_rules=dict(pool_instruments=True, func="syscore.algos.forecast_scalar", window=250000, min_periods=500, backfill=True)
```


#### Forecast cap (fixed - all classes)
Represented as: float

The forecast cap to apply to a trading rule. If undefined the project default value of 20.0 will be used.


YAML: 
```
forecast_cap: 20.0
```

Python 
```python
config.forecast_cap=20.0
```

### Forecast combination stage

Switch between fixed (default) and estimated versions as follows:

YAML: (example) 
```
use_forecast_weight_estimates: True
```

Python (example)
```python
config.use_forecast_weight_estimates=True
```

Change smoothing used for both fixed and variable weights:

YAML: (example) 
```
forecast_weight_ewma_span: 125
```


#### Forecast weights (fixed)
Represented as: (a) dict of floats. Keywords: trading rule variation names.
                (b) dict of dicts, each representing the weights for an instrument. Keywords: instrument names
Default: Equal weights, across all trading rules in the system

The forecast weights to be used to combine forecasts from different trading rule variations. These can be (a) common across instruments, or (b) specified differently for each instrument.

Notice that the default is equal weights, but these are calculated on the fly and don't appear in the defaults file.

YAML: (a)  
```
forecast_weights:
     ewmac: 0.50
     carry: 0.50

```

Python (a)
```python
config.forecast_weights=dict(ewmac=0.5, carry=0.5)
```

YAML: (b)  
```
forecast_weights:
     SP500:
	  ewmac: 0.50
	  carry: 0.50
     US10:
	  ewmac: 0.10
	  carry: 0.90

```

Python (b)
```python
config.forecast_weights=dict(SP500=dict(ewmac=0.5, carry=0.5), US10=dict(ewmac=0.10, carry=0.90))
```
#### Forecast weights (estimated)

To estimate forecast weights we need to define which trading rule variations we're using.

##### List of trading rules to get forecasts for

Represented as: (a) list of str, each a rule variation name
                (b) dict of list of str, each representing the rules for an instrument. Keywords: instrument names
Default: Using all trading rules in the system

The rules for which forecast weights are to be calculated. These can be (a) common across instruments, or (b) specified differently for each instrument. If not specified will use all the rules defined in the system.

YAML: (a)  
```
rule_variations:
     - "ewmac"
     - "carry"

```

Python (a)
```python
config.rule_variations=["ewmac", "carry"]
```

YAML: (b)  
```
rule_variations:
     SP500:
	  - "ewmac"
	  - "carry"
     US10:
	  - "ewmac"
```

Python (b)
```python
config.forecast_weights=dict(SP500=["ewmac","carry"], US10=["ewmac"])
```
##### Parameters for estimating forecast weights

Represented as: dict of str, or dict, each representing parameters.
Defaults: See below

To estimate the forecast weights we call the function defined in the `func` config element. 

The defaults given below are for the default generic optimiser function. See the section on (optimisation)[#optimisation] for more information.

YAML, showing defaults
```
forecast_weight_estimate:
   func: syscore.optimisation.GenericOptimiser
   method: shrinkage ## other options: one_period, bootstrap, equal_weights
   pool_gross_returns: True
   equalise_gross: False
   cost_multiplier: 1.0
   ceiling_cost_SR: 0.13
   apply_cost_weight: True
   frequency: "W" ## other options: D, M, Y
   date_method: expanding ## other options: in_sample, rolling
   rollyears: 20
   cleaning: True
   equalise_SR: True
   ann_target_SR: 0.5  ## Sharpe we head to if we're shrinking or equalising
   equalise_vols: True
   shrinkage_SR: 0.90
   shrinkage_corr: 0.50
   monte_runs: 100
   bootstrap_length: 50
   correlation_estimate:
     func: syscore.correlations.correlation_single_period
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      
     floor_at_zero: True
   mean_estimate:
     func: syscore.algos.mean_estimator
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      
   vol_estimate:
     func: syscore.algos.vol_estimator
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      
```

Python, example of how to change certain parameters:

```python
config.forecast_weight_estimate=dict()
config.forecast_weight_estimate['method']='one_period'
config.forecast_weight_estimate['mean_estimate']=dict(min_periods=30)
```

Note: if you are changing the config in situ within the system you should use the following to avoid overwriting the defaults within the system:

```python
config=system.config
config.forecast_weight_estimate['method']='one_period'
config.forecast_weight_estimate['mean_estimate']['min_periods']=30
```



#### Forecast diversification multiplier  (fixed)
Represented as: (a) float or (b) dict of floats with keywords: instrument_codes
Default: 1.0

This can be (a) common across instruments, or (b) we use a different one for each instrument (would be normal if instrument weights were also different).


YAML: (a)  
```
forecast_div_multiplier: 1.0

```

Python (a)
```python
config.forecast_div_multiplier=1.0
```

YAML: (b)  
```
forecast_div_multiplier:
     SP500: 1.4
     US10:  1.1
```

Python (b)
```python
config.forecast_div_multiplier=dict(SP500=1.4, US10=1.0)
```


#### Forecast diversification multiplier  (estimated)

To calculate the diversification multiplier we need to have correlations.

##### Forecast correlation calculation
Represented as: dict of str, float and int. Keywords: parameter names
Default: see below

The method used to estimate forecast correlations on a rolling out of sample basis. Compulsory arguments are pool_instruments (determines if we pool estimate over multiple instruments) and func (str function pointer to use for estimation). The remaining arguments are passed to the estimation function. Any missing items will be pulled from the project defaults file.

See [estimating correlations and the forecast diversification multiplier](#divmult).

YAML: 
```
# Here is how we do the estimation. These are also the *defaults*.
forecast_correlation_estimate:
   pool_instruments: True
   func: syscore.correlations.CorrelationEstimator ## function to use for estimation. This handles both pooled and non pooled data
   frequency: "W"   # frequency to downsample to before estimating correlations
   date_method: "expanding" # what kind of window to use in backtest
   using_exponent: True  # use an exponentially weighted correlation, or all the values equally
   ew_lookback: 250 ## lookback when using exponential weighting
   min_periods: 20  # min_periods     
   cleaning: True  # Replace missing values so we don't lose data early on
```

Python (example)
```python
config.forecast_correlation_estimate=dict(pool_instruments=False)
```

If you're considering using your own function please see [configuring defaults for your own functions](#config_function_defaults)


##### Parameters for estimation of forecast diversification multiplier
Represented as: dict of str, float and int. Keywords: parameter names
Default: see below

The method used to estimate forecast div. multipliers on a rolling out of sample basis. Any missing config elements are pulled from the project defaults. Compulsory arguments are: func (str function pointer to use for estimation). The remaining arguments are passed to the estimation function. 

See [estimating the forecast diversification multiplier](#divmult) for more detail.


YAML: 
```
# Here is how we do the estimation. These are also the *defaults*.
use_forecast_div_mult_estimates: True
forecast_div_mult_estimate:
   func: syscore.divmultipliers.diversification_multiplier_from_list
   ewma_span: 125   ## smooth to apply 
   floor_at_zero: True ## floor negative correlations
   dm_max: 2.5 ## maximum
```

Python (example)
```python
config.forecast_div_mult_estimate=dict(ewma_span=125)
```

If you're considering using your own function please see [configuring defaults for your own functions](#config_function_defaults)


### Position sizing stage

#### Capital scaling parameters 
Represented as: floats, int or str
Defaults: See below

The annualised percentage volatility target, notional trading capital and currency of trading capital. If any of these are undefined in the config the default values shown below will be used.


YAML:  
```
percentage_vol_target: 16.0
notional_trading_capital: 1000000
base_currency: "USD"
```

Python 

```python
config.percentage_vol_target=16.0
config.notional_trading_capital=1000000
config.base_currency="USD"
```

### Portfolio combination stage

Switch between fixed (default) and estimated versions as follows:

YAML: (example) 
```
use_instrument_weight_estimates: True
```

Python (example)
```python
config.use_instrument_weight_estimates=True
```

Change smoothing used for both fixed and variable weights:

YAML: (example) 
```
instrument_weight_ewma_span: 125
```


#### Instrument weights (fixed)
Represented as: dict of floats. Keywords: instrument_codes
Default: Equal weights

The instrument weights used to combine different instruments together into the final portfolio. 

Although the default is equal weights, these are not included in the system defaults file, but calculated on the fly.

YAML: 
```
instrument_weights:
    EDOLLAR: 0.5
    US10: 0.5
```

Python 
```python
config.instrument_weights=dict(EDOLLAR=0.5, US10=0.5)
```

#### Instrument weights (estimated)

Represented as: dict of str, or dict, each representing parameters.
Defaults: See below

To estimate the instrument weights we call the function defined in the `func` config element. All other parameters are passed to the optimisation function.

The defaults given below are for the default generic optimiser function. See the section on (optimisation)[#optimisation] for more information.

YAML, showing defaults
```
instrument_weight_estimate:
   func: syscore.optimisation.GenericOptimiser
   method: shrinkage ## other options: one_period, bootstrap, equal_weights
   frequency: "W" ## other options: D, M, Y
   equalise_gross: False
   cost_multiplier: 1.0
   apply_cost_weight: True
   ceiling_cost_SR: 999 ## this means we don't apply ceiling costs at all
   date_method: expanding ## other options: in_sample, rolling
   rollyears: 20
   cleaning: True
   equalise_SR: True
   ann_target_SR: 0.5  ## Sharpe we head to if we're shrinking or equalising
   equalise_vols: True
   shrinkage_SR: 0.90
   shrinkage_corr: 0.50
   monte_runs: 100
   bootstrap_length: 50
   correlation_estimate:
     func: syscore.correlations.correlation_single_period
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      
     floor_at_zero: True
   mean_estimate:
     func: syscore.algos.mean_estimator
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      
   vol_estimate:
     func: syscore.algos.vol_estimator
     using_exponent: False
     ew_lookback: 500
     min_periods: 20      
```

Python, example of how to change certain parameters:

```python
config.instrument_weight_estimate=dict()
config.instrument_weight_estimate['method']='one_period'
config.instrument_weight_estimate['mean_estimate']=dict(min_periods=30)
```

Note: if you are changing the config in situ within the system you should use the following to avoid overwriting the defaults within the system:

```python
config=system.config
config.instrument_weight_estimate['method']='one_period'
config.instrument_weight_estimate['mean_estimate']['min_periods']=30
```



#### Instrument diversification multiplier (fixed)
Represented as: float
Default: 1.0


YAML: 
```
instrument_div_multiplier: 1.0
```

Python 
```python
config.instrument_div_multiplier=1.0
```

#### Instrument diversification multiplier (estimated)

To calculate the diversification multiplier we need to have correlations.

##### Instrument corrrelations
Represented as: dict of str, float and int. Keywords: parameter names
Default: see below

The method used to estimate instrument correlations on a rolling out of sample basis. Compulsory arguments are func (str function pointer to use for estimation). The remaining arguments are passed to the estimation function. Any missing items will be pulled from the project defaults file.

See [estimating correlations](#divmult).

YAML: 
```
# Here is how we do the estimation. These are also the *defaults*.
instrument_correlation_estimate:
   func: syscore.correlations.CorrelationEstimator ## function to use for estimation. This handles both pooled and non pooled data
   frequency: "W"   # frequency to downsample to before estimating correlations
   date_method: "expanding" # what kind of window to use in backtest
   using_exponent: True  # use an exponentially weighted correlation, or all the values equally
   ew_lookback: 250 ## lookback when using exponential weighting
   min_periods: 20  # min_periods     
   cleaning: True  # Replace missing values so we don't lose data early on
```

Python (example)
```python
config.instrument_correlation_estimate=dict(cleaning=False)
```

If you're considering using your own function please see [configuring defaults for your own functions](#config_function_defaults)



##### Parameters for estimation of instrument diversification multiplier
Represented as: dict of str, float and int. Keywords: parameter names
Default: see below

The method used to estimate the instrument div. multiplier on a rolling out of sample basis. Any missing config elements are pulled from the project defaults. Compulsory arguments are: func (str function pointer to use for estimation). The remaining arguments are passed to the estimation function. 

See [estimating diversification multipliers](#divmult).


YAML: 
```
# Here is how we do the estimation. These are also the *defaults*.
use_instrument_div_mult_estimates: True
instrument_div_mult_estimate:
   func: syscore.divmultipliers.diversification_multiplier_from_list
   ewma_span: 125   ## smooth to apply 
   floor_at_zero: True ## floor negative correlations
   dm_max: 2.5 ## maximum
```

Python (example)
```python
config.use_instrument_div_mult_estimates=True
config.instrument_div_mult_estimate=dict(ewma_span=125)
```

If you're considering using your own function please see [configuring defaults for your own functions](#config_function_defaults)


#### Buffering

Represented as: bool
Default: see below

Which [buffering or position inertia method](#buffer) should we use? 'position': based on optimal position (position inertia), 'forecast': based on position with a forecast of +10; or 'none': do not use a buffer. What size should the buffer be, as a proportion of the position or average forecast position? 0.1 is 10%.

YAML: 
```
buffer_method: position
buffer_size: 0.10
```



### Accounting stage

#### Buffering and position intertia

To work out the portfolio positions should we trade to the edge of the [buffer](#buffer), or to the optimal position?

Represented as: bool
Default: True

YAML: 
```
buffer_trade_to_edge: True
```

 

#### Costs

Should we use normalised Sharpe Ratio [costs](#costs), or the actual costs for instrument level p&l (we always use SR costs for forecasts)?


YAML: 
```

use_SR_costs: True
```

Should we pool SR costs across instruments when working out forecast p&L?

YAML:
```
forecast_cost_estimate:
   use_pooled_costs: False  ### use weighted average of SR cost * turnover across instruments with the same set of trading rules
   use_pooled_turnover: True ### Use weighted average of turnover across instruments with the same set of trading rules
```

#### Capital correction

Which capital correction method should we use?

YAML:
```
capital_multiplier:
   func: syscore.capital.fixed_capital
```

Other valid functions include full_compounding and half_compounding.

