# Release notes

## Version 0.14.1

* Added progress bar (issue 51)

## Version 0.14.0

* Stages now have _names and _description defined in __init__
* log values now passed in when __init__ of stage; hence baseystem.__init__ is much cleaner
* Caching:
   * Cache is now accessed via a seperate object in system; so system.cache.* rather than system.* for cache methods
   * Caching now done through decorators: from systems.system_cache import input, dont_cache, diagnostic, output
   * Use protected=True and/or not_cached=True within decorators
* Got rid of 'switching' stages for estimating forecast scalars, forecast weights, instrument weights.
   * Explicit import of a Fixed or Estimated version of a class won't work; use the generic version.
   * Added seperate fields to .yaml file to switch between IDM and FDM estimation or fixed values
* Split ultra-massive accounts.py into multiple files and classes
* Split unwieldy ForecastCombine into several classes
* Added a bunch more unit tests as I went through the above refactoring exercise
* some refactoring of optimisation code - more to come
* fixed up examples and documentation accordingly

## Version 0.13.0

* Now requires pandas version > 0.19.0

## Version 0.12.0

* Capital correction now works. New methods: system.accounts.capital_multiplier, system.accounts.portfolio_with_multiplier, system.portfolio.get_actual_positon, system.portfolio.get_actual_buffers_with_position, system.accounts.get_buffered_position_with_multiplier. See this [blog post](http://qoppac.blogspot.co.uk/2016/06/capital-correction-pysystemtrade.html)  and [the guide](https://github.com/robcarver17/pysystemtrade/blob/master/docs/userguide.md#capcorrection)


## Version 0.11.2

* Smooth fixed weights as well as variable: removed ewma_span and moved to new config item forecast_weight_ewma_span and same for instruments. Removed override of get_instrument_weights, get_forecast_weights method from estimated classes.


## Version 0.11.1

* Added extra methods to support capital scaling, but not implemented yet.
* fixed couple of bugs in getting subsystem p&l to calculate instrument weights
* removed aligned fx method, doesn't speed up and adds complexity
* solved issue #16

## Version 0.11.0

* Included option to show account curves as cumulative (compounding): somecurve.cumulative()
* removed percentage options, now a method for account curves: somecurve.percent()
* Incorporated capital into account curves: anycurve.capital
* General clean up of the way capital dealt with in accounting


## Version 0.10.3

* More speed up, couple of tweaks...


## Version 0.10.2

* Split up optimiser class so can selectively check if need data for equal weights; speed up

## Version 0.10.01
* Fixed bugs introduced in last version

## Version 0.10.0 
* Refactored optimisation with costs code, changed configuration slightly (read [this revised blog post for more](http://qoppac.blogspot.co.uk/2016/05/optimising-weights-with-costs.html) )
* Introduced method to cope with pooling on both costs and gross returns, so doesn't recalculate several times
* Moved pre-screening for expensive assets to an earlier stage
* New optimisation method "equal_weights" for equal weights; means that eg expensive forecasts can be removed and then take an equal weight on the rest


## Version 0.10.0 

* Optimisation: 
   * Replaced slow divide, multiply methods in syscore.pdutils with straightforward division; also means:
      * Replaced Tx1 pd.DataFrames with pd.Series except where stricly necessary
      * Removed a lot of defensive reindexing code where things should already be on same timestamp
      * Replaced remaining reindexing code with pandas native .align methods
   * accounting p&l doesn't have to work out trades, then go back to positions, if no trades provided.

## Version 0.9.0 

* Changed / added the following methods to `system.accounts`: `pandl_for_instrument_forecast_weighted`, `pandl_for_trading_rule_weighted`, `pandl_for_all_trading_rules`, `pandl_for_trading_rule`, `pandl_for_trading_rule_unweighted`, `pandl_for_all_trading_rules_unweighted` See [/docs/userguide.md#weighted_acg] for more detail.
* Added `get_capital_in_rule`, `get_instrument_forecast_scaling_factor` to help calculate these.
* fixed error in user guide


## Version 0.8.1 

* Fixed small bug with shrinkage
* Added references to blog post on costs

## Version 0.8.0 

* introduced methods for optimisation with costs. See [this blog post for more](http://qoppac.blogspot.co.uk/2016/05/optimising-weights-with-costs.html)
* made a lot of tweaks to optimisation code; mainly shrinkage now shrinks towards target Sharpe ratio, equalising SR does the same; consistent annualisation 
* introduced new parameter for optimisation `ann_target_SR`
* `system.combForecast.calculation_of_raw_forecast_weights` (estimated version) no longer stores nested weights.

## Version 0.7.0 

* ability to pickle and unpickle cache (`system.pickle_cache`, `system.unpickle_cache`)
* included breakout rule (example is being written)
* seperate out weighting calculation so instrument forecast pandl can be cached
* csv data is now daily and updated to present day
* Fixed bug with loading data from private module
* Changed raw cost data so returns dict not tuple
* Added 'flags' to cache identifier to replace horrors like 'portfolio__percentageTdelayfillTroundpositionsT'
* p&l for trading rules now nested in caches rather than using special identifier

## Version 0.6.6

* Added method `accounts.pandl_for_instrument_rules`


## Version 0.6.5

* Renamed method `accounts.pandl_for_instrument_rules` to `pandl_for_instrument_rules.unweighted`
* Fixed bug with portfolio and instrument account curves overstating costs by adding cost weightings


## Version 0.6.4

* Fixed weighting of account curves and introduced explicit flag for weighting
* Added `pandl_for_trading_rule_unweighted` method to accounts object.


## Version 0.6.3

* Added `pandl_for_trading_rule` method to accounts object.


## Version 0.6.2

* Added t_test method to `accountCurve` (and all that inherit from her)


## Version 0.6.1

* Added methods to accountCurveGroup.get_stats(): .mean(), .std(), .tstat(), .pvalue()
* Added method to accountCurveGroup stack; stack object can also produce bootstrap
* Added account_test(ac1, ac2) to produce a t-test statistic for any two account curve like objects.

## Version 0.6.0

* dynamically change class depending on config flag to estimate parameters or not 
* add stage description field, and stage.methods() method 
* add stage name to cache reference, always pass stage to caching function. Added cache methods to system which understand stages

## Version 0.5.2

* Correlation tests failing - fixed up
* Costs SR didn't get turnover - duh! Now fixed. Added a bunch of input methods to accounts object to calculate them
* tweak to account curve grouping to data frame to remove nans
* cost calculation no longer fails if no trades for an instrument
* changed buffering rounding so consistent with my own system

## Version: 0.5.1

* Introduced maximum cap on IDM and FDM of 2.5, as per the book.
* Correlation cleaning wasn't working as documented - now does.
* cleaning up:
  * renamed misleading 'get_daily_price' method to 'get_raw_price', to fix some tests that hadn't realised the difference
  * fixed a bunch of tests
  * changed the way cross rates are calculated to ensure data isn't lost 

## Version: 0.5.0

* Include buffering / position intertia


## Version: 0.4.0

* Included cost data and calculations.

## Version: 0.3.0

* Account curve improvements: generate lists of simulated trades, extend the `accountCurve` object to handle multiple columns, statistics over different periods. 

## Version: 0.2.1

* Fixed bug with bootstrapping with missing values
* Changed clean correlations so it replaces with an average
* Fixed some documentation SNAFU's
* Added reference to latest blog post


## Version: 0.2.0

* Calculating forecast weights in ForecastCombineEstimated
* Created PortfoliosEstimated
   * Calculating instrument weights 
   * Calculating instrument diversification multiplier 
* Added a logging function 
* Modified system.get_instruments so will check config.instruments (useful if estimating instrument weights)
* Included daily_prices method in data; raw data method just points to it; replaced most uses of (intraday) data.get_instrument_price with daily prices
* Added some new methods to account stage
* Cleaned up the way pooling works in correlation estimation
* Finished clean_correlation function so now deals with incomplete matricies
* Changed the way defaults feed into config objects


## Version: 0.1.0

* Added estimation of forecast diversification multiplier to ForecastCombineEstimated
* Changed default forecast correlation estimation period; had to fix up some test output
* Changed way that forecast correlations are cached
* Started using more logical version numbering scheme :-)

## Version: 0.0.3

* Created ForecastCombineEstimated, with get_forecast_correlation_matrices
* Added get_trading_rule_list and get_all_forecasts to forecast_combine
* Added rule_variations config option
* Added Bund data to test suite; had to fix some tests
* Pooling for forecast scalar doesn't need its own function anymore
* Changed the way config defaults are handled
* Fixed bugs: use of bool to convert str
* Fixed bugs: some test configs had wrong trading rule parameter setup; had to fix slew of tests as a result

## Version: 0.0.2

* Added rolling estimate of forecast scalars; try System([rawdata, rules, *ForecastScaleCapEstimated()*], data, config)
* Moved .get_instrument_list from portfolio object to parent system

## Version: 0.0.1

* Basic backtesting enviroment with example futures data.



# Bugs to fix

* none are known

# Features to add - later releases

* Simulation:
   
  * add other trading rules (some in private...?) - cross sectional carry
  * quandl data
  * stitch futures contracts 
  * add new data from unstitched contracts (with explanatory post, include explanation for Nth contract stitching)
  * Create live config from a system object (Put final value of estimates into a yaml file) 
  * database data
  * Exogenous risk model
  * check systems have correct attributes; check turnover, minimum size, right forecast scalars (distribution across instruments) etc

* Live trading:

  * ib broker interface
  * accounting
  * order / position reconciliation
  * issue market order 
  * execution algos
  * control functions
  * get pricing data system 
  * Reporting: 
    * risk report
      * risk by asset class
    * interrogate signal object generated at run time
    * p&l report
    * trades report
    
