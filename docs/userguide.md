
This guide is divided into three parts. The first 'How do I?' explains how to do many common tasks. The second part 'Guide' details the relevant parts of the code, and explains how to modify or create new parts. The final part 'Reference' includes lists of methods and parameters.

# How do I?

## How do I.... Experiment with a single trading rule and instrument

Although the project is intended mainly for working with trading systems, it's possible to do some limited experimentation without building a system. See [the introduction](introduction.md) for an example.

## How do I....Create a standard futures backtest

This creates the staunch systems trader example defined in chapter 15 of my book, using the csv data that is provided, and gives you the position in the Eurodollar market:

```python
from systems.futures.basesystem import futures_system
system=futures_system()
system.portfolio.get_notional_forecast("EDOLLAR")
```

## How do I....See intermediate results from a backtest

This will give you the raw forecast (before scaling and capping) of one of the EWMAC rules for Eurodollar futures in the standard futures backtest:

```python
from systems.futures.basesystem import futures_system
system=futures_system()
system.rules.get_raw_forecast("EDOLLAR", "ewmac64_256")
```

For a complete list of possible intermediate results, see [this table](#table_system_stage_methods) and look for rows marked with **D** for diagnostic.


## How do I....See how profitable a backtest was

```python
from systems.futures.basesystem import futures_system
system=futures_system()
system.accounts.portfolio.stats() ## see some statistics
system.accounts.portfolio.curve().plot() ## plot an account curve
system.accounts.portfolio.instrument().stats() ## produce statistics for all instruments
system.accounts.portfolio.instrument().plot() ## plot an account curve for each instrument
```

For more information on what statistics are available, see the [relevant guide section](#standard_accounts_stage).


 
<a name="change_backtest_parameters">
## How do I....Change backtest parameters 
</a>

The backtest looks for its configuration information in the following places:

1. Elements in the configuration object
2. Project defaults 

This suggests that you can modify the systems behaviour in any of the following ways:

1. Change or create a new configuration yaml file, read it in, and create a new system
2. Change a configuration object in memory, and create a new system with it.
3. Change a configuration object within an existing system (advanced)
4. Change the project defaults (definitely not recommended)

For a list of all possible configuration options, see [this table](#Configuration_options).

If you use options 2 or 3, you can [save the config](#save_config).

### Option 1: Change the configuration file

Configurations in this project are stored in [yaml](http://pyyaml.org) files. Don't worry if you're not familiar with yaml; it's just a nice way of creating nested dicts, lists and other python objects in plain text. Just be aware that indentations are important, just in like python.

You should make a new config file by copying this [one](/systems/futures/futuresconfig.yaml), and modifying it. Best practice is to save this as `pysystemtrade/systems/users/your_name/this_system_name/config.yaml` (you'll need to create a couple of directories first).

You should then create a new system which points to the new config file:

```python
from syscore.fileutils import get_pathname_for_package
from sysdata.configdata import Config

my_config=Config(get_pathname_for_package("systems", ["users", "your_name", "this_system_name", "config.yaml"]))

from systems.futures.basesystem import futures_system
system=futures_system(config=my_config)
```

### Option 2: Change the configuration object; create a new system

We can also modify the configuration object in the system directly:

```python
from systems.futures.basesystem import futures_system
system=futures_system()
new_config=system.config

new_idm=1.1 ## new IDM

new_config.instrument_div_multiplier=new_idm

system=futures_system(config=new_config)
```

This is useful if you're experimenting interactively 'on the fly'.


### Option 3: Change the configuration object within an existing system (not recommended - advanced)

If you opt for (3) you will need to understand about [system caching](#caching). We can also modify the configuration object in the system directly:

```python
from systems.futures.basesystem import futures_system
system=futures_system()

## Anything we do with the system may well be cached and will need to be cleared before it sees the new value...

new_idm=1.1 ## new IDM
system.config.instrument_div_multiplier=new_idm

## The config is updated, but to reiterate anything that uses it will need to be cleared from the cache
```

Because we don't create a new system and have to recalculate everything from scratch, this can be useful for testing isolated changes to the system if you know what you're doing.

### Option 4: Change the system defaults (definitely not recommended)

I don't recommend changing the defaults, but more information is given [here](#defaults).


## How do I....Run a backtest on a different set of instruments

You need to change the instrument weights in the configuration. Only instruments with weights have positions produced for them. There are two easy ways to do this - change the config file, or the config object already in the system (for more on changing config parameters see ['change backtest parameters'](#change_backtest_parameters) ). You also need to ensure that you have the data you need for any new instruments. See ['use my own data'](#create_my_own_data) below.


### Change the configuration file

You should make a new config file by copying this [one](/systems/futures/futuresconfig.yaml). Best practice is to save this as `pysystemtrade/systems/users/your_name/this_system_name/config.yaml` (you'll need to create this directory).

You can then change this section of the config:

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

*At this stage you'd also need to recalculate the diversification multiplier (see chapter 11 of my book). The ability to do this automatically will be included in a future version of the code*

You should then create a new system which points to the new config file:

```python
from syscore.fileutils import get_pathname_for_package
from sysdata.configdata import Config

my_config=Config(get_pathname_for_package("systems", ["users", "your_name", "this_system_name", "config.yaml"]))

from systems.futures.basesystem import futures_system
system=futures_system(config=my_config)
```

### Change the configuration object

We can also modify the configuration object in the system directly:

```python
from systems.futures.basesystem import futures_system
system=futures_system()
new_config=system.config

new_weights=dict(SP500=0.5, KR10=0.5) ## create new weights
new_idm=1.1 ## new IDM

new_config.instrument_weights=new_weights
new_config.instrument_div_multiplier=new_idm

system=futures_system(config=new_config)

```



## How do I....Create my own trading rule

You should read the relevant guide section ['rules'](#rules) as there is much more to this subject than I will explain briefly here.


### Writing the function


A trading rule consists of:

- a function
- some optional data
- some optional key word arguments


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

We can eithier modify the YAML file or the configuration object we've already loaded into memory. See ['changing backtest parameters'](change_backtest_parameters) for more details. If you want to use a YAML file you need to first save the function into a .py module, so it can be referenced by a string (we can also use this method for python).

For example the rule imported like this:

```python
from systems.futures.rules import ewmac
```

Can also be referenced like this: `systems.futures.rules.ewmac`

Also note that the list of data for the rule will also be in the form of string references. If no data is included, then the system will default to passing a single data item - the price of the instrument.

Finally if other_arg keyword arguments are missing then the function will use it's own defaults.
 
At this stage we can also remove any trading rules that we don't want. We also need to modify the forecast scalars, forecast weights and probably the forecast diversification multiplier (later versions of this project will provide methods for doing this automatically).

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
forecast_scalars: 
  ..... existing rules ....
  new_rule=10.6
#
forecast_weights:
  .... existing rules ...
  new_rule=0.10
#
forecast_div_multiplier=1.5
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
config.forecast_scalars['new_rule']=7.0
config.forecast_weights=dict(.... , new_rule=0.10)  ## all forecast weights will need to be updated
config.forecast_div_multiplier=1.5

## put into a new system
```




<a name="create_my_own_data">
## How do I....Use different data or instruments
</a>

Currently the only data that is supported is .csv files for futures stitched prices (eg US10_price.csv), fx (eg AUDUSDfx.csv), and futures specific (eg AEX_carrydata.csv), data. A set of data is provided in [pysystem/sysdata/legacycsv](/sysdata/legacycsv) which is several months old. It's my intention to update this and try to keep it reasonably current with each release.

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
from syscore.fileutils import get_pathname_for_package
from systems.futures.basesystem import futures_system

data=csvFuturesData(get_pathname_for_package("private", ["system_name", "data"]))
system=futures_system(data=data)
```

There is more detail about using .csv files [here](#csv).

If you want to get data from a different place (eg a database, yahoo finance, broker, quandl...) you'll need to [create your own Data object](#create_data). Note that I intend to add support for a sql3 database, Interactive brokers and quandl data in the future.

If you want to use a different set of data values (eg equity EP ratios, interest rates...) you'll need to [create your own Data object](#create_data).


## Save my work

To remain organised it's good practice to save any work into a directory like `pysystemtrade/private/this_system_name/` (you'll need to create a couple of directories first). If you plan to contribute to github, just be careful to avoid adding 'private' to your commit ( [you may want to read this](https://24ways.org/2013/keeping-parts-of-your-codebase-private-on-github/) ). 

Because instances of **System()** encapsulate the data and functions you need, you can *pickle* them (but you might want to read about [system caching](#caching) before you reload them). 

```python
from systems.futures.basesystem import futures_system
import pickle
from syscore.fileutils import get_pathname_for_package

filename=get_pathname_for_package("systems", ["users", "your_name", "this_system_name", "system.pck"]))

with open(filename, 'wb') as outfile:
   pickle.dump(system)    
```

You can also save a config object into a yaml file - see [saving configuration](#save_config).



# Guide

The guide section explains in more detail how each part of the system works. Each section is split into parts that get progressively trickier; varying from using the standard objects that are supplied up to writing your own.

## Data 

A data object is used to feed data into a system. Data objects work with a particular **kind** of data (normally asset class specific, eg futures) from a particular **source** (for example .csv files, databases and so on).

### Using the standard data objects

Only one kind of specific data object is provided with the system in the current version - csvFutures. 

#### Generic data objects

You can get use data objects directly:

*These commands will work with all data objects - the csvFutures version is used as an example.*

```python
from sysdata.csvdata import csvFuturesData

data=csvFuturesData()

## getting data out
data.get_instrument_price(instrument_code)
data[instrument_code] ## does the same thing as get_instrument_price

data.get_instrument_list()
data.keys() ## also gets the instrument list

data.get_value_of_block_price_move(instrument_code)
data.get_instrument_currency(instrument_code)
data.get_fx_for_instrument(instrument_code, base_currency) # get fx rate between instrument currency and base currency

## using with a system
from systems.futures.basesystem import futures_system
system=futures_system(data=data)

```

Or within a system:

```python
## using with a system
from systems.futures.basesystem import futures_system
system=futures_system(data=data)

system.data.get_instrument_currency(instrument_code) # and so on
```

When specifying a data item within a trading [rule](#rules) you should omit the system eg `data.get_instrument_price`.



<a name="csvdata">
#### The csvFuturesData object 
</a>

The csvFuturesData object works like this:

```python
from sysdata.csvdata import csvFuturesData

## with the default folder
data=csvFuturesData()

## OR with a particular folder
from syscore.fileutils import get_pathname_for_package
data=csvFuturesData(get_pathname_for_package("private", ["system_name", "data"]))

## getting data out
data.get_instrument_raw_carry_data(instrument_code) ## specific data for futures

## using with a system
from systems.futures.basesystem import futures_system
system=futures_system(data=data)
system.data.get_instrument_raw_carry_data(instrument_code)
```

The pathname must contain .csv files of the following four types (where code is the instrument_code):

1. Static data- instrument_config.csv: headings: Instrument, Pointsize, AssetClass, Currency
2. Price data- code_price.csv: headings: DATETIME, PRICE
3. Futures data - code_carrydata.csv (eg AEX_carrydata): headings: DATETIME, PRICE,CARRY,CARRY_CONTRACT PRICE_CONTRACT
4. Currency data - ccy1ccy2fx.csv (eg AUDUSDfx): headings: DATETIME, FXRATE

DATETIME should be something that pandas.to_datetime can parse. Note that the price in (2) is the continously stitched price, whereas the price in (3) is the price of the contract we're currently trading. 

At a minimum we need to have a currency file for each instrument's currency against the default (defined as "USD"); and for the currency of the account we're trading in (i.e. for a UK investor you'd need a GBPUSD file). However if cross rate files are available they will be used.

See [pysystem/sysdata/legacycsv](/sysdata/legacycsv) for files you can modify.


### Creating your own data data objects

You should be familiar with the python object orientated idiom before reading this section.

The [Data](/sysdata/data) object is the base class for data. From that we inherit data type specific classes such as the [FuturesData](/sysdata/futuresdata) object. These in turn are inherited from for specific data sources, such as [csvFuturesData](/sysdata/csvdata).

So, you should consider whether you need a new type of data, a new source of data or both. You may also wish to extend an existing class. For example if you wished to add some fundamental data for futures you might define: `class FundamentalFutures(FuturesData)`.

This might seem a palaver, and it's tempting to skip and just inherit from Data() directly, however once your system is up and running it is very convenient to have the possibility of multiple data sources and this process ensures they keep a consistent API for a given data type.

#### The Data() class

Methods that you'll probably want to override:

- `get_instrument_price` Returns Tx1 pandas data frame
- `get_instrument_list` Returns list of str
- `get_value_of_block_price_move` Returns float
- `get_instrument_currency`: Returns str
- `_get_fx_data(currency1, currency2)`  Returns Tx1 pandas data frame

You should not override get_fx_for_instrument, or any of the other private fx related methods. Once , then these methods will interact to give the correct fx rate for get_fx_for_instrument(), handling cross rates and working them out when needed.
 

#### Creating a new type of data (or extending an existing one)

Here is an annotated extract of the FuturesData class illustrating how it extends Data:

```python

class FuturesData(Data):

    def get_instrument_raw_carry_data(self, instrument_code):
	### a method to get data specific for this asset class
        ### normally we'd override this in the inherited method for a particular 
        ###

        raise Exception("You have created a FuturesData() object; you probably need to replace this method to do anything useful")


    def __repr__(self):
        ### modify this method so we can tell what type of data we have
        return "FuturesData object with %d instruments" % len(self.get_instrument_list())    
```

#### Creating a new data source (or extending an existing one)

Here is an annotated extract of the csvFuturesData class, illustrating how it extends FuturesData and Data for a specific source:

```python
class csvFuturesData(FuturesData):
    """
        Get futures specific data from legacy csv files
        
        Extends the FuturesData class for a specific data source 
    
    """
    
    def __init__(self, datapath=None):
        
        if datapath is None:            
            datapath=get_pathname_for_package(LEGACY_DATA_MODULE, [LEGACY_DATA_DIR])

        """
        Most Data objects that read data from a specific place have a 'source' of some kind
        Here it's a directory
	We need to store it for future reference
        """
        setattr(self, "_datapath", datapath)
    
    
    def get_instrument_price(self, instrument_code):
        """
        Get instrument price. Overrides Data() method
        """

    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

	Overrides FuturesData method
        """

    def _get_instrument_data(self):
        """
        Get a data frame of interesting information about instruments
        Private method used by other methods
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
        Overrides Data() method
	
```

## Configuration

Configuration (config) objects determine how a system behaves. Configuration objects are very simple; they have attributes which contain eithier parameters, or nested groups of parameters.

### Creating a configuration object

There are three main ways to create a configuration object:

1. By pulling in a dictionary
2. By pulling in a YAML file
3. From a 'pre-baked' system
4. By joining together multiple configurations in a list

#### Creating a configuration object with a dictionary

```python
from sysdata.configdata import Config

my_config_dict=dict(optionone=1, optiontwo=dict(a=3.0, b="beta", c=["a", "b"]), optionthree=[1.0, 2.0])
my_config=Config(my_config_dict)
```

There are no restrictions on what is nested in the dictionary. The section on [configuration options](#Configuration_options) explains what configuration options are available.

#### Creating a configuration object from a file

This simple file will reproduce the config we get from a dictionary in the example above.

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
my_config=Config("filename.yaml")
```


There are no restrictions on what is nested in the dictionary; although it is easier to use str, float, int, lists and dicts, and the standard project code only requires those (if you're a pyyaml expert you can do other python objects, but it won't be pretty). 

The section on [configuration options](#Configuration_options) explains what configuration options are available.


#### Creating a configuration object from a pre-baked system

```python
from systems.futures.basesystem import futures_system
system=futures_system()
new_config=system.config
```

Under the hood this is effectively getting a configuration from a .yaml file - [this one](/systems/futures/futuresconfig.yaml).


#### Creating a configuration object from a list

We can also pass a list into Config(), where each item of the list contains a dict or filename. For example we could do this with the simple example above:

```python
from sysdata.configdata import Config

my_config_dict=dict(optionone=1, optiontwo=dict(a=3.0, b="beta", c=["a", "b"]), optionthree=[1.0, 2.0])

my_config=Config(["filename.yaml", my_config_dict])
```

However, since there are overlapping keynames in these 

<a name="defaults">
### Defaults
</a>

Many (but not all) configuration parameters have defaults which are used by the system if the parameters are not in the object. These can be found in the file [pysystemtrade/systems/provided/defaults.yaml](/systems/provided/defaults.yaml). The section on [configuration options](#Configuration_options) explains what the defaults are.


### Viewing configuration parameters

The keys in the top level dictionary will become attributes of the config. For example using the simple config above:

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

You can also add new configuration items in the same way:

```python
my_config.optionfour=20.0
setattr(my_config, "optionfour", 20.0) ## if you prefer
```

### Using configuration in a system

Once we're happy with our configuration we can use it in a system:

```python
from systems.futures.basesystem import futures_system
system=futures_system(config=new_config)
```


### Including your own configuration options

If you develop your own stages or modify existing ones you might want to include configuration options. Here's what your code should do:


```python
from systems.defaults import system_default

## Then assuming your config item is called my_config_item

parameter=system.config.my_config_item

## Or if you use a default
try:
   parameter=system.config.my_config_item
except:
   parameter=system_defaults.my_config_item

## You can also use nested configuration items, eg dict

parameter=system.config.my_config_dict[instrument_code]

## Lists also work. 

parameter=system.config.my_config_list

## (Note: it's possible to do tuples, but the YAML is quite messy)

```

You would then need to add the following kind of thing to your configs:

```
my_config_item: "ni"
my_config_dict:
   US10: 45.0
   US10: 0.10
my_config_list:
   - "first item"
   - "second item"
```

Similarly if you wanted to use defaults you'll also need to update the [defaults.yaml file](/systems/provided/defaults.yaml).


<a name="save_config">
### Saving configurations
</a>

You can also save a config object into a yaml file:

```python
from systems.futures.basesystem import futures_system
import yaml
from syscore.fileutils import get_pathname_for_package

system=futures_system()
my_config=system.config

## make some changes to my_config here

filename=get_pathname_for_package("systems", ["users", "your_name", "this_system_name", "config.yaml"]))

with open(filename, 'w') as outfile:
    outfile.write( yaml.dump(my_config, default_flow_style=True) )
```

This is useful if you've been playing with a backtest configuration, and want to record the changes you've made. Note this will save trading rule functions as functions; this may not work and it will also be ugly. So you should use strings to define rule functions (see [rules](#rules) for more information)

A future version of this project will allow you to save the final optimised weights for instruments and forecasts into fixed weights for live trading.

### Modifying the configuration class

It shouldn't be neccessary to modify the configuration class since it's deliberately lightweight and flexible.


## System



<a name="caching">
### System Caching
</a>

The data object doesn't actually store any information. So any caching will be done in the system.

## Stages: General


<a name="stage_wiring">
### Stage 'wiring'
</a>

## Stage: Raw data

### Using the existing raw data object

<a name="vol_calc">
#### Volatility calculation
</a>

<a name="rules">
### Stage: Rules
</a>

## Stage: Accounting

<a name="standard_accounts_stage">
### Using the standard accounts stage
</a>



# Summary information



<a name="table_system_stage_methods">
## Table of standard system.data and system.stage methods
</a>

This table lists all the methods that can be used to get data out of a system and its 'child' stages. Although strictly speaking `system.data` is not a stage, it is included for completeness and because other stages will make use of it.


### Explanation of columns


For brevity the name of the system instance is omitted from the 'call' column. So for example to get the instrument price for Eurodollar from the data object, which is marked as *data.get_instrument_price* we would do something like this:

```python
from systems.futures.basesystem import futures_system
name_of_system=futures_system()
name_of_system.data.get_instrument_price("EDOLLAR")
```

Standard methods are in all systems. Non standard methods are for stage classes inherited from the standard class, eg the raw data method specific to futures.

Common arguments are:

- instrument_code: A string indicating the name of the instrument
- rule_variation_name: A string indicating the name of the trading rule variation

Types are one or more of D, I, O:

- **D**iagnostic: Exposed method useful for seeing intermediate calculations
- Key **I**nput: A method which gets information from another stage. See [stage wiring](#stage_wiring). The description will list the source of the data.
- Key **O**utput: A method whose output is used by other stages. See [stage wiring](#stage_wiring). Note this excludes items only used by specific trading rules (noteably rawdata.daily_annualised_roll)

Private methods are excluded from this table.


### Data object


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| data.get_instrument_price | Standard  | instrument_code        | D,O  | Price used for trading rule analysis (backadjusted if relevant)|
| data.get_instrument_list  | Standard  |                        |  D   | List of instruments available in data set (not all will be used for backtest)|
| data.get_value_of_block_price_move| Standard | instrument_code | D,O  | How much does a $1 (or whatever) move in the price of an instrument block affect it's value? |
| data.get_instrument_currency|Standard | instrument_code | D,O | What currency does this instrument trade in? |
| data.get_fx_for_instrument  |Standard | instrument_code, base_currency | D, O | What is the exchange rate between the currency of this instrument, and some base currency? |
| data.get_instrument_raw_carry_data | Futures | instrument_code | D, O | Returns a dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT |



### Raw data stage

        
| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| rawdata.get_instrument_price | Standard  | instrument_code        | I  | data.get_instrument_price|
| rawdata.daily_prices | Standard |     instrument_code         | D,O | Price resampled to end of day |
| rawdata.daily_denominator_price | Standard | instrument_code  |  O | Price used to calculate % volatility (for futures the current contract price) |
| rawdata.daily_returns | Standard | instrument_code | D, O | Daily returns in price units|
| rawdata.daily_returns_volatility | Standard | instrument_code | D,O | Daily standard deviation of returns in price units |
| rawdata.get_daily_percentage_volatility | Standard | instrument_code | D,O | Daily standard deviation of returns in % (10.0 = 10%) |
| rawdata.norm_returns | Standard            | instrument_code | D | Daily returns normalised by vol (1.0 = 1 sigma) |
| rawdata.get_instrument_raw_carry_data | Futures | instrument_code | I | data.get_instrument_raw_carry_data | 
| rawdata.raw_futures_roll| Futures | instrument_code | D |  | 
| rawdata.roll_differentials | Futures | instrument_code | D |  |
| rawdata.annualised_roll | Futures | instrument_code | D | Annualised roll |
| rawdata.daily_annualised_roll | Futures | instrument_code | D | Annualised roll. Used for carry rule. |
 


### Trading rules stage (chapter 7 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| rules.trading_rules | Standard  |         | D  | List of trading rule variations |
| rules.get_raw_forecast | Standard | instrument_code, rule_variation_name | D,O| Get forecast (unscaled, uncapped) |


### Forecast scaling and capping stage (chapter 7 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| forecastScaleCap.get_raw_forecast | Standard  | instrument_code, rule_variation_name        | I  | rules.get_raw_forecast |
| forecastScaleCap.get_forecast_scalar | Standard | instrument_code, rule_variation_name        | D  | Get the scalar to use for a forecast |
| forecastScaleCap.get_forecast_cap | Standard | instrument_code, rule_variation_name        | D  | Get the maximum allowable forecast |
| forecastScaleCap.get_scaled_forecast | Standard | instrument_code, rule_variation_name        | D  | Get the forecast after scaling (after capping) |
| forecastScaleCap.get_capped_forecast | Standard | instrument_code, rule_variation_name        | D, O  | Get the forecast after scaling (after capping) |


### Combine forecasts stage (chapter 8 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| combForecast.get_capped_forecast | Standard  | instrument_code, rule_variation_name        | I  | forecastScaleCap.get_capped_forecast |
| combForecast.get_forecast_weights | Standard  | instrument_code        | D  | Forecast weights |
| combForecast.get_forecast_diversification_multiplier | Standard  | instrument_code        | D  | Get diversification multiplier |
| combForecast.get_combined_forecast | Standard  | instrument_code        | D,O  | Get weighted average of forecasts for instrument |



### Position sizing stage (chapters 9 and 10 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| positionSize.get_combined_forecast | Standard  | instrument_code        | I  | combForecast.get_combined_forecast |
| positionSize.get_price_volatility | Standard | instrument_code        | I  | rawdata.get_daily_percentage_volatility (or data.get_combined_forecast) |
| positionSize.get_instrument_sizing_data | Standard | instrument_code        | I  | rawdata.get_rawdata.daily_denominator_price( (or data.get_instrument_price); data.get_value_of_block_price_move |
| positionSize.get_fx_rate | Standard | instrument_code | I | data.get_fx_for_instrument |
| positionSize.get_daily_cash_vol_target | Standard |  | D | Dictionary of base_currency, percentage_vol_target, notional_trading_capital, annual_cash_vol_target, daily_cash_vol_target |
| positionSize.get_block_value | Standard | instrument_code | D | Get value of a 1% move in the price |
| positionSize.get_instrument_currency_vol | Standard | instrument_code |D | Get daily volatility in the currency of the instrument |
| positionSize.get_instrument_value_vol | Standard | instrument_code |D | Get daily volatility in the currency of the trading account |
| positionSize.get_volatility_scalar | Standard | instrument_code | D |Get ratio of target volatility vs volatility of instrument in instrument's own currency |
| positionSize.get_subsystem_position| Standard | instrument_code | D, O |Get position if we put our entire trading capital into one instrument |



### Portfolio stage (chapter 11 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| portfolio.get_subsystem_position| Standard | instrument_code | I |positionSize.get_subsystem_position |
| portfolio.get_instrument_weights| Standard |  | D |Get instrument weights |
| portfolio.get_instrument_diversification_multiplier| Standard |  | D |Get instrument div. multiplier |
| portfolio.get_notional_position| Standard | instrument_code | D |Get the *notional* position (with constant risk capital; doesn't allow for adjustments when profits or losses are made) |



### Accounting stage


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| accounts.get_notional_position| Standard |  | I | portfolio.get_notional_position|



<a name="Configuration_options">
## Configuration options
</a>

Below is a list of all configuration options for the system. The 'Yaml' section shows how they appear in a yaml file. The 'python' section shows an example of how you'd modify a config object in memory having first created it, like this:


```python
## Method one: from an existing system
from systems.futures.basesystem import futures_system
system=futures_system()
new_config=system.config

## Method two: from a config file
from syscore.fileutils import get_pathname_for_package
from sysdata.configdata import Config

my_config=Config(get_pathname_for_package("systems", ["users", "your_name", "this_system_name", "config.yaml"]))

## Method three: with a blank config
from sysdata.configdata import Config
my_config=Config()
```

Each section also shows the default options, which you could change [here](#defaults).

When modifying a nested part of a config object, you can of course replace it wholesale:

```python
new_config.instrument_weights=dict(SP500=0.5, US10=0.5))
new_config
```

If you do this make sure that the config element you've replaced has all the keys it requires.

Or just in part:

```python
new_config.instrument_weights['SP500']=0.2
new_config
```
If you do this make sure the rest of the config is consistent with what you've done. In eithier case, it's a good idea to display the modified config and make sure you're happy with it.



### Raw data stage

#### Volatility calculation
Represented as: dict of str, int, or float. Keywords: Parameter names

The function used to calculate volatility, and any keyword arguments passed to it. Note if any elements are missing the system won't fallback on the defaults, instead the function's own defaults will be used. See ['volatility calculation'](#vol_calc) for more information. 

*func* is required, other keywords are optional.

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

### Rules stage

#### Trading rules
Represented as: dict of dicts, each representing a trading rule. Keywords: trading rule variation names.

The set of trading rules. A trading rule definition consists of a dict containing: a *function* identifying string, an optional list of *data* identifying strings, and *other_args* an optional dictionary containing named paramters to be passed to the function. This is the only method that can be used for YAML.

There are numerous other ways to define trading rules using python code. See ['Rules'](#rules) for more detail.

Note that *forecast_scalar* isn't part of the trading rule definition, but if included here will be used instead of the seperate 'config.forecast_scalar' parameter (see the next section). 

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

#### Forecast scalar
Represented as: dict of floats. Keywords: trading rule variation names.

The forecast scalar to apply to a trading rule, if fixed scaling is being used. If undefined the default value of 1.0 will be used.

Scalars can be put inside trading rule definitions (this is the first place we look):

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

If not found there they can be put in seperately:

YAML: (example) 
```
forecast_scalars: 
   rule_name: 10.6
```

Python (example)
```python
config.forecast_scalars=dict(rule_name=10.6)
```

#### Forecast cap
Represented as: float

The forecast cap to apply to a trading rule. If undefined the default value of 20.0 will be used.


YAML: 
```
forecast_cap: 20.0
```

Python 
```python
config.forecast_cap=20.0
```

### Forecast combination stage

#### Forecast weights
Represented as: (a) dict of floats. Keywords: trading rule variation names.
                (b) dict of dicts, each representing the weights for an instrument. Keywords: instrument names

The forecast weights to be used to combine forecasts from different trading rule variations. These can be (a) common across instruments, or (b) specified differently for each instrument.

There are no default values for forecast weights.

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


#### Forecast diversification multiplier
Represented as: (a) float or (b) dict of floats with keywords: instrument_codes

This can be (a) common across instruments, or (b) we use a different one for each instrument (would be normal if instrument weights were also different).

If undefined a default value of 1.0 will be used.

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

### Position sizing stage

#### Capital scaling parameters 
Represented as: floats, int or str

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

#### Instrument weights
Represented as: dict of floats. Keywords: instrument_codes

The instrument weights used to combine different instruments together into the final portfolio. 

There are no default values for instrument weights.

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

#### Instrument diversification multiplier
Represented as: float

If undefined a default value of 1.0 will be used.

YAML: 
```
instrument_div_multiplier: 1.0
```

Python 
```python
config.instrument_div_multiplier=1.0
```

