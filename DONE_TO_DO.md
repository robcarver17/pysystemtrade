# Release notes

## Version: 0.0.1


Basic backtesting enviroment with example futures data.


# Bugs to fix

None that I know of


# Features to add - this release

portfolio p&l

fix up default.py
defaults for IDM, FDM to be used
check on the fly add trading rules works
remove fixed values of 10.0
default to equal weights
remove bad imports
run all tests


docs- intro, tutorial, api reference, developer documentation

# Features to add - later releases

logging / error catching
system cleaning

* Simulation:

  * which instruments in a portfolio?
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
    * interrogate signal object generated at run time
    * p&l report
    * trades report
