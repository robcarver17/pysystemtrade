# User guide

This guide is divided into two parts. The first 'How do I?' explains how to do many common tasks. The second part 'Reference' details the relevant parts of the code, and explains how to modify or create new parts.  

## How do I?

### Create a standard futures backtest

This creates the staunch systems trader example definied in chapter 15 of my book, using the csv data that is provided.

```python
from systems.futures.basesystem import futures_system
system=futures_system()
```



### See intermediate results from a backtest

This will give you the raw forecast (before scaling and capping) of one of the EWMAC rules for Eurodollar futures in the standard futures backtest:

```python
from systems.futures.basesystem import futures_system
system=futures_system()
system.rules.get_raw_forecast("EDOLLAR", "ewmac64_256")
```

For a complete list of possible , see [this table](#table_system_stage_methods)


### See how profitable a backtest was


### Run a backtest on a different set of instruments



### Change backtest parameters 


### Save my work


### Create my own trading rule


### Create my own data


### Change the way a stage works



### Include a new stage, or remove an old one





## Reference

### Data 

### Configuration

### System

### Stages: General


<a name="stage_wiring">
#### Stage 'wiring'
</a>

### Stage: Raw data

### Stage: Rules

### Stage:

### Summary information

<a name="table_system_stage_methods">
#### Table of standard system.data and system.stage methods
</a>

This table lists all the methods that can be used to get data out of a system and its 'child' stages. Although strictly speaking `system.data` is not a stage, it is included for completeness and because other stages will make use of it.


##### Explanation of columns


For brevity the name of the system instance is omitted from the 'call' column. So for example to get the instrument price for Eurodollar from the data object, which is marked as *data.get_instrument_price* we would do something like this:

```python
from systems.futures.basesystem import futures_system
name_of_system=futures_system()
name_of_system.data.get_instrument_price("EDOLLAR")
```

Standard methods are in all systems. Non standard methods are for stage classes inherited from the standard class, eg the raw data method specific to futures.

Common arguments are:

- instrument_code: A string indicating the name of the instrument
- rule_name: A string indicating the name of the trading rule variation

Types are one or more of D, I, O:

- **D**iagnostic: Exposed method useful for seeing intermediate calculations
- Key **I**nput: A method which gets information from another stage. See [stage wiring](#stage_wiring). The description will list the source of the data.
- Key **O**utput: A method whose output is used by other stages. See [stage wiring](#stage_wiring).

Private methods are excluded from this table.


##### Data object

| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| data.get_instrument_price | Standard  | instrument_code        | D,O  | Price used for trading rule analysis (backadjusted if relevant)|
| data.get_instrument_list  | Standard  |                        |  D   | List of instruments available in data set (not all will be used for backtest)|
| data.get_value_of_block_price_move| Standard | instrument_code | D,O  | How much does a $1 (or whatever) move in the price of an instrument block affect it's value? |
| data.get_instrument_currency|Standard | instrument_code | D,O | What currency does this instrument trade in? |
| data.get_fx_for_instrument  |Standard | instrument_code, base_currency | D, O | What is the exchange rate between the currency of this instrument, and some base currency? |
| data.get_instrument_raw_carry_data | Futures | instrument_code | D, O | Returns a dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT |

##### Raw data object
        
| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| rawdata.get_instrument_price | Standard  | instrument_code        | I  | data.get_instrument_price|
| rawdata.daily_prices | Standard |     instrument_code         | D,O | Price resampled to end of day |
| rawdata.daily_denominator_price | Standard | instrument_code  |  O | Price used to calculate % volatility (for futures the current contract price) |
| rawdata.daily_returns | Standard | instrument_code | D, O | Daily returns in price units|
| rawdata.daily_returns_volatility | Standard | instrument_code | D,O | Daily standard deviation of returns in price units |
| rawdata.get_daily_percentage_volatility | Standard | instrument_code | D,O | Daily standard deviation of returns in % (10.0 = 10%) |
| rawdata.norm_returns | Standard            | instrument_code | D | Daily returns normalised by vol (1.0 = 1 sigma) |

#####
