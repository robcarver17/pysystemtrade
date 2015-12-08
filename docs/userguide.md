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


The system name is omitted from the 'call' column. So for example to 

```python
from systems.futures.basesystem import futures_system
system=futures_system()
```

Standard methods are in all systems. Non standard methods are for stage classes inherited from the standard class, eg the raw data method specific to futures.

Arguments are:

- instrument_code: A string indicating the name of the instrument
- rule_name: A string indicating the name of the trading rule variation

Types are one or more of D, I, O:

- **D**iagnostic: Exposed method useful for seeing intermediate calculations
- Key **I**nput: A method which gets information from another stage. See [stage wiring](#stage_wiring).
- Key **O**utput: A method whose output is used by other stages. See [stage wiring](#stage_wiring).

Private methods are excluded from this table.


##### Data object

| Call                 | Standard? | Arguments       | Type | Description                                                    |
|:--------------------:|:---------:|:---------------:|:----:|:--------------------------------------------------------------:|
| get_instrument_price | Standard  | instrument_code | D,O  | Price used for trading rule analysis (backadjusted if relevant)|

