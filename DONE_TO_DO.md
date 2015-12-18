# Release notes

## Version: 0.0.1


Basic backtesting enviroment with example futures data.


# Bugs to fix

None that I know of


# Features to add - later releases

logging / error catching
system cleaning

* Simulation:

  * add account object to portfolio stage for ease of use
  * estimated trades; with buffering of trades
  * vol targeting with capital adjustment
  * Rolling estimate of forecast scalars
  * Rolling optimisation of forecast and instrument weights
  * Rolling estimate of fcast_div_mult and instr_div_mult
  * quandl data
  * Create live config from a system object (Put final value of estimates into a yaml file) 
  * database data
  * stitch futures contracts 
  * add new data from unstitched contracts (with explanatory post, include explanation for Nth contract stitching)
  * check systems have correct attributes; check turnover, minimum size etc

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
    
