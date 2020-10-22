This document is specifically about using pysystemtrade for *live production trading*.

*This is NOT a complete document, and is currently a work in progress - and in many cases a series of thoughts about design intent rather than a fully featured specification. It is not possible to run a full production system with pysystemtrade at present*

Ultimately this will include:

1. Getting prices
2. Generating desired trades
3. Executing trades
4. Getting accounting information

Related documents:

- [Storing futures and spot FX data](/docs/futures.md)
- [Main user guide](/docs/userguide.md)
- [Connecting pysystemtrade to interactive brokers](/docs/IB.md)

*IMPORTANT: Make sure you know what you are doing. All financial trading offers the possibility of loss. Leveraged trading, such as futures trading, may result in you losing all your money, and still owing more. Backtested results are no guarantee of future performance. No warranty is offered or implied for this software. I can take no responsibility for any losses caused by live trading using pysystemtrade. Use at your own risk.*

Table of Contents
=================

   * [Quick start guide](#quick-start-guide)
   * [Overview of a production system](#overview-of-a-production-system)
   * [Implementation options](#implementation-options)
      * [Automation options](#automation-options)
      * [Machines, containers and clouds](#machines-containers-and-clouds)
      * [Backup machine](#backup-machine)
      * [Multiple systems](#multiple-systems)
   * [Code and configuration management](#code-and-configuration-management)
      * [Managing your separate directories of code and configuration](#managing-your-separate-directories-of-code-and-configuration)
      * [Managing your private directory](#managing-your-private-directory)
   * [Finalise your backtest configuration](#finalise-your-backtest-configuration)
   * [Linking to a broker](#linking-to-a-broker)
   * [Other data sources](#other-data-sources)
   * [Data storage](#data-storage)
      * [Data backup](#data-backup)
         * [Mongo data](#mongo-data)
         * [Mongo / csv data](#mongo--csv-data)
   * [Echoes, Logging, diagnostics and reporting](#echoes-logging-diagnostics-and-reporting)
      * [Echos: stdout output](#echos-stdout-output)
         * [Cleaning old echo files](#cleaning-old-echo-files)
      * [Logging](#logging)
         * [Adding logging to your code](#adding-logging-to-your-code)
         * [Getting log data back](#getting-log-data-back)
         * [Cleaning old logs](#cleaning-old-logs)
      * [Reporting](#reporting)
         * [Roll report (Daily)](#roll-report-daily)
   * [Scripts](#scripts)
      * [Production system components](#production-system-components)
         * [Get spot FX data from interactive brokers, write to MongoDB (Daily)](#get-spot-fx-data-from-interactive-brokers-write-to-mongodb-daily)
         * [Update sampled contracts (Daily)](#update-sampled-contracts-daily)
         * [Update futures contract historical price data (Daily)](#update-futures-contract-historical-price-data-daily)
         * [Update multiple and adjusted prices (Daily)](#update-multiple-and-adjusted-prices-daily)
         * [Roll adjusted prices (whenever required)](#roll-adjusted-prices-whenever-required)
         * [Run an updated backtest system (overnight) for a single strategy](#run-an-updated-backtest-system-overnight-for-a-single-strategy)
      * [Ad-hoc diagnostics](#ad-hoc-diagnostics)
         * [Recent FX prices](#recent-fx-prices)
         * [Recent futures contract prices (FIX ME TO DO)](#recent-futures-contract-prices-fix-me-to-do)
         * [Recent multiple prices (FIX ME TO DO)](#recent-multiple-prices-fix-me-to-do)
         * [Recent adjusted prices (FIX ME TO DO)](#recent-adjusted-prices-fix-me-to-do)
         * [Roll information](#roll-information)
         * [Examine pickled backtest state object](#examine-pickled-backtest-state-object)
      * [Housekeeping](#housekeeping)
         * [Delete old pickled backtest state objects](#delete-old-pickled-backtest-state-objects)
         * [Clean up old log files](#clean-up-old-log-files)
         * [Truncate echo log files](#truncate-echo-log-files)
   * [Scheduling](#scheduling)
      * [Issues to consider when constructing the schedule](#issues-to-consider-when-constructing-the-schedule)
      * [A suggested schedule in pseudocode](#a-suggested-schedule-in-pseudocode)
      * [Formal list of scheduled tasks](#formal-list-of-scheduled-tasks)
      * [Choice of scheduling systems](#choice-of-scheduling-systems)
         * [Linux cron](#linux-cron)
         * [Windows task scheduler](#windows-task-scheduler)
         * [Python](#python)
         * [Manual system](#manual-system)
   * [Production system concepts](#production-system-concepts)
      * [Configuration files](#configuration-files)
         * [Private config](#private-config)
         * [System defaults](#system-defaults)
         * [Strategy config](#strategy-config)
      * [Strategies](#strategies)
   * [Production system data and data flow](#production-system-data-and-data-flow)
   * [Production system classes](#production-system-classes)
      * [Data blobs and the classes that feed on them](#data-blobs-and-the-classes-that-feed-on-them)
      * [Reporting and diagnostics](#reporting-and-diagnostics)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)



# Quick start guide

This quick start guide assumes the following:

- you are running on a linux box with a minimal distro installation
- you are using interactive brokers
- you are storing data using mongodb
- you have a backtest that you are happy with
- you are happy to store your data and configuration in the /private directory of your pysystemtrade installation

You need to:

- Prerequisites:
    - Install [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git), install or update [python3](https://docs.python-guide.org/starting/install3/linux/). You may also find a simple text editor (like emacs) is useful for fine tuning, and if you are using a headless server then [x11vnc](http://www.karlrunge.com/x11vnc/) is helpful.
    - Add the following environment variables to your .profile: (feel free to use other directories):
        - MONGO_DATA=/home/user_name/data/mongodb/
        - PYSYS_CODE=/home/user_name/pysystemtrade
        - SCRIPT_PATH=/home/user_name/pysystemtrade/sysproduction/linux/scripts
        - ECHO_PATH=/home/user_name/echos
        - MONGO_BACKUP_PATH=/media/shared_network/drive/mongo_backup
    - Create the following directories (again use other directories if you like, but you must modify the .profile above)
        - '/home/user_name/data/mongodb/'
        - '/home/user_name/echos/'
    - Install the pysystemtrade package, and install or update, any dependencies in directory $PYSYS_CODE (it's possible to put it elsewhere, but you will need to modify the environment variables listed above). If using git clone from your home directory this should create the directory '/home/user_name/pysystemtrade/'
    - [Set up interactive brokers](/docs/IB.md), download and install their python code, and get a gateway running.
    - [Install mongodb](https://docs.mongodb.com/manual/administration/install-on-linux/)
    - create a file 'private_config.yaml' in the private directory of [pysystemtrade](#/private) An example in this folder see private_config_example.yaml
    - [check a mongodb server is running with the right data directory](/docs/futures.md#mongo-db) command line: `mongod --dbpath $MONGO_DATA`
    - launch an IB gateway (this could be done automatically depending on your security setup)
- FX data:
    - [Initialise the spot FX data in MongoDB from .csv files](/sysinit/futures/repocsv_spotfx_prices.py) (this will be out of date, but you will update it in a moment)
    - Check that you have got spot FX data present: command line:`. /pysystemtrade/sysproduction/linux/scripts/interactive_diagnostics` option 3, option 33
    - Update the FX price data in MongoDB using interactive brokers: command line:`. /home/your_user_name/pysystemtrade/sysproduction/linux/scripts/update_fx_prices`
- Instrument configuration:
    - Set up futures instrument configuration using this script [instruments_csv_mongo.py](/sysinit/futures/instruments_csv_mongo.py).
- Roll calendars:
    - For *roll configuration* we need to initialise by running the code in this file [roll_parameters_csv_mongo.py](/sysinit/futures/roll_parameters_csv_mongo.py).
    - Create roll calendars for each instrument you are trading. Assuming you are happy to infer these from the supplied data [use this script](/sysinit/futures/rollcalendars_from_providedcsv_prices.py)
- Futures contract prices:
    - [If you have a source of individual futures prices, then backfill them into the Arctic database](/docs/futures.md#get_historical_data)
- Adjusted futures prices:
    - Create 'multiple prices' in Arctic. Assuming you have prices in Artic and roll calendars in csv use [this script](/sysinit/futures/multipleprices_from_arcticprices_and_csv_calendars_to_arctic.py). I recommend *not* writing the multiple prices to .csv, so that you can compare the legacy .csv data with the new prices
    - Create adjusted prices. Assuming you have multiple prices in Arctic use [this script](/sysinit/futures/adjustedprices_from_mongo_multiple_to_mongo.py)
- Live production backtest:
    - Create a yaml config file to run the live production 'backtest'. For speed I recommend you do not estimate parameters, but use fixed parameters, using the [yaml_config_with_estimated_parameters method of systemDiag](/systems/diagoutput.py) function to output these to a .yaml file.
- Scheduling:
    - Initialise the [supplied crontab](/sysproduction/linux/crontab). Note if you have put your code or echos somewhere else you will need to modify the directory references at the top of the crontab.
    - All scripts executable by the crontab need to be executable, so do the following: `cd $SCRIPT_PATH` ; `sudo chmod +x *.*`


Before trading, and each time you restart the machine you should:

- [check a mongodb server is running with the right data directory](/docs/futures.md#mongo-db) command line: `mongod --dbpath $MONGO_DATA` (the supplied crontab should do this)
- launch an IB gateway (this could [be done automatically](https://github.com/ib-controller/ib-controller) depending on your security setup)
- ensure all processes are marked as 'finished' FIXME LINK

Note that the system won't start trading until the next day, unless you manually launch the processes that would ordinarily have been started by the crontab or other [scheduler](#scheduling). [Linux screen](https://linuxize.com/post/how-to-use-linux-screen/) is helpful if you want to launch a process but not keep the window active (eg on a headless machine).

When trading you will need to do the following

- Check reports TO DO LINK TO EACH
- Roll instruments TO DO LINK
- Ad-hoc diagnostics TO DO LINK


# Overview of a production system

Here are the steps you need to follow to set up a production system. I assume you already have a backtested system in pysystemtrade, with appropriate python libraries etc.

1. Consider your implementation options
2. Ensure you have a private area for your system code and configuration
3. Finalise and store your backtested system configuration
4. If you want to automatically execute, or get data from a broker, then set up a broker
5. Set up any other data sources you need.
6. Set up a database for storage, including a backup
7. Have a strategy for reporting, diagnostics, and logs
8. Write some scripts to kick off processes to: get data, get accounting information, calculate optimal positions, execute trades, run reports, and do backups and housekeeping.
9. Schedule your scripts to run regularly
10. Regularly monitor your system, and deal with any problems


# Implementation options

Standard implementation for pysystemtrade is a fully automated system running on a single local machine. In this section I briefly describe some alternatives you may wish to consider.

My own implementation runs on a Linux machine, and some of the implementation details in this document are Linux specific. Windows and Mac users are welcome to contribute with respect to any differences.

## Automation options

You can run pysystemtrade as a fully automated system, which does everything from getting prices through to executing orders. But other patterns make sense. In particular you may wish to do your trading manually, after pulling in prices and generating optimal positions manually. It will also possible to trade manually, but allow pysystemtrade to pick up your fills from the broker rather than entering them manually. You can remove items from the scheduler[]() to achieve this.

If running fully automated, [ib-controller](https://github.com/ib-controller/ib-controller) is very useful.

## Machines, containers and clouds

Pysystemtrade can be run locally in the normal way, on a single machine. But you may also want to consider containerisation (see [my blog post](https://qoppac.blogspot.com/2017/01/playing-with-docker-some-initial.html)), or even implementing on AWS or another cloud solution. You could also spread your implemetation across several local machines.

If spreading your implementation across several machines bear in mind:

- Interactive brokers
   - interactive brokers Gateway will need to have the ip address of all relevant machines that connect to it in the whitelist
   - you will need to modify the `private_config.yaml` system configuration file so it connects to a different IP address `ib_ipaddress: '192.168.0.10'`
- Mongodb
   - Add an ip address to the `bind_ip` line in the `/etc/mongod.conf` file to allow connections from other machines `eg bind_ip=localhost, 192.168.0.10`
   - you will need to modify the `private_config.yaml` system configuration file so it connects to a different IP address `mongo_host: 192.168.0.13`
   - you may want to enforce [further security protocol](https://docs.mongodb.com/manual/administration/security-checklist/)

## Backup machine

If you are running your implementation locally, or on a remote server that is not a cloud, then you should seriously consider a backup machine. The backup machine should have an up to date environment containing all the relevant applications, code and libaries, and on a regular basis you should update the local data stored on that machine (see [backup](#data-backup)). The backup machine doesn't need to be turned on at all times, unless you are trading in such a way that a one hour period without trading would be critical (in my experience, one hour is the maximum time to get a backup machine on line assuming the code is up to date, and the data is less than 24 hours stale). I also encourage you to perform a scheduled 'failover' on regular basis: stop the live machine running (best to do this at a weekend), copy across any data to the backup machine, start up the backup machine. The live machine then becomes the backup.

## Multiple systems

You may want to run multiple trading systems on a single machine. Common use cases are:

- You want to run relative value systems *
- You want different systems for different time frames (eg intra day and slower trading) *
- You want different systems for different asset classes eg stocks and ETFs, or futures
- You want to run the same system, but for different trading accounts (pysystemtrade can't handle multiple accounts natively)
- You want a paper trading and live trading system

*for these cases I plan to implement functionality in pysystemtrade so that it can handle them in the same system.

To handle this I suggest having multiple copies of the pysystemtrade environment. You will have a single crontab, but you will need multiple script, echos and other directories. You will need to change the private config file so it points to different mongo_db database names. If you don't want multiple copies of certain data (eg prices) then you should hardcode the database_name in the relevant files whenever a connection is made eg mongo_db = mongoDb(database_name='whatever'). See storing futures and spot FX data for more detail. Finally you should set the field ib_idoffset in the private config file so that there is no chance of duplicate clientid connections; setting one system to have an id offset of 1, the next offset 1000, and so on should be sufficient.

Finally you should set the field `ib_idoffset` in the [private config file](/private/private_config.yaml) so that there is no chance of duplicate clientid connections; setting one system to have an id offset of 1, the next offset 1000, and so on should be sufficient.

# Code and configuration management

Your trading strategy will consist of pysystemtrade, plus some specific configuration files, plus possibly some bespoke code. You can either implement this as:

- separate environment, pulling in pysystemtrade as a 'yet another library'
- everything in pysystemtrade, with all specific code and configuration in the 'private' directory that is excluded from git uploads.

Personally I prefer the latter as it makes a neat self contained unit, but this is up to you.

### Managing your separate directories of code and configuration

I strongly recommend that you use a code repo system or similar to manage your non pysystemtrade code and configuration. Since code and configuration will mostly be in text (or text like) yaml files a code repo system like git will work just fine. I do not recommend storing configuration in database files that will need to be backed up separately, because this makes it more complex to store old configuration data that can be archived and retrieved if required.

### Managing your private directory

Since the private directory is excluded from the git system (since you don't want it appearing on github!), you need to ensure it is managed separately. I use a bash script which I run in lieu of a normal git add/ commit / push cycle:

```
# pass commit quote as an argument
# For example:
# . commit "this is a commit description string"
#
# copy the contents of the private directory to another, git controlled, directory
#
# we use rsync so we can exclude the git directory; which will screw things up as there is already one there
#
rsync -av ~/pysystemtrade/private/ ~/private --exclude .git
#
# git add/commit/push cycle on the main pysystemtrade directory
#
cd ~/pysystemtrade/
git add *
git commit -m "$1"
git push
#
# git add/commit/push cycle on the copied private directory
#
cd ~/private/
git add *
git commit -m "$1"
git push
```

A second script is run instead of a git pull:

```
# git pull within git controlled private directory copy
cd ~/private/
git pull
# copy the updated contents of the private directory to pysystemtrade private directory
# use rsync to avoid overwriting git metadata
rsync -av ~/private/ ~/pysystemtrade/private --exclude .git
# git pull from main pysystemtrade github repo
cd ~/pysystemtrade/
git pull
```

I use a local git repo for my private directory. Github are now offering free private repos, so that is another option.


# Finalise your backtest configuration

You can just re-run a daily backtest to generate your positions. This will probably mean that you end up refitting parameters like instrument weights and forecast scalars. This is pointless, a waste of time, and potentially dangerous. Instead I'd suggest using fixed values for all fitted parameters in a live trading system.

The following convenience function will take your backtested system, and create a dict which includes fixed values for all estimated parameters:

```python
# Assuming futures_system already contains a system which has estimated values
from systems.diagoutput import systemDiag

sysdiag = systemDiag(system)
sysdiag.yaml_config_with_estimated_parameters('someyamlfile.yaml',
                                              attr_names=['forecast_scalars',
                                                                  'forecast_weights',
                                                                  'forecast_div_multiplier',
                                                                  'forecast_mapping',
                                                                  'instrument_weights',
                                                                  'instrument_div_multiplier'])

```

Change the list of attr_names depending on what you want to output. You can then merge the resulting .yaml file into your simulation .yaml file. Don't forget to turn off the flags for `use_forecast_div_mult_estimates`,`use_forecast_scale_estimates`,`use_forecast_weight_estimates`,`use_instrument_div_mult_estimates`, and `use_instrument_weight_estimates`.  You don't need to change flag for forecast mapping, since this isn't done by default.


# Linking to a broker

You are probably going to want to link your system to a broker, to do one or more of the following things:

- get prices
- get account value and profitability
- do trades
- get trade fills

... although one or more of these can also be done manually.

You should now read [connecting pysystemtrade to interactive brokers](/docs/IB.md). The fields `broker_account`,`ib_ipaddress`, `ib_port` and `ib_idoffset` should be set in the [private config file](/private/private_config.yaml).


# Other data sources

You might get all your data from your broker, but there are good reasons to get data from other sources as well:

- multiple sources can improve accuracy
- multiple sources can provide redundancy in case of feed issues
- you can't get the relevant data from your broker
- the relevant data is cheaper elsewhere

You should now read [getting and storing futures and spot FX data](/docs/futures.md).


# Data storage

Various kinds of data files are used by the pysystemtrade production system. Broadly speaking they fall into the following categories:

- accounting (calculations of profit and loss)
- diagnostics
- prices (see [storing futures and spot FX data](/docs/futures.md))
- positions
- other state and control information
- static configuration files

The default option is to store these all into a mongodb database, except for configuration files which are stored as .yaml and .csv files. Time series data is stored in [arctic](https://github.com/man-group/arctic) which also uses mongodb. Databases used will be named with the value of parameter `mongo_db` in [private config file](/private/private_config.yaml). A seperate Arctic database will have the same name, with the suffix `_arctic`.

## Data backup

### Mongo data

Assuming that you are using the default mongob for storing, then I recommend using [mongodump](https://docs.mongodb.com/manual/reference/program/mongodump/#bin.mongodump) on a daily basis to back up your files. Other more complicated alternatives are available (see the [official mongodb man page](https://docs.mongodb.com/manual/core/backups/)). You may also want to do this if you're transferring your data to e.g. a new machine.

To avoid conflicts you should [schedule](#scheduling) your backup during the 'deadtime' for your system (see [scheduling](#scheduling)).


Linux:
```
# dumps everything into dump directory
# make sure a mongo-db instance is running with correct directory, but ideally without any load; command line: `mongod --dbpath $MONGO_DATA`
mongodump -o ~/dump/

# copy dump directory to another machine or drive. This will create a directory $MONGO_BACKUP_PATH/dump/
cp -rf ~/dump/* $MONGO_BACKUP_PATH
```

This is done by the scheduled backup process (see [scheduling](#scheduling)).

Then to restore, from a linux command line:
```
cp -rf $MONGO_BACKUP_PATH/dump/ ~
# Now make sure a mongo-db instance is running with correct directory
# If required delete any existing instances of the databases. If you don't do this the results may be unpredictable...
mongo
# This starts a mongo client
> show dbs
admin              0.000GB
arctic_production  0.083GB
config             0.000GB
local              0.000GB
meta_db            0.000GB
production         0.000GB
# Most likely we want to remove 'production' and 'arctic_production'
> use production
> db.dropDatabase()
> use arctic_production
> db.dropDatabase()
> exit
# Now we run the restore (back on the linux command line)
mongorestore
```


### Mongo / csv data

As I am super paranoid, I also like to output all my mongo_db data into .csv files, which I then regularly backup. This will allow a system recovery, should the mongo files be corrupted.

This currently supports: FX, individual futures contract prices, multiple prices, adjusted prices, position data, historical trades, capital, contract meta-data, instrument data, optimal positions. Some other state information relating to the control of trading and processes is also stored in the database and this will be lost, however this can be recovered with a litle work: roll status, trade limits, position limits, and overrides. Log data will also be lost; but archived [echo files](#echos-stdout-output) could be searched if neccessary.


```python
from sysproduction.update_backup_to_csv import backup_adj_to_csv

backup_adj_to_csv()
```

Linux script:
```
. $SCRIPT_PATH/update_backup_to_csv
```


# Echoes, Logging, diagnostics and reporting

We need to know what our system is doing, especially if it is fully automated. Here are the methods by which this should be done:

- Echoes of stdout output from processes that are running
- Storage of logging output in a database, tagged with keys to identify them
- Storage of diagnostics in a database, tagged with keys to identify them
- the option to run reports both scheduled and ad-hoc, which can optionally be automatically emailed

## Echos: stdout output

The [supplied crontab](/sysproduction/linux/crontab) contains lines like this:

```
SCRIPT_PATH="$HOME:/workspace3/psystemtrade/sysproduction/linux/scripts"
ECHO_PATH="$HOME:/echos"
#
0 6  * * 1-5 $SCRIPT_PATH/updatefxprices  >> $ECHO_PATH/updatefxprices 2>&1
```

The above line will run the script `updatefxprices`, but instead of outputting the results to stdout they will go to `updatefxprices`. These echo files are must useful when processes crash, in which case you may want to examine the stack trace. Usually however the log files will be more useful.

### Cleaning old echo files

Over time echo files can get... large (my default position for logging is verbose). To avoid this you can run the daily run cleaners process (FIX ME LINK) archives old echo files with a date suffix, and deletes anything more than a month old.

## Logging

Logging in pysystemtrade is done via loggers. See the [userguide for more detail](/docs/userguide.md#logging). The logging levels are:

```
self.log.msg("this is a normal message")
self.log.terse("not really used in production code since everything is logged by default, but if we were only running log=terse then you'd see this but not normal .msg")
self.log.warn("this is a warning message means something unexpected has happened but probably no big deal")
self.log.error("this error message means something bad but recoverable has happened")
self.log.critical("this critical message will always be printed, and an email will be sent to the user if emails are set up. Use this if user action is required, or if a process cannot continue")
```

The default logger in production code is to the mongo database. This method will also try and email the user if a critical message is logged.

### Adding logging to your code

The default for logging is to do this via mongodb. Here is an example of logging code:

```python
from syslogdiag.log import logToMongod as logger

def top_level_function():
    """
    This is a function that's called as the top level of a process
    """

    # can optionally pass mongodb connection attributes here
    log=logger("top-level-function")

    # note use of log.setup when passing log to other components, this creates a copy of the existing log with an additional attribute set
    conn = connectionIB(client=100, log=log.setup(component="IB-connection"))

    ibfxpricedata = ibFxPricesData(conn, log=log.setup(component="ibFxPricesData"))

    arcticfxdata = arcticFxPricesData(log=log.setup(component="arcticFxPricesData"))

    list_of_codes_all = ibfxpricedata.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFx.csv
    log.msg("FX Codes: %s" % str(list_of_codes_all))
    for fx_code in list_of_codes_all:

        # Using log.label permanently adds the labelled attribute (although in this case it will be replaced on each iteration of the loop
        log.label(currency_code = fx_code)
        new_fx_prices = ibfxpricedata.get_fx_prices(fx_code)

        if len(new_fx_prices)==0:
            log.error("Error trying to get data for %s" % fx_code)
            continue



```

The following should be used as logging attributes (failure to do so will break reporting code):

- type: the argument passed when the logger is setup. Should be the name of the top level calling function. Production types include price collection, execution and so on.
- stage: Used by stages in System objects, such as 'rawdata'
- component: other parts of the top level function that have their own loggers
- currency_code: Currency code (used for fx), format 'GBPUSD'
- instrument_code: Self explanatory
- contract_date: Self explanatory, format 'yyyymmdd'
- instrument_order_id, contract_order_id, broker_order_id: Self explanatory, used for live trading
- strategy_name: Self explanatory


### Getting log data back

Python:
```python
from syslogdiag.log import accessLogFromMongodb

# can optionally pass mongodb connection attributes here
mlog = accessLogFromMongodb()
# Return a list of strings per log line
mlog.get_log_items(dict(type="top-level-function")) # any attribute directory here is fine as a filter, defaults to last days results
# Printout log entries
mlog.print_log_items(dict(type="top-level-function"), lookback_days=7) # get last weeks worth
# Return a list of logEntry objects, useful for dissecting
mlog.get_log_items_as_entries(dict(type="top-level-function"))
```

Alternatively you can use the interactive diagnostics function to get old log data (FIX ME LINK)

### Cleaning old logs


This code is run automatically from the daily cleaning code (FIX ME LINK)

Python:

```python
from sysproduction.clean_truncate_log_files import clean_truncate_log_files
clean_truncate_log_files()
```

It defaults to deleting anything more than a year old.


## Reporting

Reports are run regularly to allow you to monitor the system and decide if any action should be taken. You can choose to have them emailed to you. To do this the email address, server and password *must* be set in `private_config.yaml`:

```
email_address: "somebloke@anemailadress.com"
email_pwd: "h0Wm@nyLetter$ub$tiute$"
email_server: 'smtp.anemailadress.com'
```

Reports are run automatically every day by the run reports process (FIX ME LINK), but you can also run ad-hoc reports in the interactive diagnostics tool (FIX ME LINK). Ad hoc reports can be emailed or displayed on screen.


### Roll report (Daily)

The roll report can be run for all markets (default for the email), or for a single individual market (if run on an ad hoc basis). It will also be run when you run the interactive update roll status process (FIX ME LINK) for the relevant market. Here's an example of a roll report, which I've annoted with comments (marked with quotes ""):

```
********************************************************************************
           Roll status report produced on 2020-10-19 17:10:13.280422            
********************************************************************************

"The roll report gives you all the information you need to decide when to roll from one futures contract to the next"

=============================================
       Status and time to roll in days       
=============================================

          Status  Roll_exp  Prc_exp  Crry_exp
EDOLLAR  Passive      -128      972       874

Roll_exp is days until preferred roll set by roll parameters. Prc_exp is days until price contract rolls, Crry_exp is days until carry contract rolls

"When should you roll? Certainly before the current priced contract (what we're currently trading) expires (note for some contracts, eg fixed income, you should roll before the first notice date). If the carry contract is younger (as here) then you will probably want to roll before that expires, assuming that there is enough liquidity, or carry calculations will become stale. Suggested times to roll before an expiry are shown, and these are used in the backtest to generate historical roll dates, but you do not need to treat these as gospel in live trading"

========================================================
                   List of contracts                    
========================================================

                C0         C1         C2        C3 C4 C5
EDOLLAR  20230300c  20230600p  20230900f  20231200      

Suffix: p=price, f=forward, c=carry

"This shows the contracts we're currently primarily trading (price), will trade next (forward), and are using for carry calculation (carry). Other contracts may also be shown."

===========================================
                 Positions                 
===========================================

         Pos0  Pos1  Pos2  Pos3  Pos4  Pos5
EDOLLAR   0.0   0.0  11.0   0.0   0.0   0.0


"The position we have in each contract. Here we are long 11 futures lots in the second contract (which from above is 202309: the forward contract)."

========================================
            Relative volumes            
========================================

           V0    V1    V2   V3   V4   V5
EDOLLAR  0.98  0.82  0.88  1.0  0.0  0.0

Contract volumes over recent days, normalised so largest volume is 1.0

"You can't roll until there is sufficient volume in the forward contract. Often a sign that volume is falling in the price relative to the forward is a sign you should hurry up and roll! Volumes are shown in relative terms to make interpretation easier."

********************************************************************************
                               END OF ROLL REPORT                               
********************************************************************************

```

### P&L report

The p&l report shows you profit and loss (duh!).  On a daily basis it is run for the previous 24 hours. On an ad hoc basis, it can be run for any time period (recent or in the past).

Here is an example, with annotations added in quotes (""):


```

********************************************************************************
P&L report produced on 2020-10-20 09:50:44.037739 from 2020-06-01 00:00:00 to 2020-10-20 09:17:16.470039
********************************************************************************

"Total p&l is what you'd expect. This comes from comparing broker valuations from the two relevant snapshot times. "

Total p&l is -2.746%


"P&L by instrument as a % of total capital. Calculated from database prices and trades. There is a bug in my live cattle price somewhere!"

====================================
P&L by instrument for all strategies
====================================

      codes  pandl
0   LIVECOW -18.10
1   SOYBEAN  -4.08
2      CORN  -1.34
3   EUROSTX  -0.81

".... truncated"

19      OAT   2.29
20      BTP   3.88
21    WHEAT   5.03

"If we add up our futures P&L and compare to the total p&l, we get a residual. This could be because of a bug (as here), but also fees and interest charges, or non futures instruments which aren't captured by the instrument p&l, or because of a difference in timing between the broker account valuation and the relevant prices."

Total futures p&l is -12.916%
Residual p&l is 10.171%

===============================
        P&L by strategy        
===============================

"P&L versus total capital, not the capital for the specific strategy. So these should all add up to total p&l"

                   codes  pandl
0  medium_speed_TF_carry -13.42
1               ETFHedge  -0.63
2  _ROLL_PSEUDO_STRATEGY   0.00
0               residual  11.31


==================
P&L by asset class
==================

    codes  pandl
0     Ags -18.51
1  Equity  -0.81
2     Vol  -0.36
3  OilGas  -0.24
4    STIR  -0.11
5  Metals   0.16
6      FX   1.15
7    Bond   5.81


********************************************************************************
                               END OF P&L REPORT                                
********************************************************************************

```

### Status report

The status report monitors the status of processes and data acquisition, plus all control elements. It is run on a daily basis, but can also be run ad hoc. Here is an example report, with annotations in quotes(""):

```

********************************************************************************
              Status report produced on 2020-10-19 23:02:57.321674              
********************************************************************************

"A process is called by the scheduler, eg crontab. Processes have start/end times, and can also have pre-requisite processes that need to have been run recently. This provides a quick snapshot to show if the system is running normally"

===============================================================================================================================================================================================================================
                                                                                                     Status of processses                                                                                                      
===============================================================================================================================================================================================================================

name                 run_capital_update run_daily_prices_updates             run_stack_handler                   run_reports   run_backups                  run_cleaners               run_systems run_strategy_order_generator
running                           False                    False                         False                          True          True                         False                      True                        False
start                       10/19 01:00              10/19 20:05                   10/19 00:30                   10/19 23:00   10/19 22:20                   10/19 22:10               10/19 22:05                  10/19 21:55
end                         10/19 19:08              10/19 22:05                   10/19 19:30                   10/16 23:54   10/16 23:14                   10/19 22:10               10/16 22:55                  10/19 21:57
status                               GO                       GO                            GO                            GO            GO                            GO                        GO                           GO
finished_in_last_day               True                     True                          True                         False         False                          True                     False                         True
start_time                     01:00:00                 20:00:00                      00:01:00                      23:00:00      22:20:00                      22:10:00                  01:00:00                     01:00:00
end_time                       19:30:00                 23:00:00                      19:30:00                      23:59:00      23:59:00                      23:59:00                  23:00:00                     23:00:00
required_machine                   None                     None                          None                          None          None                          None                      None                         None
right_machine                      True                     True                          True                          True          True                          True                      True                         True
time_to_run                       False                    False                         False                          True          True                          True                     False                        False
previous_required                  None       run_capital_update  run_strategy_order_generator  run_strategy_order_generator  run_cleaners  run_strategy_order_generator  run_daily_prices_updates                  run_systems
previous_finished                  True                     True                          True                          True          True                          True                      True                        False
time_to_stop                       True                     True                          True                         False         False                         False                      True                         True


"Methods are called from within processes. We list the methods in reverse order from when they last ran; older processes first. If something hasn't run for some reason it will be at the top of this list. "

=============================================================================================
                                      Status of methods                                      
=============================================================================================

                                                           process_name last_run_or_heartbeat
method_or_strategy                                                                           
update_total_capital                                 run_capital_update           10/19 19:08
strategy_allocation                                  run_capital_update           10/19 19:08
handle_completed_orders                               run_stack_handler           10/19 19:26
process_fills_stack                                   run_stack_handler           10/19 19:26

"....truncated for space...."

status_report                                               run_reports           10/19 23:00
backup_arctic_to_csv                                        run_backups           10/19 23:00


"Here's a list of all adjusted prices we've generated and FX rates. Again, listed oldest first. If a market closes or something goes wrong then the price would be stale. Notice the Asian markets near the top for which we've had no price since this morning - not a surprise, and the FX rates with timestamp 23:00 which means they're daily prices (I don't collect intraday FX prices). "

==============================================
Status of adjusted price / FX price collection
==============================================

                last_update
name                       
KOSPI   2020-10-19 08:00:00
KR3     2020-10-19 08:00:00
KR10    2020-10-19 08:00:00
OAT     2020-10-19 18:00:00
CAC     2020-10-19 19:00:00

"....truncated for space...."

US20    2020-10-19 21:00:00
JPYUSD  2020-10-19 23:00:00
AUDUSD  2020-10-19 23:00:00
CADUSD  2020-10-19 23:00:00
CHFUSD  2020-10-19 23:00:00
EURUSD  2020-10-19 23:00:00
GBPUSD  2020-10-19 23:00:00
HKDUSD  2020-10-19 23:00:00
KRWUSD  2020-10-19 23:00:00


"Optimal positions are generated by the backtest that runs daily; this hasn't quite finished yet hence these are from the previous friday."

=====================================================
        Status of optimal position generation        
=====================================================

                                          last_update
name                                                 
medium_speed_TF_carry/AEX     2020-10-16 22:54:20.386
medium_speed_TF_carry/AUD     2020-10-16 22:54:21.677
medium_speed_TF_carry/BOBL    2020-10-16 22:54:22.386
medium_speed_TF_carry/BTP     2020-10-16 22:54:22.999

"....truncated for space...."

medium_speed_TF_carry/V2X     2020-10-16 22:54:57.874
medium_speed_TF_carry/VIX     2020-10-16 22:54:58.551
medium_speed_TF_carry/WHEAT   2020-10-16 22:55:00.283


"This shows the status of any trade and position limits: I've just reset these so the numbers are pretty boring"

=========================================================================================================================================
                                                         Status of trade limits                                                          
=========================================================================================================================================

                      instrument_code  period_days  trade_limit  trades_since_last_reset  trade_capacity_remaining  time_since_last_reset
strategy_name                                                                                                                            
                                 US10            1            3                        0                         3 0 days 00:00:00.000015
medium_speed_TF_carry            US10            1            3                        0                         3 0 days 00:00:00.000011
                                  KR3            1           12                        0                        12 0 days 00:00:00.000011
                                  AEX            1            1                        0                         1 0 days 00:00:00.000010

"....truncated for space...."

                                  V2X            1            6                        0                         6 0 days 00:00:00.000010
                                  OAT            1            2                        0                         2 0 days 00:00:00.000010
                                  US5           30           35                        0                        35 3 days 06:04:32.129139
                              EUROSTX           30            8                        0                         8 3 days 06:03:49.437166

"....truncated for space...."

                               COPPER           30            3                        0                         3 3 days 05:56:49.324062
                                WHEAT           30            6                        0                         6 3 days 05:56:36.958089
                                  V2X           30           32                        0                        32 3 days 05:56:26.776116
                                  OAT           30           11                        0                        11 3 days 05:56:21.616143


"Notice where we have a position we report on the limit, even if none is set. In this case I've set instrument level, but not strategy/instrument position limits"

=====================================================
              Status of position limits              
=====================================================

                             keys  position pos_limit
0    medium_speed_TF_carry/GAS_US      -1.0  no limit
1       medium_speed_TF_carry/AUD       1.0  no limit
2      medium_speed_TF_carry/BOBL       2.0  no limit

"....truncated for space...."

12      medium_speed_TF_carry/BTP       3.0  no limit
13      medium_speed_TF_carry/MXP       4.0  no limit
0                             V2X      -5.0        35
1                             BTP       3.0        10
2                         LEANHOG       0.0         8

"....truncated for space...."

34                           US10       0.0        16
35                        LIVECOW       0.0        11
36                        EDOLLAR      11.0        86
37                            US5       0.0        39


"Overrides allow us to reduce or eliminate positions temporarily in specific instruments, but I'm not using these right now"

===================
Status of overrides
===================

Empty DataFrame
Columns: [override]
Index: []

"Finally we check for instruments that are locked due to a position mismatch: see the reconcile report for details"

Locked instruments (position mismatch): []

********************************************************************************
                              END OF STATUS REPORT                              
********************************************************************************
```


### Trade report

The trade report lists all trades recorded in the database, and allows you to analyse slippage in very fine detail.  On a daily basis it is run for the previous 24 hours. On an ad hoc basis, it can be run for any time period (recent or in the past).

Here is an example, with annotations added in quotes (""):

```

********************************************************************************
              Trades report produced on 2020-10-20 09:25:43.596580              
********************************************************************************

"Here is a list of trades with basic information. Note that due to an issue with the way roll trades are displayed, they are shown with fill 0."

==================================================================================================================
                                                  Broker orders                                                   
==================================================================================================================

         instrument_code          strategy_name           contract_id       fill_datetime    fill     filled_price
order_id                                                                                                          
30365                V2X  medium_speed_TF_carry            [20201200] 2020-10-02 07:51:53    (-1)           (27.7)
30366                KR3  medium_speed_TF_carry            [20201200] 2020-10-05 01:01:00     (1)         (112.01)

"....truncated for space...."


30378            EDOLLAR  medium_speed_TF_carry            [20230900] 2020-10-14 13:50:32    (-1)          (99.61)
30380               CORN  _ROLL_PSEUDO_STRATEGY  [20201200, 20211200] 2020-10-15 09:25:54  (0, 0)  (397.75, 394.0)
30379                V2X  _ROLL_PSEUDO_STRATEGY  [20201100, 20201200] 2020-10-15 09:24:32  (0, 0)   (25.25, 24.25)
30383                V2X  _ROLL_PSEUDO_STRATEGY  [20201100, 20201200] 2020-10-15 09:43:30  (0, 0)     (25.5, 24.4)
30388               KR10  medium_speed_TF_carry            [20201200] 2020-10-20 02:00:21     (1)         (133.03)


================================================================================================================================================================
                                                                             Delays                                                                             
================================================================================================================================================================

"We now look at timing. When was the parent order generated (the order at instrument level that generated this specific order) versus when the order was submitted to the broker? Normally this is the night before, when the backtest is run, but for roll orders there are no parents, and also for manual orders. In our simulation we assume that orders are generated with a one business day delay. Here we're mostly doing better than that. Once submitted, how long did it take to fill the order? Issues with timestamps when I ran this report mean that some orders that apparently got filled before they were submitted, we ignore these. "

         instrument_code          strategy_name parent_generated_datetime         submit_datetime       fill_datetime submit_minus_generated filled_minus_submit
order_id                                                                                                                                                        
30365                V2X  medium_speed_TF_carry   2020-10-01 21:56:29.669 2020-10-02 08:50:03.637 2020-10-02 07:51:53                  39214                 NaN
30366                KR3  medium_speed_TF_carry   2020-10-02 21:57:41.427 2020-10-05 02:00:07.262 2020-10-05 01:01:00                 187346                 NaN
30367            EDOLLAR  medium_speed_TF_carry                       NaT 2020-10-05 12:43:01.885 2020-10-05 11:48:02                    NaN                 NaN
30368            EDOLLAR  medium_speed_TF_carry   2020-10-06 21:58:12.765 2020-10-07 00:30:32.000 2020-10-06 23:35:32                9139.24                 NaN

"....truncated for space...."

30380               CORN  _ROLL_PSEUDO_STRATEGY                       NaT 2020-10-15 09:24:46.000 2020-10-15 09:25:54                    NaN                  68
30379                V2X  _ROLL_PSEUDO_STRATEGY                       NaT 2020-10-15 09:22:16.000 2020-10-15 09:24:32                    NaN                 136
30383                V2X  _ROLL_PSEUDO_STRATEGY                       NaT 2020-10-15 09:41:42.000 2020-10-15 09:43:30                    NaN                 108
30388               KR10  medium_speed_TF_carry   2020-10-16 22:54:38.166 2020-10-20 02:00:16.000 2020-10-20 02:00:21                 270338                   5


==========================================================================================================================================================================================================================================================
                                                                                                                 Slippage (ticks per lot)                                                                                                                 
==========================================================================================================================================================================================================================================================

"We can calculate slippage in many different units. We start with 'ticks', units of price (not strictly ticks I do know that...). The reference price is the price when we generated the parent order (usually the closing price from the day before). The mid price is the mid price when we submit. The side price is the price we would pay if we submitted a market order (the best bid if we're selling, best offer if we're buying). The limit price is whatever the algo submits the order for initially. Normally an algo will try and execute passively, so the limit price would normally be the best offer if we're selling, best bid if we're buying. Alternatively, if the parent order has a limit (for strategies that try and achieve particular prices) the algo should use that price. The filled price is self explanatory. We can then measure our slippage in different ways: caused by delay (side price versus reference price - delays tend to add a lot of variability, but usually net out very close to zero in our backtest (checking actual delays over a long period of time should confirm this), caused by bid/ask spread (mid versus side price, which is what we assume we pay in a backtest), and caused by execution (side price versus fill, if our algo is doing it's thing this should offset some of our costs). We can also measure the quality of our execution (initial limit versus fill) and how we did versus the required limit order (if relevant). Negative numbers are bad (we paid), positive are good (we earned). Take the first order as an example (V2X sell one contract) with no parent order limit price, the market moved 0.225 points in our favour from 27.45 the night before to a mid of 27.675 (bid 27.65, offer 27.7). If we'd paid up we would have sold at 27.65 side price (bid/ask cost -0.025). We submitted a limit order of 27.7 at the offer, and were filled there. So our execution cost was positive 0.05. Our total trading cost was -0.025+0.05 = 0.025."

         instrument_code          strategy_name    trade parent_reference_price parent_limit_price calculated_mid_price calculated_side_price limit_price calculated_filled_price   delay bid_ask execution versus_limit versus_parent_limit total_trading
order_id                                                                                                                                                                                                                                                  
30365                V2X  medium_speed_TF_carry     (-1)                  27.45               None               27.675                 27.65        27.7                    27.7   0.225  -0.025      0.05           -0                 NaN         0.025
30366                KR3  medium_speed_TF_carry      (1)                 112.08               None              111.995                   112      111.99                  112.01   0.085  -0.005     -0.01        -0.02                 NaN        -0.015
30367            EDOLLAR  medium_speed_TF_carry     (-1)                    NaN               None              99.6725                 99.67      99.675                   99.67     NaN -0.0025        -0       -0.005                 NaN       -0.0025
30368            EDOLLAR  medium_speed_TF_carry     (-1)                 99.645               None              99.6425                 99.64      99.645                   99.64 -0.0025 -0.0025        -0       -0.005                 NaN       -0.0025

"....truncated for space...."

30380               CORN  _ROLL_PSEUDO_STRATEGY  (1, -1)                    2.5               None                    4                  4.25        3.75                    3.75    -1.5   -0.25       0.5            0                 NaN          0.25
30379                V2X  _ROLL_PSEUDO_STRATEGY  (1, -1)                   0.85               None                 1.05                  1.15           1                       1    -0.2    -0.1      0.15            0                 NaN          0.05
30383                V2X  _ROLL_PSEUDO_STRATEGY  (1, -1)                   0.85               None                 1.05                  1.15        0.95                     1.1    -0.2    -0.1      0.05        -0.15                 NaN         -0.05
30388               KR10  medium_speed_TF_carry      (1)                 132.45               None              133.035                133.04      133.03                  133.03  -0.585  -0.005      0.01            0                 NaN         0.005


=======================================================================================================================================================================
                                                         Slippage (normalised by annual vol, BP of annual SR)                                                          
=======================================================================================================================================================================

"Ticks are meaningless as it depends on how volatile an instrument is. We divide by the annual vol of an instrument, in price terms, to get a normalised figure. This is  multiplied by 10000 to get a basis point figure. For example the V2X trade had bid/ask slippage of 0.025, and the annual vol is currently 11.585; that works out to 0.025 / 11.585 = 0.00216, or 21.6 basis points. Note that ignoring holding costs using my 'speed limit' concept we'd be able to do 0.13 / 0.00216 = 60 trades a year in V2X (or 48 if you assume monthly rolls), to put it another way the cost budget is 1300 basis points."

         instrument_code          strategy_name    trade last_annual_vol delay_vol bid_ask_vol execution_vol versus_limit_vol versus_parent_limit_vol total_trading_vol
order_id                                                                                                                                                               
30365                V2X  medium_speed_TF_carry     (-1)         11.5805   194.292    -21.5879       43.1759               -0                     NaN           21.5879
30366                KR3  medium_speed_TF_carry      (1)        0.829709   1024.46    -60.2621      -120.524         -241.048                     NaN          -180.786
30367            EDOLLAR  medium_speed_TF_carry     (-1)        0.224771       NaN    -111.224            -0         -222.448                     NaN          -111.224
30368            EDOLLAR  medium_speed_TF_carry     (-1)        0.224771  -111.224    -111.224            -0         -222.448                     NaN          -111.224

"....truncated for space...."

30380               CORN  _ROLL_PSEUDO_STRATEGY  (1, -1)         71.6612  -209.318    -34.8864       69.7727                0                     NaN           34.8864
30379                V2X  _ROLL_PSEUDO_STRATEGY  (1, -1)         11.5805  -172.704    -86.3518       129.528                0                     NaN           43.1759
30383                V2X  _ROLL_PSEUDO_STRATEGY  (1, -1)         11.5805  -172.704    -86.3518       43.1759         -129.528                     NaN          -43.1759
30388               KR10  medium_speed_TF_carry      (1)         4.18168  -1398.96    -11.9569       23.9138                0                     NaN           11.9569


==================================================================================================================================================================================
                                                                           Slippage (In base currency)                                                                            
==================================================================================================================================================================================

"Finally we can work out the slippage in base currency, i.e. actual money cost by multiplying ticks by the value of a price point in base currency (GBP for me)"

         instrument_code          strategy_name    trade value_of_price_point delay_cash bid_ask_cash execution_cash versus_limit_cash versus_parent_limit_cash total_trading_cash
order_id                                                                                                                                                                          
30365                V2X  medium_speed_TF_carry     (-1)              90.8755     20.447     -2.27189        4.54377                -0                      NaN            2.27189
30366                KR3  medium_speed_TF_carry      (1)              677.198    57.5618     -3.38599       -6.77198           -13.544                      NaN            -10.158
30367            EDOLLAR  medium_speed_TF_carry     (-1)               1930.7        NaN     -4.82676             -0          -9.65352                      NaN           -4.82676
30368            EDOLLAR  medium_speed_TF_carry     (-1)               1930.7   -4.82676     -4.82676             -0          -9.65352                      NaN           -4.82676

"....truncated for space...."

30380               CORN  _ROLL_PSEUDO_STRATEGY  (1, -1)              38.6141   -57.9211     -9.65352         19.307                 0                      NaN            9.65352
30379                V2X  _ROLL_PSEUDO_STRATEGY  (1, -1)              90.8755   -18.1751     -9.08755        13.6313                 0                      NaN            4.54377
30383                V2X  _ROLL_PSEUDO_STRATEGY  (1, -1)              90.8755   -18.1751     -9.08755        4.54377          -13.6313                      NaN           -4.54377
30388               KR10  medium_speed_TF_carry      (1)              677.198   -396.161     -3.38599        6.77198                 0                      NaN            3.38599

"Then follows a very long section, which is only really useful for doing annual analysis of trades (unless you trade a lot!). For each type of slippage (delay, bid/ask, execution, versus limit, versus parent limit, total trading [execution + bid/ask]) we calculate summary statistics for each instrument and strategy: the total, count, mean, lower and upper range (+/- two standard deviations), in three ways: ticks, vol adjusted, and base currency cash."

```



### Reconcile report

The reconcile report checks the consistency of positions and trades stored in the database, and with the broker. It is run on a daily basis, but can also be run ad hoc. Here is an example, with annotations added in quotes (""):

```

********************************************************************************
            Reconcile report produced on 2020-10-19 23:31:23.329834             
********************************************************************************

"Optimal positions are set by the nightly backtest. For this strategy we set an upper and lower buffer region, so two figures are shown for the optimal. A break occurs if the position is outside the buffer region. For example you can see for BTP that the current position (long 3) is higher than the upper buffer(2.4, rounded to 2). This eithier means that the relevant market hasn't traded yet, or there is something wrong with the system (check the status report to see if a process or method hasn't run)."

=============================================================
               Optimal versus actual positions               
=============================================================

                               current        optimal  breaks
medium_speed_TF_carry AEX          0.0   -0.029/0.029   False
medium_speed_TF_carry AUD          1.0    1.030/1.301   False
medium_speed_TF_carry BOBL         2.0    1.696/2.107   False
medium_speed_TF_carry BTP          3.0    2.211/2.432    True
medium_speed_TF_carry BUND         0.0   -0.069/0.069   False

"....truncated for space...."

medium_speed_TF_carry JPY          0.0   -0.177/0.177   False
medium_speed_TF_carry KOSPI        0.0   -0.028/0.028   False
medium_speed_TF_carry KR10         1.0    1.953/2.131    True
medium_speed_TF_carry KR3          8.0    8.655/9.567    True
medium_speed_TF_carry LEANHOG      0.0  -0.616/-0.316   False

"....truncated for space...."

medium_speed_TF_carry VIX          1.0    0.410/0.541   False
medium_speed_TF_carry WHEAT        0.0   -0.135/0.115   False

"We now look at positions at a contract level, and compare those in the database with those that the broker has recorded"

==========================================
             Positions in DB              
==========================================

   instrument_code contract_date  position
7              AUD      20201200       1.0
4             BOBL      20201200       2.0
5              BTP      20201200       3.0

"....truncated for space...."

14             V2X      20201200      -5.0
12             VIX      20201200       1.0


==========================================
             Positions broker             
==========================================

   instrument_code contract_date  position
10             AUD      20201214       1.0
9             BOBL      20201208       2.0
5              BTP      20201208       3.0

"....truncated for space...."

11             V2X      20201216      -5.0
12             VIX      20201216       1.0

"We now check for position breaks. These are of three kinds: an instrument position is out of line with the optimal, the instrument positions are out of line with the aggregate across contract positions, or the broker and database disagree on what the contract level positions are. The first problem should be fixed automatically if the system is running properly; the second or third may require the creation of manual trades: see interactive_stack_handler script."

Breaks Optimal vs actual [medium_speed_TF_carry BTP, medium_speed_TF_carry KR10, medium_speed_TF_carry KR3]
 Breaks Instrument vs Contract []
 Breaks Broker vs Contract []

"We now compare the orders in the database for the last 24 hours with those the broker has on record. No automated check is done, but you can do this visually. No trades were done for this report so I've pasted in trades from another day to illustrate what it looks like. You can see the trades match up (ignore the fills shown as 0 this is an artifact of the way trades are stored)."


=========================================================================================================
                                              Trades in DB                                               
=========================================================================================================

                         strategy_name           contract_id       fill_datetime    fill     filled_price
instrument_code                                                                                          
CORN             _ROLL_PSEUDO_STRATEGY  [20201200, 20211200] 2020-10-15 09:25:54  (0, 0)  (397.75, 394.0)
V2X              _ROLL_PSEUDO_STRATEGY  [20201100, 20201200] 2020-10-15 09:24:32  (0, 0)   (25.25, 24.25)
V2X              _ROLL_PSEUDO_STRATEGY  [20201100, 20201200] 2020-10-15 09:43:30  (0, 0)     (25.5, 24.4)


=================================================================================================
                                       Trades from broker                                        
=================================================================================================

                strategy_name           contract_id       fill_datetime     fill     filled_price
instrument_code                                                                                  
V2X                            [20201118, 20201216] 2020-10-15 09:24:32  (1, -1)   (25.25, 24.25)
CORN                           [20201214, 20211214] 2020-10-15 09:25:54  (1, -1)  (397.75, 394.0)
V2X                            [20201118, 20201216] 2020-10-15 09:43:30  (1, -1)     (25.5, 24.4)



********************************************************************************
                              END OF STATUS REPORT                              
********************************************************************************


```


### Strategy report

The strategy report is bespoke to a strategy; it will load the last backtest file generated and report diagnostics from it. On a daily basis it runs for all strategies. On an ad hoc basis, it can be run for all or a single strategy.

The strategy reporting is determined by the parameter `strategy_list/strategy_name/reporting_code/function` in default.yaml or overriden in the private config .yaml file. The 'classic' reporting function is `sysproduction.strategy_code.report_system_classic.report_system_classic`

Here is an example, with annotations added in quotes (""):

```

********************************************************************************
Strategy report for medium_speed_TF_carry backtest timestamp 20201012_215827 produced at 2020-10-12 23:15:08.677151
********************************************************************************



================================================================================================================================================================================================================================================================================================================================================================================
                                                                                                                                                                              Unweighted forecasts                                                                                                                                                                              
================================================================================================================================================================================================================================================================================================================================================================================

"This is a matrix of all forecast values for each instrument, before weighting. Not shown for space reasons"


================================================================================================================================================================================================================================================================================================================================================================================
                                                                                                                                                                                Forecast weights                                                                                                                                                                                
================================================================================================================================================================================================================================================================================================================================================================================

"This is a matrix of all forecast weights for each instrument, before weighting. Not shown for space reasons"



================================================================================================================================================================================================================================================================================================================================================================================
                                                                                                                                                                               Weighted forecasts                                                                                                                                                                               
================================================================================================================================================================================================================================================================================================================================================================================

"This is a matrix of all forecast values for each instrument, after weighting. Not shown for space reasons"

"Here we calculate the vol target for the strategy"

Vol target calculation {'base_currency': 'GBP', 'percentage_vol_target': 25.0, 'notional_trading_capital': 345040.64, 'annual_cash_vol_target': 86260.16, 'daily_cash_vol_target': 5391.26}

"Now we see how the instrument vol is calculated. These figures are also calculated independently in the risk report"

================================================================
                        Vol calculation                         
================================================================

         Daily return vol       Price  Daily % vol  annual % vol
AEX                6.3238    573.2500       1.1031       17.6504
AUD                0.0045      0.7214       0.6267       10.0272

"... truncated for space"

VIX                0.7086     27.7000       2.5580       40.9277
WHEAT             10.7527    596.5000       1.8026       28.8420


=========================================================================================================================================
                                                           Subsystem position                                                            
=========================================================================================================================================

"Calculation of subsystem positions: the position we'd have on if the entire system was invested in a single instrument. Abbreviations won't make sense unless you've read my first book, 'Systematic Trading'"

         Block_Value  Daily price % vol         ICV    FX      IVV  Daily Cash Vol Tgt  Vol Scalar  Combined forecast  subsystem_position
AEX          1146.50               1.10     1264.76  0.91  1094.74             5391.26        4.92               0.00                0.00
AUD           721.40               0.63      452.10  0.77   352.52             5391.26       15.29               9.02               13.79

"... truncated for space"

V2X            23.90               3.29       78.57  0.91    68.01             5391.26       79.28             -10.36              -82.15
VIX           277.00               2.56      708.56  0.77   552.48             5391.26        9.76               8.80                8.59
WHEAT         298.25               1.80      537.63  0.77   419.21             5391.26       12.86               1.07                1.38


=================================================================
                       Portfolio positions                       
=================================================================


"Final notional positions"

         subsystem_position  instr weight  IDM  Notional position
AEX                   0.000         0.022  2.5              0.000
AUD                  13.792         0.033  2.5              1.149

"... truncated for space"

V2X                 -82.154         0.025  2.5             -5.135
VIX                   8.592         0.025  2.5              0.537
WHEAT                 1.379         0.033  2.5              0.115


===============================================================================================
                                     Positions vs buffers                                      
===============================================================================================

"Shows the calculation of buffers. The position at timestamp is the position when the backtest was run; the current position is what we have on now"

         Notional position  Lower buffer  Upper buffer  Position at timestamp  Current position
AEX                    0.0          -0.0           0.0                    0.0               0.0
AUD                    1.1           1.0           1.3                    1.0               1.0

"... truncated for space"

V2X                   -5.1          -5.6          -4.6                   -4.0              -4.0
VIX                    0.5           0.5           0.6                    1.0               1.0
WHEAT                  0.1           0.0           0.2                    0.0               0.0

End of report for medium_speed_TF_carry

```


### Risk report

The risk report.... you're smart people, you can guess. It is run on a daily basis, but can also be run ad hoc. Here is an example, with annotations added in quotes (""):

```

********************************************************************************
               Risk report produced on 2020-10-19 23:54:09.835241               
********************************************************************************

"Our expected annual standard deviation is 10.6% a year, across everything"

Total risk across all strategies, annualised percentage 10.6

========================================
Risk per strategy, annualised percentage
========================================

"We now break this down by strategy, taking into account the capital allocated to each strategy. The 'roll pseduo strategy' is used to generate roll trades and should never have any risk on. ETFHedge is another nominal strategy"


                               risk
_ROLL_PSEUDO_STRATEGY  0
medium_speed_TF_carry  10.6
ETFHedge               0


============================================================================================================================================================================================================================================================
                                                                                                                      Instrument risk                                                                                                                       
============================================================================================================================================================================================================================================================

"Detailed risk calculations for each instrument. Most of these are, hopefully, self explanatory, but in case they aren't, from left to right: daily standard deviation in price units, annualised std. dev in price units, the price, daily standard deviation in % units (std dev in price terms / price), annual % std. dev, the point size (the value of a 1 point price movement) expressed in the base currency (GBP for me), the contract exposure value in GBP (point size * price), daily risk standard deviation in GBP for owning one contract (daily % std dev * exposure value, or daily price std dev * point size), annual risk per contract (daily risk * 16), current position, total capital at risk, exposure of position held as % of capital (contract exposure * position / capital), annual risk of position held as % of capital (annual risk per contract / capital)."

         daily_price_stdev  annual_price_stdev   price  daily_perc_stdev  annual_perc_stdev  point_size_base  contract_exposure  daily_risk_per_contract  annual_risk_per_contract  position   capital  exposure_held_perc_capital  annual_risk_perc_capital
GAS_US                 0.1                 1.5     3.3               2.9               46.6           7722.8            25423.5                    740.4                   11845.6      -1.0  353675.6                        -7.2                      -3.3
EUROSTX               36.4               582.0  3207.0               1.1               18.1              9.1            29143.8                    330.5                    5288.6      -2.0  353675.6                       -16.5                      -3.0
V2X                    0.7                11.6    24.9               2.9               46.5             90.9             2262.8                     65.8                    1052.4      -5.0  353675.6                        -3.2                      -1.5
"... truncated for space"PLAT                  22.7               363.9   855.5               2.7               42.5             38.6            33034.3                    878.1                   14050.1       1.0  353675.6                         9.3                       4.0
BTP                    0.3                 5.4   149.4               0.2                3.6            908.8           135777.1                    307.7                    4923.3       3.0  353675.6                       115.2                       4.2


============================================================================================================
                                                Correlations                                                
============================================================================================================

"Correlation of *instrument* returns - doesn't care about sign of position"

          V2X   OAT   BTP   KR3  SOYBEAN  KR10   AUD  GAS_US  PLAT   VIX  BOBL  EDOLLAR   MXP  EUROSTX  CORN
V2X      1.00  0.19 -0.14  0.12    -0.22  0.21 -0.56    0.01 -0.30  0.77  0.21     0.41 -0.48    -0.71 -0.08
OAT      0.19  1.00  0.46  0.22    -0.05  0.19 -0.09   -0.10 -0.12  0.09  0.60     0.39 -0.16    -0.13 -0.11
BTP     -0.14  0.46  1.00  0.08    -0.01  0.09  0.22   -0.10  0.04 -0.04  0.17     0.02 -0.13     0.06 -0.06

"... truncated for space"

MXP     -0.48 -0.16 -0.13 -0.15     0.29 -0.13  0.48   -0.09  0.32 -0.56 -0.14    -0.33  1.00     0.44  0.11
EUROSTX -0.71 -0.13  0.06 -0.08     0.17 -0.15  0.53    0.00  0.17 -0.54 -0.32    -0.43  0.44     1.00  0.02
CORN    -0.08 -0.11 -0.06 -0.06     0.68 -0.10  0.08    0.05  0.13 -0.10 -0.25    -0.15  0.11     0.02  1.00


********************************************************************************
                               END OF RISK REPORT                               
********************************************************************************


```


# Production system data flow

Update FX prices / Update manual check FX prices  (interactive)
Input: IB fx prices
Output: Spot FX prices

Update roll adjusted prices (interactive)
Input: Manual decision, existing multiple price series
Output: Current set of active contracts (price, carry, forward), Roll calendar (implicit in updated multiple price series)

Update sampled contracts
Input: Current set of active contracts (price, carry, forward) implicit in multiple price series
Output: Contracts to be sampled by historical data

Update historical prices / Update manual check historical prices (interactive)
Input: Contracts to be sampled by historical data, IB futures prices
Output: Futures prices per contract

Update multiple adjusted prices
Input: Futures prices per contract, Existing multiple price series, Existing adjusted price series
Output: Adjusted price series, Multiple price series

Update account values / update capital manual  (interactive)
Input: Brokerage account value from IB
Output: Total capital. Account level p&l

[Update strategy capital](#allocate-capital-to-strategies)
Input: Total capital
Output: Capital allocated per strategy

Run systems
Input: Capital allocated per strategy, Adjusted futures prices, Multiple price series, Spot FX prices
Output: Optimal positions and buffers per strategy

Run strategy order generator
Input:  Optimal positions and buffers per strategy
Output: Order tickets

Run stack handler
Input: Order tickets
Output: Trades


# Positions and order levels

At this stage it's worth discussing the different kinds

## Instrument level

### Instrument positions

### Instrument orders

### Spreads


## Contract level

### Contract positions

### Contract orders

### Spreads


## Broker level

### Broker positions

### Broker orders


# Orders and execution

## Desired execution

## Executing spreads


# Scripts

Scripts are used to run python code which:

- runs different parts of the trading system, such as:
   - get price data
   - get FX data
   - calculate positions
   - execute trades
   - get accounting data
- fix any issues or basically interactively meddle with the system
- runs report and diagnostics, either regular or ad-hoc
- Do housekeeping duties, eg truncate log files and run backups

Script are then called by [schedulers](#scheduling), or on an ad-hoc basis from the command line.

## Script calling

I've created scripts that run under Linux, however these all just call simple python functions so it ought to be easy to create your own scripts in another OS.

So, for example, here is the [run reports script](/sysproduction/linux/scripts/run_reports):

```
#!/bin/bash
. ~/.profile
. p sysproduction.run_reports.run_reports
```

In plain english this will call the python function `run_reports()`, located in `/sysproduction/run_reports.py` By convention all 'top level' python functions should be located in this folder, and the file name, script name, and top level function name ought to be the same.

Scripts are run with the following linux convenience [script](/sysproduction/linux/scripts/p) that just calls run.py with the single argument in the script that is the code reference for the function:

```
python3 run.py $1
```

run.py is a little more complicated as it allows you to call python functions that require arguments, such as [interactive_update_roll_status](/sysproduction/interactive_update_roll_status).


## Script naming convention

The following prefixes are used for scripts:

- _backup: run a backup.
- _clean: run a housekeeping / cleaning process
- _interactive: run an interactive process to check or fix the system, avoiding diving into python every time something goes wrong
- _update: update data in the system (price or capital)
- startup: run when the machine starts
- _run: run a regularly scheduled process.

Normally it's possible to call a process directly (eg _backup_files) on an ad-hoc basis, or it will be called regularly through a 'run' process that may do other stuff as well  (eg run_backups, runs all backup processses). Run processes are a bit complicated, as I've foolishly written my own scheduling code, so see this section FIX ME for more. Some exceptions are interactive scripts which only run when called, and run_systems / run_strategy_order_generator which do not have seperate scripts.

## Run processes

These are listed here for convenience, but more documentation is given below in the relevant section for each script

- run_backups: Runs backup_arctic_to_csv (FIX ME LINK), backup_files (FIX ME LINK)
- run_capital_updates: Runs update_strategy_capital, update_total_capital (FIX ME LINKS)
- run_cleaners: Runs clean_truncate_backtest_states, clean_truncate_echo_files, clean_truncate_log_files (FIX ME LINKS)
- run_daily_price_updates: Runs update_fx_prices, update_sampled_contracts, update_historical_prices, update_multiple_adjusted_prices (FIX ME LINKS)
- run_reports: Runs all reports (FIX ME LINK), you can also run these using interactive_diagnostics (FIX ME LINK)
- run_stack_handler: Executes trades placed on the stack by run_strategy_order_generator (FIX ME LINK)
- run_strategy_order_generator: Creates trades based on the output of run_systems (FIX ME LINK)
- run_systems: Runs a backtest to decide what optimal positions are required (FIX ME LINK)


## Core production system components

These control the core functionality of the system.

### Get spot FX data from interactive brokers, write to MongoDB (Daily)

Python:
```python
from sysproduction.updateFxPrices import update_fx_prices

update_fx_prices()
```

Linux script:
```
. $SCRIPT_PATH/update_fx_prices
```

Called by: `run_daily_price_updates`


This will check for 'spikes', unusually large movements in FX rates either when comparing new data to existing data, or within new data. If any spikes are found in data for a particular contract it will not be written. The system will attempt to email the user when a spike is detected. The user will then need to [manually check the data](#manual-check-of-fx-price-data).
.

The threshold for spikes is set in the default.yaml file, or overidden in the private config, using the paramater `max_price_spike`. Spikes are defined as a large multiple of the average absolute daily change. So for example if a price typically changes by 0.5 units a day, and `max_price_spike=6`, then a price change larger than 3 units will trigger a spike.


### Update sampled contracts (Daily)

This ensures that we are currently sampling active contracts, and updates contract expiry dates.

Python:
```python
from sysproduction.update_sampled_contracts import updated_sampled_contracts
update_sampled_prices()
```

Linux script:
```
. $SCRIPT_PATH/update_sampled_contracts
```

Called by: `run_daily_price_updates`


### Update futures contract historical price data (Daily)

This gets historical daily data from IB for all the futures contracts marked to sample in the mongoDB contracts database, and updates the Arctic futures price database.
If update sampled contracts has not yet run, it may not be getting data for all the contracts you need.

Python:
```python
from sysproduction.update_historical_prices import update_historical_prices
update_historical_prices()
```

Linux script:
```
. $SCRIPT_PATH/update_historical_prices
```

Called by: `run_daily_price_updates`

This will get daily closes, plus intraday data at the frequency specified by the parameter `intraday_frequency` in the defaults.yaml file (or overwritten in the private .yaml config file). It defaults to 'H: hourly'.

This will check for 'spikes', unusually large movements in price either when comparing new data to existing data, or within new data. If any spikes are found in data for a particular contract it will not be written. The system will attempt to email the user when a spike is detected. The user will then need to [manually check the data](#manual-check-of-futures-contract-historical-price-data).
.

The threshold for spikes is set in the default.yaml file, or overidden in the private config .yaml file, using the paramater `max_price_spike`. Spikes are defined as a large multiple of the average absolute daily change. So for example if a price typically changes by 0.5 units a day, and `max_price_spike=8`, then a price change larger than 4 units will trigger a spike.



### Update multiple and adjusted prices (Daily)

This will update both multiple and adjusted prices with new futures per contract price data.

It should be scheduled to run once the daily prices for individual contracts have been updated.

Python:
```python
from sysproduction.update_multiple_adjusted_prices import update_multiple_adjusted_prices_daily
update_multiple_adjusted_prices_daily()
```

Linux script:
```
. $SCRIPT_PATH/update_multiple_adjusted_prices
```

Called by: `run_daily_price_updates`


Spike checks are not carried out on multiple and adjusted prices, since they should hopefully be clean if the underlying per contract prices are clean.


### Update capital and p&l by polling brokerage account
(daily)

See [capital](#capital) to understand how capital works. On a daily basis we need to check how our brokerage account value has changed. This will be used to update our total available capital, and allocate that to individual strategies.

Python:
```python
from sysproduction.update_account_values
update_account_values()
```

Linux script:
```
. $SCRIPT_PATH/update_account_values
```

Called by: `run_capital_update`


If the brokers account value changes by more than 10% then capital will not be adjusted, and you will be sent an email. You will then need to run `modify_account_values`. This will repeat the poll of the brokerage account, and ask you to confirm if a large change is real. The next time `update_account_values` is run there will be no error, and all adjustments will go ahead as normal.


### Allocate capital to strategies

Allocates total capital to individual strategies. See [strategy capital](#strategy-capital) for more details. Will not work if `update_account_values` has not run at least once, or capital has been manually initialised by `update_capital_manual`.

Python:
```python
from sysproduction.update_strategy_capital import update_strategy_capital
update_strategy_capital()
```

Linux script:
```
. $SCRIPT_PATH/update_strategy_capital
```

Called by: `run_capital_update`


### Run updated backtest systems for one or more strategies
(Usually overnight)

The paradigm for pysystemtrade is that we run a new backtest nightly, which outputs some parameters that a trading engine uses the next day. For the basic system defined in the core code those parameters are a pair of position buffers for each instrument. The trading engine will trade if the current position lies outside those buffer values.

This can easily be adapted for different kinds of trading system. So for example, for a mean reversion system the nightly backtest could output the target prices for the range. For an intraday system it could output the target position sizes and entry  / exit points. This process reduces the amount of work the trading engine has to do during the day.


Python:
```python
from sysproduction.update_run_systems import update_run_systems
run_system()
```

Linux script:
```
. $SCRIPT_PATH/update_system_example
```

The code to run each strategies backtest is defined in the configuration parameter in the default.yaml file (or overriden in the private yaml config): `strategy_list/strategy_name/run_systems`. The sub-parameters do the following:

- `object` the class of the code that runs the system, eg `sysproduction.strategy_code.run_system_classic.runSystemClassic`
- `function` the method of the class that runs the system eg `run_system_classic`
- `backtest_config_filename` the location of the .yaml configuration file to pass to the strategy runner eg `systems.provided.futures_chapter15.futures_config.yaml`
- `max_executions` the number of times the backtest should be run on each iteration of run_systems. Normally 1, unless you have some whacky intraday system. Can be omitted.
- `frequency` how often, in minutes, the backtest is run. Normally 60 (but only relevant if max_executions>1). Can be omitted.

See [launcher functions](#launcher-functions) and scheduling processes (FIX ME) for more details.

The backtest will use the most up to date prices and capital, so it makes sense to run this after these have updated(see FIX ME).

### Generate orders for each strategy

Once each strategy knows what it wants to do, we generate orders. These will depend on the strategy; for the classic system we generate optimal positions that are then compared with current positions to see what trades are needed (or not). Other strategies may have specific limits ('buy but only at X or less'). Importantly these are *instrument orders*. These will then be mapped to actual *contract level* orders (FIX ME SEE LINKS).

Python:
```python
from sysproduction.run_strategy_order_generator import run_strategy_order_generator
run_strategy_order_generator()
```

Linux script:
```
. $SCRIPT_PATH/run_strategy_order_generator
```

The code to run each strategies backtest is defined in the configuration parameter in the default.yaml file (or overriden in the private yaml config): `strategy_list/strategy_name/run_systems`. The sub-parameters do the following:

- `object` the class of the code that generates the orders, eg `sysexecution.strategies.classic_buffered_positions.orderGeneratorForBufferedPositions`.
- `function` the method of the class that generates the orders eg `get_and_place_orders`
- `max_executions` the number of times the generator should be run on each iteration of run_systems. Normally 1, unless you have some whacky intraday system. Can be omitted.
- `frequency` how often, in minutes, the generator is run. Normally 60 (but only relevant if max_executions>1). Can be omitted.

See [launcher functions](#launcher-functions) and scheduling processes (FIX ME) for more details.



### Execute orders

Once we have orders on the instrument stack (put there by the order generator), we need to execute them. This is done by the stack handler, which handles all three order stacks (instrument stack, contract stack and broker stack).

Python:
```python
from sysproduction.run_stack_handler import run_stack_handler
run_stack_handler()
```

Linux script:
```
. $SCRIPT_PATH/run_stack_handler
```

The behaviour of the stack handler is extremely complex (and it's worth reading FIX ME, before reviewing this section). Here is the normal path an order takes:

- Instrument order created (by the strategy order generator)
- Spawn a contract order from an instrument order
- Create a broker order from a contract order and submit this to the broker
- Manage the execution of the order (technically done by execution algo code, but this is called by the stack handler), and note any fills that are returned
- Pass fills upwards; if a broker order is filled then the contract order should reflect that, and if a contract order is filled then an instrument order should reflect that
- Update position tables when fills are received
- Handle completed orders (which are fully filled) by deleting them from the stack after copying them to the historic order table

In addition the stack handler will:

- Check that the broker and database positions are aligned at contract level, if not then it will lock the instrument so it can't be traded (locks can be cleared automatically once positions reconcile again, or using interactive_stack_handler FIX ME LINK).
- Generate roll orders if a roll status is FORCE or FORCELEG (see FIX ME LINK)
- Safely clear the order stacks at the end of the day or when the process is stopped by cancelling existing orders, and deleting them from the order stack.

That's quite a list, hence the use of the interactive_order_stack (FIX ME LINK) to keep it in check!

## Interactive scripts to modify data

### Manual check of futures contract historical price data
(Whever required)

You should run these if the normal price collection has identified a spike (for which you'd be sent an email, if you've set that up).

Python:
```python
from sysproduction.interactive_manual_check_historical_prices import interactive_manual_check_historical_prices
interactive_manual_check_historical_prices(instrument_code)
```

Linux script:
```
. $SCRIPT_PATH/interactive_manual_check_historical_prices
```

The script will pull in data from interactive brokers, and the existing data, and check for spikes. If any spikes are found, then the user is interactively asked if they wish to (a) accept the spiked price, (b) use the previous time periods price instead, or (c) type a number in manually. You should check another data source to see if the spike is 'real', if so accept it, otherwise type in the correct value. Using the previous time periods value is only advisable if you are fairly sure that the price change wasn't real and you don't have a source to check with.

If a new price is typed in then that is also spike checked, to avoid fat finger errors. So you may be asked to accept a price you have have just typed in manually if that still results in a spike. Accepted or previous prices are not spike checked again.

Spikes are only checked on the FINAL price in each bar, and the user is only given the opportunity to correct the FINAL price. If the FINAL price is changed, then the OPEN, HIGH, and LOW prices are also modified; adding or subtracting the same adjustment that was made to the final price. The system does not currently use OHLC prices, but you should be aware of this creating potential inaccuracies. VOLUME figures are left unchanged if a price is corrected.

Once all spikes are checked for a given contract then the checked data is written to the database, and the system moves on to the next contract.


### Manual check of FX price data
(Whever required)

You should run these if the normal price collection has identified a spike (for which you'd be sent an email, if you've set that up).


Python:
```python
from sysproduction.interactive_manual_check_fx_prices import interactive_manual_check_fx_prices
interactive_manual_check_fx_prices(fx_code)
```

Linux script:
```
. $SCRIPT_PATH/interactive_manual_check_fx_prices
```

See [manual check of futures contract prices](#manual-check-of-futures-contract-historical-price-data) for more detail. Note that as the FX data is a single series, no adjustment is required for other values.


### Interactively modify capital values

Python:
```python
from sysproduction.interactive_update_capital_manual import interactive_update_capital_manual
interactive_update_capital_manual()
```

Linux script:
```
. $SCRIPT_PATH/interactive_update_capital_manual
```

See [capital](#capital) to understand how capital works.
This function is used interactively to control total capital allocation in any of the following scenarios:

- You want to initialise the total capital available in the account. If this isn't done, it will be done automatically when `update_account_values` runs with default values. The default values are brokerage account value = total capital available = maximum capital available (i.e. you start at HWM), with accumulated profits = 0. If you don't like any of these values then you can initialise them differently.
- You have made a withdrawal or deposit in your brokerage account, which would otherwise cause the apparent available capital available to drop, and needs to be ignored
- There has been a large change in the value of your brokerage account. A filter has caught this as a possible error, and you need to manually confirm it is ok.
- You want to delete capital entries for some recent period of time (perhaps because you missed a withdrawal and it screwed up your capital)
- You want to delete all capital entries (and then probably reinitialise). This is useful if, for example, you've been running a test account and want to move to production.
- You want to make some other modification to one or more capital entries. Only do this if you know exactly what you are doing!




### Interactively roll adjusted prices
(Whenever required)

Allows you to change the roll state and roll from one priced contract to the next.

Python:
```python
from sysproduction.interactive_update_roll_status import interactive_update_roll_status
interactive_update_roll_status(instrument_code)
```

Linux script:
```
. $SCRIPT_PATH/interactive_update_roll_status
```

The first thing the process will do is create and print a roll report. See the roll report (FIX ME LINK) for more information on how to interpret the information shown. You will then have the option of switching between roll modes. Not all modes will be allowed, depending on the current positions that you are holding and the current roll state.

The possible options are:

- No roll. Obvious.
- Passive. This will tactically reduce positions in the priced contract, and open new positions in the forward contract.
- Force. This will pause all normal trading in the relevant instrument, and the stack handler will create a calendar spread trade to roll from the priced to the forward contract.
- Force legs. This will pause all normal trading, and create two outright trades (closing the priced contract position, opening a forward position).
- Roll adjusted. This is only possible if you have no positions in the current price contract. It will create a new adjusted and multiple price series, hence the current forward contract will become the new priced contract (and everything else will shift accordingly).


## Menu driven interactive scripts

The remaining interactive scripts allow you to view and control a large array of things, and hence are menu driven. There are three such scripts:

- interactive_controls: Trade limits, position limits, process control and monitoring
- interactive_diagnostics: View backtest objects, generate ad hoc reports, view logs/emails and errors; view prices, capital, positions & orders, and configuration.
- interactive_order_stack: View order stacks and positions, create orders, net/cancel orders, lock/unlock instruments, delete and clean up the order stack.

Menus are nested, and a common pattern is that <return> will go back a step, or exit.

### Interactive controls

Tools to control the system's behaviour, including operational risk controls.

Python:
```python
from sysproduction.interactive_controls
interactive_controls()
```

Linux script:
```
. $SCRIPT_PATH/interactive_controls
```

#### Trade limits

We can set limits for the maximum number of trades we will done over a given period, and for a specific instrument, or a specific instrument within a given strategy. Limits are applied within run_stack_handler whenever a broker order is about to be generated from a contract order. Options are as follows:

- View limits
- Change limits (instrument, instrument & strategy)
- Reset limits (instrument, instrument & strategy): helpful if you have reached your limit but want to keep trading, without increasing the limits upwards
- Autopopulate limits

Autopopulate uses current levels of risk to estimate the appropriate trade limit. So it will make limits smaller when risk is higher, and vice versa. It makes a lot of assumptions when setting limits: that all your strategies have the same risk limit (which you can set), and the same IDM (also can be modified), and that all instruments have the same instrument weight (which you can set), and trade at the same speed (again you can set the maximum proportion of typical position traded daily). It does not use actual instrument weights, and it only sets limits that are global for a particular instrument. It also assumes that trade sizes scale with the square root of time for periods greater than one day.

#### Position limits

We can set the maximum allowable position that can be held in a given instrument, or by a specific strategy for an instrument. An instrument trade that will result in a position which exceeds this limit will be rejected (this occurs when run_strategy_order_generator is run). We can:

- View limits
- Change limits (instrument, instrument & strategy)
- Autopopulate limits

Autopopulate uses current levels of risk to estimate the appropriate position limit. So it will make position limits smaller when risk is higher, and vice versa. It makes a lot of assumptions when setting limits: that all your strategies have the same risk limit (which you can set), and the same IDM (also can be modified), and that all instruments have the same instrument weight (which you can set). It does not use actual instrument weights, and it only sets limits that are global for a particular instrument.


#### Trade control / override

Overrides allow us to reduce positions for a given strategy, for a given instrument (across all strategies), or for a given instrument & strategy combination. They are eithier:

- a multiplier, between 0 and 1, by which we multiply the desired . A multiplier of 1 is equal to 'normal', and 0 means 'close everything'
- a flag, allowing us only to submit trades which reduce our positions
- a flag, allowing no trading to occur in the given instrument.

Instrument trades will be modified to achieve any required override effect (this occurs when run_strategy_order_generator is run). We can:

- View overrides
- Update / add / remove overide (for strategy, instrument, or instrument & strategy)


#### Process control & monitoring

Allows us to control how processes behave.

See scheduling FIX ME LINK


##### View processes

Here's an example of the relevant output, start/end times, currently running, status, and PID (process ID).

```
run_capital_update: Last started 2020-10-21 01:00:01.412000 Last ended 2020-10-20 19:07:07.112000 is running, status GO, PID 86140
run_daily_prices_updates: Last started 2020-10-20 20:05:12.405000 Last ended 2020-10-21 09:27:04.973000 is not running, status GO, PID None
run_systems: Last started 2020-10-21 10:59:00.898000 Last ended 2020-10-21 12:16:52.191000 is not running, status GO, PID None
run_strategy_order_generator: Last started 2020-10-21 12:18:20.953000 Last ended 2020-10-21 12:20:23.840000 is not running, status GO, PID None
run_stack_handler: Last started 2020-10-21 09:30:14.443000 Last ended 2020-10-21 09:26:51.279000 is running, status GO, PID 88642
run_reports: Last started 2020-10-20 23:00:00.059000 Last ended 2020-10-20 23:58:00.790000 is not running, status GO, PID None
run_cleaners: Last started 2020-10-20 22:10:00.134000 Last ended 2020-10-20 22:10:01.731000 is not running, status GO, PID None
run_backups: Last started 2020-10-20 22:20:00.589000 Last ended 2020-10-20 23:33:04.582000 is not running, status GO, PID None
```

You can use the PID to check using the Linux command line eg `ps aux | grep 86140` if a process really is running (in this case I'm checking if run_capital_update really is still going), or if it's abnormally aborted (in which case you will need to change it to 'not running' before relaunching - see below).

Note that processes that have launched but waiting to properly start (perhaps because it is not their scheduled start time) will be shown as not running and will have no PID registered. You can safely kill them.

#####  Change status of process

You can change the status of any process to STOP, GO or NO RUN. A process which is NO RUN will continue running, but won't start again. This is the correct way to stop processes that you want to kill, as it will properly update their process state and (importantly in the case of run stack handler) do a graceful exit. Stop processes will only stop once they have finished running their current method, which means for run_systems and run_strategy_order_generator they will stop when the current strategy has finished processing (which can take a while!).

If a process refuses to STOP, then as a last resort you can use `kill NNNN` at the command line where NNNN is the PID, but there may be data corruption, or weird behaviour (particularly if you do this with the stack handler), and you will definitely need to mark it as finished (see below).

Marking a process as START won't actually launch it, you will have to do this manually or wait for the crontab to run it. Nor will the process run if it's preconditions aren't met (start and end time window, previous process).

#####  View process configuration

This allows you to see the configuration for each process, eithier from defaults.yaml or the private yaml config file. See scheduling FIX ME LINK


#####  Mark as finished

This will manually mark a process as finished. This is done automatically when a process finishes normally, or is told to stop, but if it terminates unexpectedly then the status may well be set as 'running', which means a new version of the process can't be launched until this flag is cleared. Marking a process as finished won't stop it if it is still running! Use 'change status' instead. Check the process PID isn't running using `ps aux | grep NNNNN` where NNNN is the PID, before marking it as finished.

Note that the startup script will also mark all processes as finished (as there should be no processes running on startup).

### Interactive diagnostics

Tools to view internal diagnostic information.

Python:
```python
from sysproduction.interactive_diagnostics import interactive_diagnostics
interactive_diagnostics()
```

Linux script:
```
. $SCRIPT_PATH/interactive_diagnostics
```

#### Backtest objects

It's often helpful to examine the backtest output of run_systems to understand where particular trades came from (above and beyond what the strategy report FIX ME LINK gives you). These are saved as a combination of pickled cache and configuration .yaml file, allowing you to see the calculations done when the system ran.

##### Output choice

First of all you can choose your output:

- Interactive python. This loads the backtest, and effectively opens a small python interpreter (actually it just runs eval on the input).
- Plot. This loads a menu allowing you to choose a data element in the backtest, which is then plotted (may fail on headless servers)
- Print. This loads a menu allowing you to choose a data element in the backtest, which is then printed to screen.
- HTML. This loads a menu allowing you to choose a data element in the backtest, which is then output to an HTML file (outputs to ~/temp.html), which can easily be web browsed

##### Choice of strategy and backtest

Next you can choose your strategy, and the backtest you want to see- all backtests are saved with a timestamp (normally these are kept for a few days, SEE FIX ME LINK). The most recent backtest file is the default.

##### Choose stage / method / arguments

Unless you're working in 'interactive python' mode, you can then choose the stage and method for which you want to see output. Depending on exactly what you've asked for, you'll be asked for other parameters like the instrument code and possibly trading rule name. The time series of calling the relevant method will then be shown to you using your chosen output method.

##### Alternative python code

If you prefer to do this exercise in your python environment, then this will interactively allow you to choose a system and dated backtest, and returns the system object for you to do what you wish.

```python
from sysproduction.data.backtest import dataBacktest
d = dataBacktest()
system = d.system
```


#### Reports

Allows you to run any of the reports on an ad-hoc basis FIX ME LINK.

#### Logs, errors, emails

Allows you to look at various system diagnostics.

##### View stored emails

The system sends emails quite a bit: when critical errors occur, when reports are sent, and when price spikes occur. To avoid spamming a user, it won't send an email with the same subject line as a previous email sent in the last 24 hours. Instead these emails are stored, and if you view them here they will be printed and then deleted from the store. The most common case is if you get a large price move which affects many different contracts for the same instrument; the first spike email will be sent, and the rest stored.

##### View errors

Log entries are tagged with a level; higher levels are more likely to be serious errors. You can view log entries for any time period at a given level. In theory this could be ordinary messages, but you'd be better off using 'view logs' which allows you to filter logs further.

##### View logs

You can view logs filtered by any group of attributes, over a given period. Log attributes are selected iteratively, until you have narrowed down exactly what you want to look at.

Alternatively you can do this in python directly:

```python
from sysproduction.data.logs import diagLogs
d = diagLogs()
lookback_days = 1
d.get_list_of_unique_log_attribute_keys(lookback_days = lookback_days) # what attributes do we have eg type, instrument_code...
d.get_list_of_values_for_log_attribute("type", lookback_days=lookback_days ) # what value can an attribute take
d.get_log_items(dict(instrument_code = "EDOLLAR", type = "process_fills_stack"), lookback_days=lookback_days) # get the log items with some attribute dict
```


#### View prices

View dataframes for historical prices. Options are:

- Individual futures contract prices
- Multiple prices
- Adjusted prices
- FX prices

#### View capital

View historical series of capital. See FIX ME LINK for more details on how capital works. You can see the:

- Capital for a strategy
- Total capital (across all strategies): current capital
- Total capital: broker valuation
- Total capital: maximum capital
- Total capital: accumulated returns

#### Positions and orders

View historic series of positions and orders. Options are:

- Optimal position history (instruments for strategy)
- Actual position history (instruments for strategy)
- Actual position history (contracts for instrument)
- List of historic instrument level orders (for strategy)
- List of historic contract level orders (for strategy and instrument)
- List of historic broker level orders (for strategy and instrument)
- View full details of any individual order (of any type)


#### Instrument configuration

##### View instrument configuration data

View the configuration data for a particular instrument, eg for EDOLLAR:

```{'Description': 'US STIR Eurodollar', 'Exchange': 'GLOBEX', 'Pointsize': 2500.0, 'Currency': 'USD', 'AssetClass': 'STIR', 'Slippage': 0.0025, 'PerBlock': 2.11, 'Percentage': 0.0, 'PerTrade': 0.0}```

Note there may be further configuration stored in other places, eg broker specific.

#####  View contract configuration data

View the configuration for a particular contract, eg:

```{'contract_date_dict': {'expiry_date': (2023, 6, 19), 'contract_date': '202306', 'approx_expiry_offset': 0}, 'instrument_dict': {'instrument_code': 'EDOLLAR'}, 'contract_params': {'currently_sampling': True}}
Rollcycle parameters hold_rollcycle:HMUZ, priced_rollcycle:HMUZ, roll_offset_day:-1100.0, carry_offset:-1.0, approx_expiry_offset:18.0```

See FIXME to understand roll parameters.

### Interactive order stack

Allows us to examine and control the various order stacks SEE FIX ME FOR LINK.

Python:
```python
from sysproduction.interactive_order_stack import interactive_order_stack
interactive_order_stack()
```

Linux script:
```
. $SCRIPT_PATH/interactive_order_stack
```

#### View

Options are:

- View specific order (on any stack)
- View instrument order stack
- View contract order stack
- View broker order stack (as stored in the local database)
- View broker order stack (will get all the active orders and completed trades from the broker API)
- View positions (optimal, instrument level, and contract level from the database; plus contract level from the broker API)

#### Create orders

Orders will normally be created by run_strategy_order_generator or by run_stack_handler, but sometimes its useful to do these manually.

##### Spawn contract orders from instrument orders
##### Create force roll contract orders
##### Create (and try to execute...) IB broker orders
##### Balance trade: Create a series of trades and immediately fill them (not actually executed)
##### Balance instrument trade: Create a trade just at the strategy level and fill (not actually executed)
##### Manual trade: Create a series of trades to be executed
##### Cash FX trade


#### Netting, cancellation and locks

##### Cancel broker order
##### Net instrument orders
##### Lock/unlock order
##### Lock/unlock instrument code
##### Unlock all instruments

#### Delete and clean

##### Delete entire stack (CAREFUL!)
##### Delete specific order ID (CAREFUL!)
##### End of day process (cancel orders, mark all orders as complete, delete orders)




## Reporting, housekeeping and backup scripts

### Run all reports

Python:
```python
from sysproduction.run_reports import run_reports
run_reports()
```

Linux script:
```
. $SCRIPT_PATH/run_reports
```

See reporting for details on individual reports FIX ME LINK

See reporting and diagnostics for details on report configuration FIX ME LINK

### Delete old pickled backtest state objects

Python:
```python
from sysproduction.clean_truncate_backtest_states
clean_truncate_backtest_states()
```

Linux script:
```
. $SCRIPT_PATH/clean_truncate_backtest_states
```

Called by: `run_cleaners`



### Clean up old logs


Python:
```python
from sysproduction.clean_truncate_log_files import clean_truncate_log_files
clean_truncate_log_files()
```

Linux command line:
```
cd $SCRIPT_PATH
. clean_truncate_log_files
```

Called by: `run_cleaners`

### Truncate echo files

Python:
```python
from sysproduction.clean_truncate_echo_files import clean_truncate_echo_files
clean_truncate_echo_files()
```

Linux command line:
```
cd $SCRIPT_PATH
. clean_truncate_echo_files
```

Called by: `run_cleaners`


### Backup Arctic data to .csv files

Python:
```python
from sysproduction.backup_arctic_to_csv import backup_arctic_to_csv
backup_arctic_to_csv()
```

Linux script:
```
. $SCRIPT_PATH/backup_arctic_to_csv
```

Called by: `run_backups`


### Backup files


Python:
```python
from sysproduction.backup_files import backup_files
backup_files()
```

Linux script:
```
. $SCRIPT_PATH/backup_files
```

Called by: `run_backups`


### Start up script



Python:
```python
from sysproduction.startup import startup
startup()
```

Linux script:
```
. $SCRIPT_PATH/startup
```

Clear IB client IDs: Do this when the machine restarts and IB is definitely not running (FIX ME TO DO)



# Scheduling

Running a fully or partially automated trading system requires the use of scheduling software that can launch new scripts at regular intervals, for example:

- processes that kick off when a machine is switched on
- processes that kick off daily
- processes that kick off several times a day (eg regular reports or reconciliation)


## Issues to consider when constructing the schedule

Things to consider when constructing a schedule include:

- Machine load   (eg avoid running computationally intensive processes when also trading where latency could be important). This is less important if you are running multiple machines.
- Database thrashing (eg avoid running input intensive reporting processes on database tables that are being actively read / written to by more important live trading processes)
- File lock / integrity (eg avoid running backups whilst active writes are occuring)
- Robustness (eg it's probably better to have trading processes shutting down each night and then restarting in the morning, than trying to keep them running continously)


## A suggested schedule in pseudocode

Here is the schedule I use for my own trading system. Since I trade US, European, and Asian markets, I trade between midnight (9am in Asia) and 8pm (4pm in New York) local UK time. This reduces the 'dead time' when reporting and backups can take place to between 8pm and midnight.

- Midnight: If you are restarting IB Gateway on a daily basis, do it now
- Midnight: Launch processes for monitoring account value, executing trades, generating trades, and gathering intraday prices
- 6am: Get daily spot FX prices
- 6am: Run some lightweight morning reports
- 8pm: Stop processes for monitoring account value, executing trades, and gathering intraday prices
- 8pm: Clear client id tracker used by IB to avoid conflicts
- 8:30pm: Get daily 'closing' prices (some of these may not be technically closes if markets have not yet closed)
- 9:00pm: Run daily reports, and any computationally intensive processes (like running a backtest based on new prices)
- 11pm: If you are restarting IB Gateway on a daily basis, close it now.
- 11pm: Run backups
- 11pm: Truncate echo files, discard log file entries more than one year old, clear IB locked client IDs

There will be flexibility in this schedule depending on how long different processes take. Notice that I don't shut down and then launch a new interactive brokers gateway daily. Some people may prefer to do this, but I am using an authentication protocol which requires manual intervention. [This product](https://github.com/ib-controller/ib-controller/) is popular for automating the lauch of the IB gateway.

## Formal list of scheduled tasks

TO DO


## Choice of scheduling systems

You need some sort of scheduling system to kick off the various top level processes.

### Linux cron

Because I use cron myself, there are is a [cron tab included in pysystemtrade](https://github.com/robcarver17/pysystemtrade/blob/master/sysproduction/linux/crontab).

### Windows task scheduler

I have not used this product (I don't use Windows or Mac products for ideological reasons, also they're rubbish and overpriced respectively), but in theory it should do the job.

### Python

You can use python itself as a scheduler, using something like [this](https://github.com/dbader/schedule), which gives you the advantage of being platform independent. However you will still need to ensure there is a python instance running all the time. You also need to be careful about whether you are spawning new threads or new processes, since only one connection to IB Gateway or TWS can be launched within a single process.

### Manual system

It's possible to run pysystemtrade without any scheduling, by manually starting the neccessary processes as required. This option might make sense for traders who are not running a fully automated system.

# Production system concepts

## Configuration files

### Private config

TO DO
### System defaults


TO DO

### List of production configuration options

TO DO
max_price_spike
strategy_list
base_currency
production_capital_method
strategy_capital_allocation:
  function: sysproduction.strategy_code.strategy_allocation.weighted_strategy_allocation
  strategy_weights:
    medium_speed_TF_carry: 100.0


## Capital

*Capital* is how much we have 'at risk' in our trading account. This total capital is then allocated to trading strategies; see [strategy-capita](#strategy-capital) on a [daily basis](#update-capital-and-p&l-by-polling-brokerage-account).

The simplest possible case is that your capital at risk is equal to what is in your trading account. If you do nothing else, that is how the system will behave. For all other cases, the behaviour of capital will depend on the interaction between stored capital values and the parameter value `production_capital_method` (defaults to *full* unless set in private yaml config). If you want to do things differently, you should consider modifying that parameter and/or using the [interactive tool](#interactively-modify-capital-values) to modify or initialise capital.

On initialising capital you can choose what the following values are:

- Brokerage account value (defaults to value from brokerage API). You might want to change this if you have stitched in some capital from another system, otherwise usually leave as the default
- Current capital allocated (defaults to brokerage account value).
- Maximum capital allocated (defaults to current capital). This is only used if `production_capital_method='half'`. It's effectively the 'high water mark' for your strategy. You might want to set this higher than current capital if for example you have already been running the strategy elsewhere, and it's accumulated losses. Although you can set it lower than current capital, there is no logical reason for doing that.
- Accumulated profits and losses (defaults to zero). Doesn't affect capital calculations, but is nice to know. You may want to set this if you've already been running the strategy elsewhere.

If you don't initialise capital deliberately, then the first time that is run it will populate the fields with the defaults (which will effectively mean your capital will be equal to your current trading account value).

After initialising the capital is updated [daily](#update-capital-and-p&l-by-polling-brokerage-account). First the valuation of the brokerage account is captured, and compared to the previous valuation. The difference between the valuations is your profit (or loss) since the capital was last checked, and this is written to the p&l accumulation account.

What will happen next will depend on `production_capital_method`. Read [this first](https://qoppac.blogspot.com/2016/06/capital-correction-pysystemtrade.html):

- if *full*, then your profit or loss is added to capital employed. For tidiness, maximum capital is set to be equal to current capital employed. This will result in your returns being compounded. This is the default.
- if *half* then your profit or loss is added to capital employed, until your capital is equal to the maximum capital employed. After that no further profits accrue to your capital. This is 'Kelly compatible' because losses reduce capital, but your returns will not be compounded. It's the method I use myself.
- if *fixed* then no change is made to capital. For tidiness, maximum capital is set to be equal to current capital employed. This isn't recommended as it isn't 'Kelly compatible', and if you lose money you will make exponentially increasing losses as a % of your account value. It could plausibly make sense in a small test account where you want to maintain a minimum position size.

Capital is mostly 'fire and forget', with a few exceptions which require the interactive tool to deal with:

### Large changes in capital

If brokerage account value has changed by more than 10% no further action is taken as it's likely this is an erroneous figure. An email is sent, and you are invited to run the [interactive tool](#interactively-modify-capital-values) choosing option 'Update capital from IB account value'. The system will get the valuation again, and if the change is still larger than 10% you will have the option of accepting this (having checked it yourself of course!).


### Withdrawals and deposits of cash or stock

The method above is neat in that it 'self recovers'; if you don't collect capital for a while it will adjust correctly when restarted. However this does mean that if you withdraw cash or securities from your brokerage account, it will look like you've made a loss and your capital will reduce. The reverse will happen if you make a deposit. This may not bother you (you actually want this to happen and aren't using the account level p&l figures), but if it does you can run the [interactive tool](#interactively-modify-capital-values) and select 'Adjust account value for withdrawal or deposit'. Make sure you are using the base currency of the account.

If you forget to do this, you should select 'Delete values of capital since time T' in the interactive tool. You can then delete the erroneous rows of capital, account for the withdrawal, and finally 'Update capital from IB account value' to make sure it has worked properly.

If you want the p&l to be correct, but do want your capital to reduce (increase), then you should use option 'Modify any/all values' after accounting for the withdrawal. Decrease (increase) the total capital figure accordingly. If you are using half compounding you also need to increase the maximium capital figure if it is lower than the new total capital figure.


### Change in capital methodology or capital base

In the [interactive tool](#interactively-modify-capital-values), option 'Modify any/all values'. Note that it's possible to change the method for capital calculation, the maximum capital or anything you wish even after you have started trading, and there may be good reasons for doing so. It's recommended that you don't delete previous capital values if you want to be able to consistently calculate your 'account level' percentage profit and loss; but the option is there to do so ('Delete everything and start again' in the interactive tool).

- Changing the capital method: this is fine, and indeed I've done it myself. The system doesn't record historic values of this parameter but you can usually infer it from the behaviour of historic capital values.
- Changing the total capital: this is also fine and can often make sense. For example you might want to start a new system off with a limited amount of capital and gradually increase it, even if the full amount is already in the brokerage account. Or temporarily reduce it because you're a scaredy cat. If using half compounding then think about your maximum capital.
- Changing your maximum capital (only affects half compounding): this might make sense but think about behaviour. If you reduce it below current total capital, then total capital will immediately reduce to that level. If you increase it above current total capital, then you will be able to accumulate profits until you reach the new maximum.

You can also change other values in the interactive tool, but be careful and make sure you know what you are doing and why!


## Strategies

Each strategy is defined in the config parameter `strategy_list`, found either in the defaults.yaml file or overriden in private yaml configuration. The following shows the parameters for an example strategy, named (appropriately enough) `example`.

```
strategy_list:
  example:
    overnight_launcher:
      function: sysproduction.system_launchers.run_system_classic.run_system_classic
      backtest_config_filename: systems.provided.futures_chapter15.futures_config.yaml
```
### Strategy capital

Strategy capital is allocated from [total capital](#capital). This is done by the scripted function, [update strategy capital](#allocate-capital-to-strategies). It is controlled by the configuration element below (in the defaults.yaml file, or overriden in private_config.yaml).

```
strategy_capital_allocation:
  function: sysproduction.strategy_code.strategy_allocation.weighted_strategy_allocation
  strategy_weights:
    example: 100.0
```

The allocation calls the function specified, with any other parameters passed as keywords. This default function is very simple, and just carves out the capital proportionally across all the strategies listed in `strategy_weights`. If you wish to use it you will just need to change the `strategy_weights` dict element. Alternatively, you can write your own capital allocation function.


#### Risk target

The actual risk a strategy will take depends on both it's capital and it's risk target. The risk target is set in the configuration option, `percentage_vol_target`, in the backtest configuration .yaml file for the relevant strategy (if not supplied, the defaults.yaml value is used; this is *not* overriden by private_config.yaml). Risk targets can be different across strategies.

#### Changing risk targets and/or capital

Strategy capital can be changed at any time, and indeed will usually change daily since it depends on the total capital allocated. You can also change the weight a strategy across the total strategy. A history of a strategies capital is stored, so any changes can be seen historically. Weights are not stored, but can be backed out from the total capital and strategy capital.

We do not store a history of the risk target of a strategy, so if you change the risk target this will make it difficult to compare across time. I do not advise doing this.


### Launcher functions

Launch functions run overnight backtests for each of the strategies you are running (see [here](#run-updated-backtest-systems-for-one-or-more-strateges) for more details.)

The following shows the launch function parameters for an example strategy, named (appropriately enough) `example`.

```
strategy_list:
  example:
    overnight_launcher:
      function: sysproduction.system_launchers.run_system_classic.run_system_classic
      backtest_config_filename: systems.provided.futures_chapter15.futures_config.yaml
```

The configuration for the overnight launcher includes the launcher function; the other configuration values are passed as keyword arguments to the launcher function.
Launcher functions must include the strategy name and a [data 'blob'](#data-blobs-and-the-classes-that-feed-on-them) as their first two arguments.

A launcher usually does the following:

- get the amount of capital currently in your trading account. See [strategy-capita](#strategy-capital).
- run a backtest using that amount of capital
- get the position buffer limits, and save these down (for the classic system, other systems may save different values down)
- store the backtest state (pickled cache) in the directory specified by the parameter csv_backup_directory (set in your private config file, or the system defaults file), subdirectory strategy name, filename date and time generated. It also copies the config file used to generate this backtest with a similar naming pattern.

As an example here is the provided 'classic' launcher function:

```python
def run_system_classic(strategy_name, data,
               backtest_config_filename="systems.provided.futures_chapter15.futures_config.yaml",
               ):


        capital_value = get_capital(data, strategy_name)

        system = production_classic_futures_system(backtest_config_filename,
                                            log=data.log, notional_trading_capital=capital_value,
                                           )

        updated_buffered_positions(data, strategy_name, system)

        store_backtest_state(data, system, strategy_name=strategy_name,
                             backtest_config_filename=backtest_config_filename)
        return success
```

# Recovering from a crash - what you can save and how, and what you can't


# Production system things of interest

Here I describe parts of the production system that are a bit fiddly and weird, as well as some conventions.

## Data blobs and the classes that feed on them

TO DO



## 'Run' process

## Reporting and diagnostics

TO DO
