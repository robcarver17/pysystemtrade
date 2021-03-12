# Release notes

Moved 'quant' type functions to sysquant: robust_vol_calc - you may get error messages - update your config 
Renamed certain functions in systems.rawdata (used by 'fancier' trading rules) - update your config

## Version 0.85
**WARNING! FROM VERSION 0.85.0 IS A MAJOR UPGRADE. SEE [pandas_upgrade](pandas_upgrade.md) BEFORE DOING ANYTHING!

Upgraded pandas and arctic versions
Added 'Pause' process status
Refactored and tidied control code
Control process now sleep when not needed to save energy
Removed option to specify machine to run process on

## Version 0.80

Finished refactoring of production code (or at least, for now!)
sysproduction/diagnostics now renamed reporting
sysproduction/data code now uses generic handler and property methods to access data
broker API now has proper base classes
Tinkered with requirements to get running on new machine

## Version 0.75

Moved defaults.yaml to /sysdata/config directory
Removed 'example' strategy from config files - strategies need to be explicit in private yaml config
Cleaned up configuration code. Production config now accessed through data blob where possible.
Messed up order database by changing formats; let me know if you have any issues reading your old orders

## Version 0.70

Massive refactoring mainly of order code but also IB client structure. Should be backwardly compatible with old saved orders except 'split' orders which are ignored. Read 'journey of an order' in production code for granular detail. 

added remote monitoring

## Version 0.60.0

Split out control configuration from other YAML files (**YOU WILL NEED TO CHANGE PRIVATE CONFIG** look at the production docs!)
Refactoring of run and control processes mostly into new syscontrol module
Added simple monitoring tool
Added email 'to' option (**YOU WILL NEED TO CHANGE PRIVATE CONFIG TO INCLUDE email_to parameter**)

## Version 0.52.0

Mostly refactoring and documenting the creation and storage of data


## Version 0.51.0

Essentially 'finished' production.md (in as much as anything can be finished...)
Changed data Blobs so now take lists of objects rather than str, easier to see dependencies

## Version 0.50.0

(Done loads of work but forgotten to update the version number or this file. So let's reward ourselves with a 0.20 version bump. The following list is almost certainly incomplete...)
Done loads of documentation for production
Added position limits
Removed broker base classes as redundant
Minimum tick size used in setting limit orders
Stopped double counting of volumes when daily/intraday data mixed
Added startup script
Fixed issues with time zone mismatches
Added trades report, strategy report, signals report, risk report, p&l report
Position locks
Added interactive diagnostics, interactive order stack, interactive controls
Execution algo!
Added capability to trade

## Version 0.30.0

Introduced capital model for production
Fixed bug in implementation of correlation to covariance
Added optional code for risk overlay [see blog](https://qoppac.blogspot.com/2020/05/when-endogenous-risk-management-isnt.html)
Moved fx cross logic out of sim data into fxPricesData
Strategies now run backtests from configuration file

## Version 0.29.0

Added price 'spike' checker, and manual price checking service
Removed PIL library (issue 161)
Fixed ib_insync PIP issue (pull 162)
MongoDb logs will now try to email user if a critical error is raised

## Version 0.28.0

IB now uses ib_insync, not native IB library

## Version 0.27.0

Cleaned up way defaults and private config files work
Removed separate mongodb config file
Added production code to run a system backtest and save optimal position state
Cleaned up the way path and filename resolution works
Added production code to backup mongodb to .csv files

## Version 0.26.0

Added production code to get daily futures prices from IB, update sampled contracts, update multiple and adjusted prices.

## Version 0.25.0

Can now get individual futures prices from IB, both historical daily and intraday (with get_prices_at_frequency_for_* methods)
Added code to deal with VIX weekly expiries - they can now be ignored
Caching IB contract objects in IB client as rather expensive
IB client will now avoid pacing violations
Removed futuresContract.simple() method; you can now just do futuresContract("AUDUSD", "yyyymmdd")
Cleaned up IB client code, error handling is now consistent
Added  broker_get_contract_expiry_date method to brokerClient and ibClient
IB connection will now check to see if a clientid is being used even if one is passed. Has '.terminate' method which will try and clear clientid.
.csv config files are cached in IB price API objects

## Version 0.24.0

Can now pass keyword arguments to data methods when creating a trading rule (Enhancement # 141)
Fixed bugs relating to building multiple and adjusted prices
Slight refactoring of futuresContractPrices objects. These only have FINAL, not CLOSE or SETTLE prices now.
Added more data

## Version 0.23.0

'get_filename_for_package' can now take absolute as well as relative paths, and can cope with separate file names
Updated legacy .csv files
Fixed a few bugs
Can now get unexpired contracts for a given instrument using 'contractDateWithRollParameters.get_unexpired_contracts_from_now_to_contract_date()'

## Version 0.22.0

*Now requires python 3.6.0, pandas 0.25.2*
Fixed a few bugs in production functions for FX prices
Logging now requires an explicit labelling argument, eg `log=logtoscreen("String required here")
Changed mongodb logging so now indexes on unique ID
Generally cleaned up logging code
Moved update fx price logic inside generic fx price object

## Version 0.21.0

Removed dependency on Quandl currency for setting up spot FX, now uses investing.com
Fixed issues relating to robust vol calc, date offset in roll calendars

## Version 0.20.0

Started documenting 'how to run a production system'
Created logging to mongo database
Refactoring of mongo and arctic connections
Started creating crontab and scripts for various production functions (read and write FX prices)
Added code to ensure unique client ID for IB

## Version 0.19.0

Added connection code for Interactive Brokers. See [connecting pysystemtrade to interactive brokers](/docs/IB.md) for more details.
Implemented data socket for spot FX, getting data from IB
Added handcrafting optimisation code.

## Version 0.18.2
Added methods to read weight data from csv files
Put generalised non linear mapping into forecast combination
Added flag option to use process pools for parallel processing - but not actually used yet
Cleaned up setup.py file now finds data files recursively
Fixed bug in getting asset class data from csv config files

## Version 0.18.1
Finished populating configuration files for Quandl and roll configuration.
Debugged futures.md documentation file.

## Version 0.18
See [futures documentation](/docs/futures.md) for more details.
New data sources: Quandl. Data storage in mongodb and arctic is now supported.
Back-adjustment is possible and can be done 'on the fly' or from scratch with new data. 
Further refactoring of sim data objects to support the above.

## Version 0.17
Massive refactoring of sim data objects, to support alternative data sources and backadjusting

## Version 0.16.6
Created classses for individual futures contracts, and included example of how to use Quandl to get them

## Version 0.16.5
Updated .csv data and moved to separate section - now stored under Github LFS

## Version 0.16.4
Added quandl data (but only for individual futures contracts right now so useless)

## Version 0.16.3
Removed uses of old carry function which was deprecated

## Version 0.16.2
Fixed incorrect calculation of returns over weekends
Forecast scalars now only pool across the set of instruments using a given trading rule
Changed error handling for empty Rules() objects
Added TOC to userguide.md file

## Version 0.16.1
Updated to pandas 0.22.0
Fixed issue #64, #68, #70 and other issues relating to pandas API update breaking correlation matrices

## Version 0.16.0
Moved most examples except core to separate git [here](https://github.com/robcarver17/pysystemtrade_examples)

## Version 0.15.0

* Now supports pandas 0.20.3 (earlier pandas will break)

## Version 0.14.1

* Added progress bar (issue 51)

## Version 0.14.0

* Stages now have _names and _description defined in __init__
* log values now passed in when __init__ of stage; hence baseystem.__init__ is much cleaner
* Caching:
   * Cache is now accessed via a separate object in system; so system.cache.* rather than system.* for cache methods
   * Caching now done through decorators: from systems.system_cache import input, dont_cache, diagnostic, output
   * Use protected=True and/or not_cached=True within decorators
* Got rid of 'switching' stages for estimating forecast scalars, forecast weights, instrument weights.
   * Explicit import of a Fixed or Estimated version of a class won't work; use the generic version.
   * Added separate fields to .yaml file to switch between IDM and FDM estimation or fixed values
* Split ultra-massive accounts.py into multiple files and classes
* Split unwieldy ForecastCombine into several classes
* Added a bunch more unit tests as I went through the above refactoring exercise
* some refactoring of optimisation code - more to come
* fixed up examples and documentation accordingly

## Version 0.13.0

* Now requires pandas version > 0.19.0

## Version 0.12.0

* Capital correction now works. New methods: system.accounts.capital_multiplier, system.accounts.portfolio_with_multiplier, system.portfolio.get_actual_positon, system.portfolio.get_actual_buffers_with_position, system.accounts.get_buffered_position_with_multiplier. See this [blog post](https://qoppac.blogspot.com/2016/06/capital-correction-pysystemtrade.html) and [the guide](https://github.com/robcarver17/pysystemtrade/blob/master/docs/userguide.md#capcorrection)


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
* Refactored optimisation with costs code, changed configuration slightly (read [this revised blog post for more](https://qoppac.blogspot.com/2016/05/optimising-weights-with-costs.html) )
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

* Changed / added the following methods to `system.accounts`: `pandl_for_instrument_forecast_weighted`, `pandl_for_trading_rule_weighted`, `pandl_for_all_trading_rules`, `pandl_for_trading_rule`, `pandl_for_trading_rule_unweighted`, `pandl_for_all_trading_rules_unweighted` See [Weighted and unweighted account curve groups](/docs/userguide.md#weighted_acg) for more detail.
* Added `get_capital_in_rule`, `get_instrument_forecast_scaling_factor` to help calculate these.
* fixed error in user guide


## Version 0.8.1 

* Fixed small bug with shrinkage
* Added references to blog post on costs

## Version 0.8.0 

* introduced methods for optimisation with costs. See [this blog post for more](https://qoppac.blogspot.com/2016/05/optimising-weights-with-costs.html)
* made a lot of tweaks to optimisation code; mainly shrinkage now shrinks towards target Sharpe ratio, equalising SR does the same; consistent annualisation 
* introduced new parameter for optimisation `ann_target_SR`
* `system.combForecast.calculation_of_raw_forecast_weights` (estimated version) no longer stores nested weights.

## Version 0.7.0 

* ability to pickle and unpickle cache (`system.pickle_cache`, `system.unpickle_cache`)
* included breakout rule (example is being written)
* separate out weighting calculation so instrument forecast pandl can be cached
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

* Added rolling estimate of forecast scalars; try `System([rawdata, rules, ForecastScaleCapEstimated()], data, config)`
* Moved .get_instrument_list from portfolio object to parent system

## Version: 0.0.1

* Basic backtesting environment with example futures data.



# Bugs to fix

* If you use a non USD currency then you get a flat spot earlier in the account curve. It should be NAN

# Features to add -next release


# Features to add - later releases

* Simulation:

  * Parallel processing of - getting data, trading rules, p&l calculation, optimisation
  * Create live config from a system object (Put final value of estimates into a yaml file) 
  * Check systems have correct attributes; check turnover, minimum size, right forecast scalars (distribution across instruments) etc
  * Check does 'cheap rules' not work when fixed instrument rules, know about weight==0
  * Refactor yaml code to drop pyyaml (no long supported)
  * Add risk overlay


* Live trading:

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
    
