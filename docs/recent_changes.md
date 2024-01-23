# Recent changes

There are several major changes to the application that are not fully reflected in the docs yet. See below for links to discussions or issues where covered:

### Parquet / Arctic
* Nov 2023
* Default behaviour is now to use Parquet for persistence of timeseries data. Staying with Arctic is still possible with manual changes
* Read more [here](https://github.com/robcarver17/pysystemtrade/discussions/1290), and [here](https://github.com/robcarver17/pysystemtrade/discussions/1291)

### More recent dependency versions
* Nov 2023
* More recent versions of Python (3.10), Pandas (2) are supported
* Read more [here](https://github.com/robcarver17/pysystemtrade/discussions/1293)

### Roll states, auto rolling, roll rules
* Jul 2023
* Contract rolling behaviour updated
* Read more [here](https://github.com/robcarver17/pysystemtrade/issues/1198), [here](https://github.com/robcarver17/pysystemtrade/issues/931), and [here](https://github.com/robcarver17/pysystemtrade/issues/1193)

### No market data
* Jul 2023
* Easier trading without market data subscriptions
* Read more [here](https://github.com/robcarver17/pysystemtrade/issues/1165), [here](https://github.com/robcarver17/pysystemtrade/issues/1016), and the `algo_overrides` section in [defaults.yml](https://github.com/robcarver17/pysystemtrade/blob/master/sysdata/config/defaults.yaml) 

### Instrument and forecast weight config as hierarchy
* Jun 2023
* Easier way to specify weights
* Read more [here](https://github.com/robcarver17/pysystemtrade/discussions/1160) and [here](https://github.com/robcarver17/pysystemtrade/issues/1162)

### Instrument and roll config moved to CSV storage
* Mar 2023 
* Persistence of instrument and roll config moved from MongoDB to CSV
* Read more [here](https://github.com/robcarver17/pysystemtrade/discussions/1054)

### Development processes
* Mar 2023 
* Now two branches: `master` is stable, develop work happens on `develop`. Branches for PRs should be made from `develop`
* Read more [here](https://github.com/robcarver17/pysystemtrade/discussions/1069)

### Changes to timing of production processes 
* Jan 2023
* Timing of some daily production processes adjusted
* Read more [here](https://github.com/robcarver17/pysystemtrade/discussions/913), [here](https://github.com/robcarver17/pysystemtrade/discussions/956), and [here](https://github.com/robcarver17/pysystemtrade/discussions/961)

### Separate daily and hourly prices
* Aug 2022
* Daily and hourly price data are now stored separately
* Read more [here](https://github.com/robcarver17/pysystemtrade/discussions/756)
 


