# Release notes

## Version 0.6.6

* Added method accounts.pandl_for_instrument_rules


## Version 0.6.5

* Renamed method accounts.pandl_for_instrument_rules to pandl_for_instrument_rules.unweighted
* Fixed bug with portfolio and instrument account curves overstating costs by adding cost weightings


## Version 0.6.4

* Fixed weighting of account curves and introduced explicit flag for weighting
* Added pandl_for_trading_rule_unweighted method to accounts object.


## Version 0.6.3

* Added pandl_for_trading_rule method to accounts object.


## Version 0.6.2

* Added t_test method to accountCurve (and all that inherit from her)


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
* Pooling for forecast scalar doesn't need it's own function anymore
* Changed the way config defaults are handled
* Fixed bugs: use of bool to convert str
* Fixed bugs: some test configs had wrong trading rule parameter setup; had to fix slew of tests as a result

## Version: 0.0.2

* Added rolling estimate of forecast scalars; try System([rawdata, rules, *ForecastScaleCapEstimated()*], data, config)
* Moved .get_instrument_list from portfolio object to parent system

## Version: 0.0.1

* Basic backtesting enviroment with example futures data.



# Bugs to fix

* none

# Features to add - later releases

* Simulation:

  * remove weighting from instrument forecast pandl so can be cached
  * pickle and unpickle cache
  * add cross sectional carry rule and breakout rule
  * vol targeting with capital adjustment
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
    
