This document describes how we should choose which instruments to trade, and how this is all configured.

It will make no sense unless you've already read:

- [Backtesting with pysystemtrade](/docs/backtesting.md)
- [Storing futures and spot FX data](/docs/data.md)
- [Using pysystemtrade in production](/docs/production.md)

Table of Contents
=================

* [Different instrument sets](#different-instrument-sets)
* [The global superset of all instruments](#the-global-superset-of-all-instruments)
* [The list of instruments we are sampling](#the-list-of-instruments-we-are-sampling)
* [Instruments we have adjusted prices for, used for simulation and production system backtest raw data](#instruments-we-have-adjusted-prices-for-used-for-simulation-and-production-system-backtest-raw-data)
* [Instruments used for simulation and production system backtests](#instruments-used-for-simulation-and-production-system-backtests)
   * [The global list of instruments, when defined](#the-global-list-of-instruments-when-defined)
   * [Always excluded](#always-excluded)
      * [Duplicated instruments](#duplicated-instruments)
      * [Ignored instruments](#ignored-instruments)
   * [Excluded for optimisation](#excluded-for-optimisation)
      * [Untradeable](#untradeable)
      * [Bad markets](#bad-markets)
* [Operating in production](#operating-in-production)
   * [A note about configuration](#a-note-about-configuration)
   * [Reduce only and other constraints in static systems](#reduce-only-and-other-constraints-in-static-systems)
   * [Reduce only and other constraints in dynamic systems](#reduce-only-and-other-constraints-in-dynamic-systems)
* [Deciding which are 'bad' markets](#deciding-which-are-bad-markets)
   * [Check slippage costs are accurate](#check-slippage-costs-are-accurate)
   * [Get list of bad markets](#get-list-of-bad-markets)
* [Deciding which duplicate instruments to use](#deciding-which-duplicate-instruments-to-use)



# Different instrument sets

Different sets of instruments are used for different purposes:

- The superset of all instruments we can use are defined in the instrument configuration (a .csv version of which lives [here](/data/futures/csvconfig/instrumentconfig.csv))
- When sampling instrument prices in production, we use a subset consisting of the current list of instruments already saved with multiple prices
- When pulling in back adjusted prices into a simulation environment or update_systems production script, we use a subset consisting of the current list of instruments that have adjusted prices saved (which may be different in a database environment, but for .csv will be the prices [here](/data/futures/adjusted_prices_csv/))
- Within that simulation environment we can further exclude different instruments for different reasons


# The global superset of all instruments

This will include everything you'd potentially want to trade now or in the future. The list provided in the repo is very exhaustive. There isn't much value in adding instruments to this speculatively, except perhaps to see off future name conflicts.

# The list of instruments we are sampling

This is keyed off the multiple instruments database. This should be as extensive as you can manage given time and data costs constraints, as it's always worth collecting price data speculatively and often a pain to backfill historic data.

# Instruments we have adjusted prices for, used for simulation and production system backtest raw data

If they're both coming from a database, then this in principle should be the same as the previous list, however if you use .csv prices for simulated backtesting then you might have a different set of instruments. Obviously try and avoid this! (Unless it's deliberate, eg you're doing a quick and dirty backtest on a subset of instruments).

```python
from systems.provided.futures_chapter15.basesystem import *
config = Config()
system = futures_system(config = config)
instruments_with_adj_prices = system.data.get_instrument_list()
"SP500" in instruments_with_adj_prices
>True
```


# Instruments used for simulation and production system backtests

This is where it gets complicated :-) Basically we start with the instruments we have adjusted prices for, and then have three further subsets of those:

- The global list of instruments (when defined)
- The global list of instruments after dropping always excluded instruments. At this stage we drop  *duplicate_instruments* and *ignored_instruments*.
- The list of instruments after dropping those excluded for optimisation purposes. We drop here instruments with *trading_restrictions* and *bad_markets*

## The global list of instruments, when defined

If we load a default config that contains no instrument information, then in principle we'll have available every instrument with an adjusted price in the source we're using (sim .csv or database):

```python
from systems.provided.futures_chapter15.basesystem import *
config = Config() # using a default config so we know we have all instruments there in principle
system = futures_system(config = config)
instruments_with_adj_prices = system.data.get_instrument_list()
"SP500" in instruments_with_adj_prices
>True
```

However we normally don't want to run a backtest with everything, so there are two ways of restricting this subset. The first is to set explicit instrument weights:

```python
system.cache.delete_all_items()
system.config.instrument_weights = dict(BTP=.5, US2=.5)
system.get_instrument_list()
>['BTP', 'US2']
```

The second is to pass a list of instruments without weights, which is what you'd do if you were optimising:

```python
del(system.config.instrument_weights)
system.cache.delete_all_items()
system.config.instruments = ['US5', 'US10']
system.get_instrument_list()
>['US5', 'US10']
```

The code snips above make this is a good time to point out that, if you are moving from running a fixed system (i.e. fixed instrument weights) to running an estimated system (i.e. the system sets the weights), your config needs to specify a list of `instruments` *explicitly*.  The system will not presume that the set of instruments you were using in `instrument_weights` for a fixed system will be the same set of instruments you want to use for the estimated system (it will instead use all instruments for which it has data), so you need to set this config item directly, e.g.:

```python
system.config.instruments = list(system.config.instrument_weights.keys())
```


## Always excluded

We can take the global list and exclude instruments from it for various reasons. Always excluded means exactly that- the system literally can't see them.

```python
from systems.provided.futures_chapter15.basesystem import *
config = Config() # using a default config so we know we have all instruments there in principle
system = futures_system(config = config)
instruments_with_adj_prices = system.data.get_instrument_list()
"SP500" in instruments_with_adj_prices
>True
```

The system will log a bunch of stuff at this point 

```
Following instruments are 'duplicate_markets' and will be excluded from sim ['COPPER-mini', 'CORN_mini', 'CRUDE_W', 'GAS_US', 'GASOILINE_mini', 'GOLD', 'HEATOIL_mini', 'JGB_mini', 'JGB-SGX-mini', 'JPY_micro', 'JPY-SGX-TITAN', 'JPY-SGX', 'KOSPI_mini', 'KRWUSD_mini', 'NASDAQ', 'SILVER_mini', 'SOYBEAN_mini', 'SP500', 'TWD-mini', 'VIX_mini', 'WHEAT_mini'] 
Following instruments are marked as 'ignore_instruments': not included: ['EURIBOR']
```

Now lets' see what instruments we have.
```
"SP500" in system.get_instrument_list()
>False
```

Where has it gone?
```
"SP500" in system.get_list_of_instruments_to_remove()
> True
```

It's been removed. The S&P 500 future will play no further part in this backtest.


### Duplicated instruments

The S&P 500 is an example of a *duplicated instrument*. This is the e-mini contract (no explicit label as at the time it was the only one I traded), but we actually prefer the micro contract. Both contracts will have almost precisely the same price data. It's pointless to have duplicated data, and in fact dangerous since often when optimising or calibrating a parameter we take an average across instruments or estimate a correlation matrix.

```
"SP500_micro" in system.get_instrument_list()
> True
```


We can see the list of instruments we'll exclude:

```python
system.get_list_of_duplicate_instruments_to_remove()
> ['COPPER-mini', 'CORN_mini', 'CRUDE_W', 'GAS_US', 'GASOILINE_mini', 'GOLD', 'HEATOIL_mini', 'JGB_mini', 'JGB-SGX-mini', 'JPY_micro', 'JPY-SGX-TITAN', 'JPY-SGX', 'KOSPI_mini', 'KRWUSD_mini', 'NASDAQ', 'SILVER_mini', 'SOYBEAN_mini', 'SP500', 'TWD-mini', 'VIX_mini', 'WHEAT_mini']
```

These are defined in the following configuration element (values from default.yaml shown here):

```python
system.config.duplicate_instruments['exclude']
>{'copper': 'COPPER-mini', 'corn': 'CORN_mini', 'crude': 'CRUDE_W', 'gas_us': 'GAS_US', 'gasoiline': 'GASOILINE_mini', 'gold': 'GOLD', 'heatoil': 'HEATOIL_mini', 'jgb': ['JGB_mini', 'JGB-SGX-mini'], 'jpy': ['JPY_micro', 'JPY-SGX-TITAN', 'JPY-SGX'], 'kospi': 'KOSPI_mini', 'krwusd': 'KRWUSD_mini', 'nasdaq': 'NASDAQ', 'silver': 'SILVER_mini', 'soybean': 'SOYBEAN_mini', 'sp500': 'SP500', 'twd': 'TWD-mini', 'vix': 'VIX_mini', 'wheat': 'WHEAT_mini'}
system.config.duplicate_instruments['include']
>{'copper': 'COPPER', 'corn': 'CORN', 'crude': 'CRUDE_W_mini', 'gas_us': 'GAS_US_mini', 'gasoiline': 'GASOILINE', 'gold': 'GOLD_micro', 'heatoil': 'HEATOIL', 'jgb': 'JGB', 'jpy': 'JPY', 'kospi': 'KOSPI', 'krwusd': 'KRWUSD', 'nasdaq': 'NASDAQ_micro', 'silver': 'SILVER', 'soybean': 'SOYBEAN', 'sp500': 'SP500_micro', 'twd': 'TWD', 'vix': 'VIX', 'wheat': 'WHEAT'}
```

We could swap the two S&P contracts if we fancied it:

```python
system.cache.delete_all_items()
system.config.duplicate_instruments['exclude']['sp500']="SP500_micro"
system.config.duplicate_instruments['include']['sp500']="SP500"
"SP500" in system.get_instrument_list()
> True
"SP500_micro" in system.get_instrument_list()
> False
```

If you wanted to make this change permanent, you could modify the backtest and/or private_config.yaml files (see discussion about configuration below). Later in the document I explain how to determine which is the best duplicate instrument to use in any given pair.



### Ignored instruments

As well as duplicates, we might have other instruments we just don't like at all. Again, these will be absent from get_instrument_list. 

```python
"EURIBOR" in system.data.get_instrument_list() ## this won't show True if you're using .csv prices but I have EURIBOR prices in my database - just not very good ones
> True
system.config.exclude_instrument_lists['ignore_instruments'] # from the default config
>['EURIBOR']
system.get_list_of_ignored_instruments_to_remove()
>['EURIBOR']
"EURIBOR" in system.get_instrument_list()
False
```


## Excluded for optimisation

The list of instruments we have now will be used throughout the backtest. So we could get forecasts for them, even calculate subsystem account curves:

```
from systems.provided.futures_chapter15.estimatedsystem import *
system = futures_system()
system.config.instruments
>['EDOLLAR', 'US10', 'EUROSTX', 'MXP', 'CORN', 'V2X']
system.get_instrument_list()
>['CORN', 'EDOLLAR', 'EUROSTX', 'MXP', 'US10', 'V2X'] ## nothing has been excluded yet
system.portfolio.get_subsystem_position("V2X")
> ....
2021-10-05   -33.749026
2021-10-06   -34.279859
Freq: B, Length: 2314, dtype: float64
```

However it turns out that V2X is a 'bad market' and ought to be excluded for optimisation:

```
"V2X" in system.get_list_of_bad_markets()
>True
"V2X" in system.get_list_of_markets_not_trading_but_with_data()
>True
```

```
system.portfolio.get_instrument_list(for_instrument_weights=True)
>*** Following instruments are listed as trading_restrictions and/or bad_markets but still included in instrument weight optimisation: ***
['V2X']
This is fine for dynamic systems where we remove them in later optimisation, but may be problematic for static systems
Consider adding to config element allocate_zero_instrument_weights_to_these_instruments
['CORN', 'EDOLLAR', 'EUROSTX', 'MXP', 'US10', 'V2X']
```

OK, let's do what we're told:

```
system.cache.delete_all_items()
system.config.allocate_zero_instrument_weights_to_these_instruments= ['V2X']
system.portfolio.get_instrument_list(for_instrument_weights=True)
['CORN', 'EDOLLAR', 'EUROSTX', 'MXP', 'US10']
system.portfolio.get_instrument_weights().tail(1)

>              CORN   EDOLLAR   EUROSTX      MXP      US10  V2X
index                                                           
2021-10-06  0.260899  0.188551  0.181449  0.18055  0.188551  0.0

```

Incidentally, this will also apply zero weights if we are using 1/n fixed instrument weights:
```
system.portfolio.get_raw_fixed_instrument_weights()
>WARNING: No instrument weights  - using equal weights of 0.2000 over all 5 instruments in data
            CORN  EDOLLAR  EUROSTX  MXP  US10  V2X
1972-10-18   0.2      0.2      0.2  0.2   0.2  0.0
2021-10-06   0.2      0.2      0.2  0.2   0.2  0.0
```

If you pass explicit instrument weights you will have to set the relevant bad market to zero manually.

Now if you're using the dynamic optimisation, which works at a later stage, then you'll find the instruments are excluded automatically by applying them as 'reduce_only' constraints in the dynamic optimisation (this is for consistency with production, where the same logic is applied by the strategy order generator). Most likely we want to *include* them for instrument weight  optimisation; generate positions for them, but then in the final optimisation we won't have any.

```
from sysproduction.strategy_code.run_dynamic_optimised_system import *
data =csvFuturesSimData()
config = Config()
system = futures_system(data, config)
>Following instruments are 'duplicate_markets' and will be excluded from sim ...
>Following instruments are marked as 'ignore_instruments': not included: ['EURIBOR']
>Following instruments have restricted trading: optimisation will not trade them ...
>Following instruments are marked as 'bad_markets': optimisation will not trade them ['ALUMINIUM', .... 'V2X']

system.optimisedPositions.get_reduce_only_instruments()
>['US-STAPLES',... 'EU-CHEM']
```



### Untradeable

Markets which are untradeable are usually so for regulatory restrictions. For me, this means certain US futures:

```python
from systems.provided.futures_chapter15.basesystem import *
config = Config() # using a default config so we know we have all instruments there in principle
system = futures_system(config = config)
system.config.exclude_instrument_lists['trading_restrictions']
>['US-DISCRETE', 'US-ENERGY', 'US-FINANCE', 'US-HEALTH', 'US-INDUSTRY', 'US-MATERIAL', 'US-PROPERTY', 'US-REALESTATE', 'US-STAPLES', 'US-TECH', 'US-UTILS']
system.get_list_of_markets_with_trading_restrictions()
>['US-DISCRETE', 'US-ENERGY', 'US-FINANCE', 'US-HEALTH', 'US-INDUSTRY', 'US-MATERIAL', 'US-PROPERTY', 'US-REALESTATE', 'US-STAPLES', 'US-TECH', 'US-UTILS']
```


### Bad markets

AKA markets with high costs or low liquidity ('bad markets' is catchier, is it not?) Markets we can trade, but choose not to.

```python
system.config.exclude_instrument_lists['bad_markets']
['ALUMINIUM', 'BBCOMM', 'CHEESE', 'DJSTX-SMALL', 'EU-BANKS', 'EU-CHEM', 'EU-CONSTRUCTION', 'EU-DIV30', 'EU-FOOD', 'EU-HEALTH', 'EU-INSURE', 'EU-TRAVEL', 'EURIBOR', 'FTSEINDO', 'INR', 'KOSPI_mini', 'KRWUSD', 'LUMBER', 'MILK', 'MILKDRY', 'MSCIASIA', 'NOK', 'OATIES', 'RICE', 'SGD', 'SHATZ', 'US-DISCRETE', 'US-REALESTATE', 'USIRS5', 'V2X']
system.get_list_of_bad_markets()
['ALUMINIUM', 'BBCOMM', 'CHEESE', 'DJSTX-SMALL', 'EU-BANKS', 'EU-CHEM', 'EU-CONSTRUCTION', 'EU-DIV30', 'EU-FOOD', 'EU-HEALTH', 'EU-INSURE', 'EU-TRAVEL', 'EURIBOR', 'FTSEINDO', 'INR', 'KOSPI_mini', 'KRWUSD', 'LUMBER', 'MILK', 'MILKDRY', 'MSCIASIA', 'NOK', 'OATIES', 'RICE', 'SGD', 'SHATZ', 'US-DISCRETE', 'US-REALESTATE', 'USIRS5', 'V2X']
```


### Automatically excluded

It's also possible that there are some instruments that have zero positions. The most likely explanation for this is that you have set a speed limit on trading costs, and there are no trading rules that are cheap enough to trade the given instrument. These are automatically added to the list of markets given a zero weight for optimisation. 


## Customising the list of 'all instruments' and 'excluded for optimisation'

If you make two calls to system *before you do anything else with a system* you can decide exactly what is, or is not, included in the instrument lists. The following calls will reproduce the default system behaviour, but you can modify them if desired. IMPORTANT: they must be called in this order if you want to change the instrument_list() call.

```python
## days_required is used if we remove markets with short history
system.get_instrument_list(
                            remove_duplicates=True,
                            remove_ignored=True,
                            remove_trading_restrictions=False,
                            remove_bad_markets=False,
                            remove_short_history=False,
                            days_required = 750)

system.get_list_of_markets_not_trading_but_with_data(
                                                      remove_duplicates=True,
                                                      remove_ignored=True,
                                                      remove_trading_restrictions=True,
                                                      remove_bad_markets=True,
                                                      remove_short_history=False,
                                                      days_required=750
                                                      )

```


# Operating in production environment

Operating in the production environment is a bit more complex, due to the interaction of configuration files, the way that constraints operate, and the possibility of pulling in additional constraints from a database.

## A note about configuration

When you're running in simulation things are relatively simple; configuration items are defined in defaults_yaml, but can be overridden by your private_config.yaml, and then also by your own backtest.yaml file.

Importantly, once we're out of the 'backtesting' part of a production system, we can't see the backtest configuration (which after all is system specific, whereas generally in the production environment we're working with global parameters). So the priority order is `defaults.yaml`, overridden by `private_config.yaml`. The downstream code that produces strategy orders once the production backtest has generated optimal positions, and then trades those orders, will operate only on the configuration in `private_config.yaml` and `defaults.yaml`. 

## Reduce only and other constraints in static systems

Duplicate and ignored instruments work in exactly the same way in production; they'll be ignored in a backtest. Now normally in a static system we'd not be dynamically optimising our instrument weights every time we run the production backtest, but operating with saved instrument weights. If those weights were generated with untradeable and/or bad markets, then those markets will appear with zero instrument weights. We'll still generate forecasts and subsystem positions for them, but their optimal position will be zero.

When the strategy order generator runs it will apply *overrides* on any generated orders. Overrides allow us to reduce positions for a given strategy, for a given instrument (across all strategies), or for a given instrument & strategy combination. They are either:

- a multiplier, between 0 and 1, by which we multiply the desired position. A multiplier of 1 is equal to 'normal', and 0 means 'close everything'
- a flag, allowing us only to submit trades which reduce our positions
- a flag, allowing no trading to occur in the given instrument.

The list of overrides will include:

- Any overrides recorded in the override database (which can be of any type above)
- Any instruments configured as bad, duplicated, ignored, or untradeable will have overrides applied to them: normally 'reduce only', except for untradeable instruments which will be marked as don't trade (obviously!)

We always apply the most conservative override in any given situation. 

What this means in practice is that you can modify the list of instruments in the various categories and the system will automatically respond. So for example to remove a bad instrument:

- Add it to the configured list of bad instruments
- Set instrument weight to zero (either in one go, or gradually over time)
- The production system will see it as having a 'reduce only' flag, and allow a trade that reduces the size of the position

And to allow a bad instrument to begin trading again:

- Remove it from the configured list of bad instruments
- Re-optimise instrument weights so it has a positive instrument weight
- The production system will no longer see it has having a 'reduce only' flag, and will start to trade in that instrument
- If the weight is increased gradually then we'll gradually trade into the desired position

Similar logic will apply to ignored and duplicated instruments. Obviously if you mark an instrument has untradeable, and you have a position on, that position will continue to be held! Also limits on the number of trades that can be done will apply, so if you want to shut something down today you might need to create a manual order using the interactive order stack handler.

The code that applies this constraints is generic; it won't load in the strategy configuration .yaml, so if you wish to change the default configuration of bad, duplicated, ignored or untradeable instruments you need to change the `private_config.yaml`.

You can see the current list of instruments with overrides (either from configuration or set in the database) in the interactive_controls script:

(bash)
```
~/pysystemtrade/sysproduction/linux/scripts$ . interactive_controls 

0: Trade limits
1: Position limits
2: Trade control (override)
3: Broker client IDS
4: Process control and monitoring
5: Update configuration

Your choice? <RETURN for EXIT> 2
20: View overrides (configured, and database)
21: Update / add / remove override for strategy in database
22: Update / add / remove override for instrument in database
23: Update / add / remove override for strategy & instrument in database
24: Delete all overrides in database


Your choice? <RETURN for Back> 20
All overrides:

ALUMINIUM Override Reduce only because bad_instrument in config
BBCOMM Override Reduce only because bad_instrument in config
CHEESE Override Reduce only because bad_instrument in config
COPPER-mini Override Reduce only because duplicate_instrument in config
....
V2X Override Reduce only because bad_instrument in config
VIX_mini Override Reduce only because duplicate_instrument in config
WHEAT_mini Override Reduce only because duplicate_instrument in config
```

You can also set database trade overrides here.


## Reduce only and other constraints in dynamic systems

In a dynamic system we apply an optimisation to the optimal positions from the production backtest before generating orders. This optimisation needs to know about instruments with status 'reduce_only' and 'dont_trade'; again it will pull this information from a combination of configuration .yaml information (importantly, ignoring the backtest .yaml file) and what is loaded in the database. 

In principle the orders which are generated will also be subjected to the same constraints as for a static system, but since the optimisation takes care of them already this step won't have any effect on the orders that have been created.

This also means that there will be a more gradual transition out of newly added bad instruments (or ignored, or duplicate) instruments into ones that have been redeemed, since this is done in an optimisation with full knowledge of costs. Again if you wish to close a position today, you will need to issue a manual trade.

# Deciding which are 'bad' markets

I define a 'bad market' as one which:

- Has costs per trade> 0.01 SR units
- Trades<100 contracts per day
- Trades<$1.5 million of risk units per day

We can get a list of suggested 'bad' markets through the interactive controls script.

## Check slippage costs are accurate

To calculate costs accurately we need to make sure our slippage is correct. 

```
~/pysystemtrade/sysproduction/linux/scripts$ . interactive_controls 
0: Trade limits
1: Position limits
2: Trade control (override)
3: Broker client IDS
4: Process control and monitoring
5: Update configuration


Your choice? <RETURN for EXIT> 5
50: Auto update spread cost configuration based on sampling and trades
51: Suggest 'bad' markets (illiquid or costly)
52: Suggest which duplicate market to use


Your choice? <RETURN for Back> 50

% difference to filter on? (eg 30 means we ignore differences<30% <RETURN for default 30.0> 

```

What this does is run the standard costs report, which calculates a recommended slippage cost. This figure is a weighted average of the costs of trading, costs measured through daily sampling of the relevant instrument, and the current configured value. It then checks to see if the recommended value is more than 30% different from the configured value. We then get a series of prompts like this:

```
% difference to filter on? (eg 30 means we ignore differences<30% <RETURN for default 30.0> 
bid_ask_trades           NaN
total_trades             NaN
bid_ask_sampled    20.666667
weight_trades       0.000000
weight_samples      0.382716
weight_config       0.617284
estimate           14.304580
Configured         10.360086
% Difference        0.380739
Name: US-DISCRETE, dtype: float64
New configured slippage value (current 10.360086, default is estimate 14.304580) <RETURN for default 14.304579734718004> 
```

This is a market we haven't traded, but our sampled values (14.3 price points) is 38% higher than our configured (10.36). This is because the sampled bid/ask spread has averaged 20.67 points; we given a 38% weight to these samples (maybe we haven't traded that much) and 62% to the configured value.

```
New configured slippage value (current 0.172000, default is estimate 0.117354) <RETURN for default 0.11735449352746953> 
ALL VALUES MULTIPLIED BY 1000000.000000 INCLUDING INPUTS!!!!
bid_ask_trades          1.500000
total_trades           -0.100000
bid_ask_sampled         0.179167
weight_trades       97192.224622
weight_samples     578833.693305
weight_config      323974.082073
estimate                0.476278
Configured              0.700000
% Difference      -319603.003188
Name: KRWUSD, dtype: float64
New configured slippage value (current 0.700000, default is estimate 0.476278) <RETURN for default 0.47627789776817986> 
```

This is the only 'gotcha', for some instruments if the spread is very tiny we multiply everything by some power of 10 to get easier numbers (which, as I'm lazy, includes the weight_* figures).

## Get list of bad markets

We can now get the list of bad markets:

```
~/pysystemtrade/sysproduction/linux/scripts$ . interactive_controls 
1: Position limits
2: Trade control (override)
3: Broker client IDS
4: Process control and monitoring
5: Update configuration


Your choice? <RETURN for EXIT> 5
50: Auto update spread cost configuration based on sampling and trades
51: Suggest 'bad' markets (illiquid or costly)
52: Suggest which duplicate market to use


Your choice? <RETURN for Back> 51
Maximum SR cost? <RETURN for default 0.01> 
Minimum contracts traded per day? <RETURN for default 100> 
Min risk $m traded per day? <RETURN for default 1.5> 
```

This will take a while to get all the relevant data, but eventually you will get presented with something like this:

```
Add the following to yaml .config under bad_markets heading:

bad_markets:
  - ALUMINIUM
  - BBCOMM
  - CHEESE
  - DJSTX-SMALL
....
  - USIRS5
  - V2X
New bad markets ['FTSEINDO', 'V2X']
Removed bad markets ['US10']
```

At the bottom it tells you what changes it recommends, and you can implement these changes by copying and pasting the .yaml fragment above - this doesn't happen automatically!
Although this doesn't give you the reason why markets are bad, the costs and liquidity reports use the same underlying information.


# Deciding which duplicate instruments to use

A very similar approach is used to decide which of the duplicated instruments to use. We apply the same filters as used for bad markets, to make sure we don't pick anything bad:

```
~/pysystemtrade/sysproduction/linux/scripts$ . interactive_controls 
1: Position limits
2: Trade control (override)
3: Broker client IDS
4: Process control and monitoring
5: Update configuration


Your choice? <RETURN for EXIT> 5
50: Auto update spread cost configuration based on sampling and trades
51: Suggest 'bad' markets (illiquid or costly)
52: Suggest which duplicate market to use


Your choice? <RETURN for Back> 52
Maximum SR cost? <RETURN for default 0.01> 
Minimum contracts traded per day? <RETURN for default 100> 
Min risk $m traded per day? <RETURN for default 1.5> 


```
We then get a printout of the recommended duplicate markets.

In this trivial example we only have one market that we have data for, but that doesn't meet any of the filters!

```
Current list of included markets ['KRWUSD'], excluded markets ['KRWUSD_mini']
              SR_cost  volume_contracts  volume_risk  contract_size
KRWUSD       0.025299              12.0         0.06         5017.0
KRWUSD_mini       NaN               NaN          NaN            NaN
Best market <No good markets>, current included market(s) ['KRWUSD']
```

Again here we have data for only one market, but it passes our filters so is recommended.

```
Current list of included markets ['HEATOIL'], excluded markets ['HEATOIL_mini']
               SR_cost  volume_contracts  volume_risk  contract_size
HEATOIL       0.002312           18436.0       315.85        17133.0
HEATOIL_mini       NaN               NaN          NaN            NaN
Best market HEATOIL, current included market(s) ['HEATOIL']
```

Two markets now, but only one passes the filter:
```
Current list of included markets ['KOSPI'], excluded markets ['KOSPI_mini']
             SR_cost  volume_contracts  volume_risk  contract_size
KOSPI_mini  0.015313           69366.0       128.40         1851.0
KOSPI       0.006080          209258.0      1944.95         9295.0
Best market KOSPI, current included market(s) ['KOSPI']
```

Here are some examples with multiple instruments passing our filter; we pick the one with the smallest contract size:
```
Current list of included markets ['CRUDE_W_mini'], excluded markets ['CRUDE_W']
               SR_cost  volume_contracts  volume_risk  contract_size
CRUDE_W_mini  0.003753            8495.0        61.24         7208.0
CRUDE_W       0.001992          170167.0      1987.92        11682.0
Best market CRUDE_W_mini, current included market(s) ['CRUDE_W_mini']


Current list of included markets ['SP500_micro'], excluded markets ['SP500']
              SR_cost  volume_contracts  volume_risk  contract_size
SP500_micro  0.000858          545179.0       941.33         1727.0
SP500        0.000814          865522.0     14932.25        17252.0
Best market SP500_micro, current included market(s) ['SP500_micro']

Current list of included markets ['GAS_US_mini'], excluded markets ['GAS_US']

              SR_cost  volume_contracts  volume_risk  contract_size
GAS_US_mini  0.003782            4614.0        39.06         8467.0
GAS_US       0.000849           48674.0      1619.18        33266.0
Best market GAS_US_mini, current included market(s) ['GAS_US_mini']

Current list of included markets ['NASDAQ_micro'], excluded markets ['NASDAQ']
               SR_cost  volume_contracts  volume_risk  contract_size
NASDAQ        0.000452          361956.0     11287.52        31185.0
NASDAQ_micro  0.000436          577104.0      1740.20         3015.0
Best market NASDAQ_micro, current included market(s) ['NASDAQ_micro']


Current list of included markets ['GOLD_micro'], excluded markets ['GOLD']
             SR_cost  volume_contracts  volume_risk  contract_size
GOLD_micro  0.001062           22632.0        39.07         1726.0
GOLD        0.000950           84525.0      1457.25        17240.0
Best market GOLD_micro, current included market(s) ['GOLD_micro']

```


