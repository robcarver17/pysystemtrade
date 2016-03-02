# Release notes


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

None that I know of


# Features to add - later releases

logging / error catching
system cleaning

* Simulation:

  * estimated trades; with buffering of trades
  * autodetect if need to estimate parameters or not
  * vol targeting with capital adjustment
  * quandl data
  * stitch futures contracts 
  * add new data from unstitched contracts (with explanatory post, include explanation for Nth contract stitching)
  * Create live config from a system object (Put final value of estimates into a yaml file) 
  * Speed up optimisation and correlation estimates
  * database data
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
    
