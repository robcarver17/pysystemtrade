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

For a complete list of possible , see [this table](#Table_of_standard_system.stage_methods)


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

### Stage: Raw data

### Stage: Rules

### Stage:

### Summary information

#### Table of standard system.stage methods


