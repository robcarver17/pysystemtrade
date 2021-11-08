This document describes how we should choose which instruments to trade, and how this is all configured.

# Different instrument sets

Different sets of instruments are used for different purposes:

- The superset of all instruments we can use are defined in the instrument configuration (a .csv version of which lives here)
- When sampling instrument prices in production, we use a subset consisting of the current list of instruments already saved with multiple prices
- When pulling in back adjusted prices into a simulation environment or update_systems production script, we use a subset consisting of the current list of instruments that have adjusted prices saved (which may be different in a database environment, but for .csv will be the prices here)
- Within that simulation environment we can further exclude different instruments for different reasons


# The global superset of all instruments

This will include everything you'd potentially want to trade now or in the future. The list provided in the repo is very exhaustive. There isn't much value in adding instruments to this speculatively, except perhaps to see off future name conflicts.

# The list of instruments we are sampling

This is keyed off the multiple instruments database. This should be as extensive as you can manage, as it's always worth collecting price data speculatively and often a pain to backfill historic data.

# Instruments we have adjusted prices for, used for simulation and production system backtest raw data

If they're both coming from a database, then this in principal should be the same as the previous list, however if you use .csv prices for simulated backtesting then you might have a different set of instruments. Obviously try and avoid this! (Unless it's deliberate, eg you're doing a quick and dirty backtest on a subset of instruments).

```python
from systems.provided.futures_chapter15.basesystem import *
config = Config()
system = futures_system(config = config)
instruments_with_adj_prices = system.data.get_instrument_list()
"SP500" in instruments_with_adj_prices
*True*
```


# Instruments used for simulation and production system backtests

This is where it gets complicated :-) Basically we start with the instruments we have adjusted prices for, and then have two further subsets of those:

- Always excluded instruments. At this stage we drop  *duplicate_instruments* and *ignored_instruments*.
- Excluded for optimisation purposes. We also drop here instruments with *trading_restrictions* and *bad_markets*

## Always excluded

Always excluded means exactly that- the system literally can't see them. Continuing from the earlier example:

```python
from systems.provided.futures_chapter15.basesystem import *
config = Config()
system = futures_system(config = config)
instruments_with_adj_prices = system.data.get_instrument_list()
"SP500" in instruments_with_adj_prices
*True*
instruments_in_system = system.get_instrument_list()
"SP500" in instruments_in_system
*False*
```


### Duplicated instruments

### Ignored instruments


## 


## A note about configuration


# Deciding which duplicate instruments to use



# Deciding which are 'bad' markets

See the futures data document for more detail.

INCOMPLETE SCRATCH JOTTINGS RIGHT NOW!


config
(feels like this could be more bulletproof eg override complete sections??)


You might want to calculate forecasts for certain instruments (so don't include them in `ignore_instruments`), but not actually trade them.



If you include the config element `allocate_zero_instrument_weights_to_these_instruments` then those instruments will have a zero instrument weight calculated, and the system will produce a zero desired position for them.


overrides

Overrides allow us to reduce positions for a given strategy, for a given instrument (across all strategies), or for a given instrument & strategy combination. They are either:

- a multiplier, between 0 and 1, by which we multiply the desired . A multiplier of 1 is equal to 'normal', and 0 means 'close everything'
- a flag, allowing us only to submit trades which reduce our positions
- a flag, allowing no trading to occur in the given instrument.



#### Position limits

We can set the maximum allowable position that can be held in a given instrument, or by a specific strategy for an instrument. An instrument trade that will result in a position which exceeds this limit will be rejected (this occurs when run_strategy_order_generator is run). We can:


- Auto update spread cost configuration based on sampling and trades
- Suggest 'bad' markets (illiquid or costly)
- Suggest which duplicate market to use

