# User guide

This guide is divided into two parts. The first 'How do I?' explains how to do many common tasks. The second part 'Reference' details the relevant parts of the code, and explains how to modify or create new parts.  

## How do I?

### Find out



### Create a standard futures backtest

This creates the staunch systems trader example defined in chapter 15 of my book, using the csv data that is provided, and gives you the position in the Eurodollar market:

```python
from systems.futures.basesystem import futures_system
system=futures_system()
system.portfolio.get_notional_forecast("EDOLLAR")
```

### See intermediate results from a backtest

This will give you the raw forecast (before scaling and capping) of one of the EWMAC rules for Eurodollar futures in the standard futures backtest:

```python
from systems.futures.basesystem import futures_system
system=futures_system()
system.rules.get_raw_forecast("EDOLLAR", "ewmac64_256")
```

For a complete list of possible intermediate results, see [this table](#table_system_stage_methods) and look for rows marked with **D** for diagnostic.


### See how profitable a backtest was

```python
from systems.futures.basesystem import futures_system
system=futures_system()
system.accounts.portfolio.stats() ## see some statistics
system.accounts.portfolio.curve().plot() ## plot an account curve
system.accounts.portfolio.instrument().stats() ## produce statistics for all instruments
system.accounts.portfolio.instrument().plot() ## plot an account curve for each instrument
```

For more information on what statistics are available, see the [relevant reference section](#standard_accounts_stage).


### Run a backtest on a different set of instruments

You need to change the instrument weights in the configuration. Only instruments with weights have positions produced for them. There are two easy ways to do this - change the config file, or the config object already in the system (for more on changing config parameters see ['change backtest parameters'](#change_backtest_parameters) ). You also need to ensure that you have the data you need for any new instruments. See ['create my own data'](#create_my_own_data) below.


#### Change the configuration file

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

#### Change the configuration object

We can also modify the configuration object in the system directly:

```python
from systems.futures.basesystem import futures_system
system=futures_system()

new_weights=dict(SP500=0.5, KR10=0.5) ## create new weights
new_idm=1.1 ## new IDM

system.config.instrument_weights=new_weights
system.config.instrument_div_multiplier=new_idm
```

 
<a name="change_backtest_parameters">
### Change backtest parameters 
</a>

The backtest looks for its configuration information 

1. Arguments passed when creating a stage object
2. Elements in the configuration ob
3. Project defaults 

This suggests that you can modify the systems behaviour in any of the following ways:

1. Create a new stage object, passing in the 
2. Change
3. Change the configuration object 
4. Change the project defaults (not recommended)

For the time 

If you

### Save my work


### Create my own trading rule


<a name="create_my_own_data">
### Create my own data
</a>


### Change the way a stage works



### Include a new stage, or remove an old one





## Reference

### Data 

### Configuration


<a name="config_instr_weights">
#### Instrument weights, and diversification multiplier
</a>

### System

### Stages: General


<a name="stage_wiring">
#### Stage 'wiring'
</a>

### Stage: Raw data

### Stage: Rules

### Stage: Accounting

<a name="standard_accounts_stage">
#### Using the standard accounts stage
</a>



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
- rule_variation_name: A string indicating the name of the trading rule variation

Types are one or more of D, I, O:

- **D**iagnostic: Exposed method useful for seeing intermediate calculations
- Key **I**nput: A method which gets information from another stage. See [stage wiring](#stage_wiring). The description will list the source of the data.
- Key **O**utput: A method whose output is used by other stages. See [stage wiring](#stage_wiring). Note this excludes items only used by specific trading rules (noteably rawdata.daily_annualised_roll)

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



##### Raw data stage

        
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
 


##### Trading rules stage (chapter 7 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| rules.trading_rules | Standard  |         | D  | List of trading rule variations |
| rules.get_raw_forecast | Standard | instrument_code, rule_variation_name | D,O| Get forecast (unscaled, uncapped) |


 
##### Forecast scaling and capping stage (chapter 7 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| forecastScaleCap.get_raw_forecast | Standard  | instrument_code, rule_variation_name        | I  | rules.get_raw_forecast |
| forecastScaleCap.get_forecast_scalar | Standard | instrument_code, rule_variation_name        | D  | Get the scalar to use for a forecast |
| forecastScaleCap.get_forecast_cap | Standard | instrument_code, rule_variation_name        | D  | Get the maximum allowable forecast |
| forecastScaleCap.get_scaled_forecast | Standard | instrument_code, rule_variation_name        | D  | Get the forecast after scaling (after capping) |
| forecastScaleCap.get_capped_forecast | Standard | instrument_code, rule_variation_name        | D, O  | Get the forecast after scaling (after capping) |



##### Combine forecasts stage (chapter 8 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| combForecast.get_capped_forecast | Standard  | instrument_code, rule_variation_name        | I  | forecastScaleCap.get_capped_forecast |
| combForecast.get_forecast_weights | Standard  | instrument_code        | D  | Forecast weights |
| combForecast.get_forecast_diversification_multiplier | Standard  | instrument_code        | D  | Get diversification multiplier |
| combForecast.get_combined_forecast | Standard  | instrument_code        | D,O  | Get weighted average of forecasts for instrument |



##### Position sizing stage (chapters 9 and 10 of book)


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



##### Portfolio stage (chapter 11 of book)


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| portfolio.get_subsystem_position| Standard | instrument_code | I |positionSize.get_subsystem_position |
| portfolio.get_instrument_weights| Standard |  | D |Get instrument weights |
| portfolio.get_instrument_diversification_multiplier| Standard |  | D |Get instrument div. multiplier |
| portfolio.get_notional_position| Standard | instrument_code | D |Get the *notional* position (with constant risk capital; doesn't allow for adjustments when profits or losses are made) |



##### Accounting stage


| Call                              | Standard?| Arguments       | Type | Description                                                    |
|:-------------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| accounts.get_notional_position| Standard |  | I | portfolio.get_notional_position|



#### System parameters

Configuration options, and how to apply through arguments and in config.

