This document is specifically about using pysystemtrade for *live production trading*. 

*This is NOT a complete document, and is currently a work in progress - any in many cases a series of thoughts about design intent rather than a fully featured specificiation. It is not possible to run a full production system with pysystemtrade at present*

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
        - ECHO_PATH=/home/user/echos
    - Create the following directories (again use other directories, but you must modify the .profile above and crontab below)
        - '/data/mongodb/'
        - '/echos/'
        - '/pysystemtrade/
    - Install the pysystemtrade package, and install or update, any dependencies in directory $PYSYS_CODE (it's possible to put it elsewhere, but you will need to modify the environment variables listed above)
    - [Set up interactive brokers](/docs/IB.md), download and install their python code, and get a gateway running.
    - [Install mongodb](https://docs.mongodb.com/manual/administration/install-on-linux/)
    - create a file 'private_config.yaml' in the private directory of [pysystemtrade](#/private)
    - [check a mongodb server is running with the right data directory](/docs/futures.md#mongo-db) command line: `mongod --dbpath $MONGO_DATA`
    - launch an IB gateway (this could be done automatically depending on your security setup)
- FX data:
    - [Initialise the spot FX data in MongoDB from .csv files](/sysinit/futures/repocsv_spotfx_prices.py) (this will be out of date, but you will update it in a moment)
    - Check that you have got spot FX data present: command line:`. /pysystemtrade/sysproduction/linux/scripts/read_fx_prices`
    - Update the FX price data in MongoDB using interactive brokers: command line:`. /home/your_user_name/workspace3/pysystemtrade/sysproduction/linux/scripts/update_fx_prices`
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
- Scheduling:
- Initialise the [supplied crontab](/sysproduction/linux/crontab). Note if you have put your code or echos somewhere else you will need to modify the directory references at the top of the crontab.
- All scripts executable by the crontab need to be executable, so do the following: `cd $SCRIPT_PATH` ; `sudo chmod +x update*` ;`sudo chmod +x truncate*` FIX ME ADD FURTHER FILES AS REQUIRED

Before trading, and each time you restart the machine you should:

- [check a mongodb server is running with the right data directory](/docs/futures.md#mongo-db) command line: `mongod --dbpath $MONGO_DATA`
- launch an IB gateway (this could [be done automatically](https://github.com/ib-controller/ib-controller) depending on your security setup)


# Overview of a production system

Here are the steps you need to follow to set up a production system. I assume you already have a backtested system in pysystemtrade, with appropriate python libraries etc.

1. Consider your implementation options
2. Ensure you have a private area for your system code and configuration
3. Finalise and store your backtested system configuration
4. If you want to automatically execute, or get data from a broker, then set up a broker 
5. Set up any other data sources you need.
6. Set up a database for storage, including a backup
7. Have a strategy for reporting, diagnostics, and logs
8. Write some scripts to kick off processes to: get data, get accounting information, calculate optimal positions, execute trades, run reports.
9. Schedule your scripts to run regularly
10. Regularly monitor your system, and deal with any problems


# Implementation options

Standard implementation for pysystemtrade is a fully automated system running on a single local machine. In this section I briefly describe some alternatives you may wish to consider.

My own implementation runs on a Linux machine, and some of the implementation details in this document are Linux specific. Windows and Mac users are welcome to contribute with respect to any differences.

## Automatation options

You can run pysystemtrade as a fully automated system, which does everything from getting prices through to executing orders. But other patterns make sense. In particular you may wish to do your trading manually, after pulling in prices and generating optimal positions manually. It will also possible to trade manually, but allow pysystemtrade to pick up your fills from the broker rather than entering them manually.

## Machines, containers and clouds

Pysystemtrade can be run locally in the normal way, on a single machine. But you may also want to consider containerisation (see [my blog post](https://qoppac.blogspot.com/2017/01/playing-with-docker-some-initial.html)), or even implementing on AWS or another cloud solution. You could also spread your implemetation across several local machines.

If spreading your implementation across several machines bear in mind:

- Interactive brokers
   - interactive brokers Gateway will need to have the ip address of all relevant machines that connect to it in the whitelist
   - you will need to modify the `private_config.yaml` system configuration file so it connects to a different IP address `ib_ipaddress: '192.168.0.10'`
- Mongodb
   - Add an ip address the `bind_ip` line in the `/etc/mongod.conf` file to allow connections from other machines `eg bind_ip=localhost, 192.168.0.10`
   - you will need to modify the `private_config.yaml` system configuration file so it connects to a different IP address `mongo_host: 192.168.0.13`
   - you may want to enforce [further security protocol](https://docs.mongodb.com/manual/administration/security-checklist/)

## Backup machine

If you are running your implementation locally, or on a remote server that is not a cloud, then you should seriously consider a backup machine. The backup machine should have an up to date environment containing all the relevant applications, code and libaries, and on a regular basis you should update the local data stored on that machine (see INSERT BACKUP LINK). The backup machine doesn't need to be turned on at all times, unless you are trading in such a way that a one hour period without trading would be critical (in my experience, one hour is the maximum time to get a backup machine on line assuming the code is up to date, and the data is less than 24 hours stale). I also encourage you to perform a scheduled 'failover' on regular basis: stop the live machine running (best to do this at a weekend), copy across any data to the backup machine, start up the backup machine. The live machine then becomes the backup.

## Multiple systems

You may want to run multiple trading systems. Common use cases are:

- You want different systems for different asset classes
- You want different systems for different time frames (eg intra day and slower trading). This is a specific use case with it's own problems, namely executing the aggregated orders from both systems, which I'll be specifically considering in future versions of pysystemtrade.
- You want to run the same system, but in different trading accounts
- You want a paper trading and live trading system

To handle this I suggest having multiple copies of the pysystemtrade environment. You will have a single crontab, but you will need multiple script, echos (AND FIX ME REPORTS?) directories. You will need to change the [private config file](private.private_config.yaml) so it points to different `mongo_db` database names. If you don't want multiple copies of certain data (eg prices) then you should hardcode the `database_name` in the relevant files whenever a connection is made eg `mongo_db = mongoDb(database_name='whatever')`. See [storing futures and spot FX data](/docs/futures.md#mongo-db) for more detail. Finally you should set the field `ib_idoffset` in the [private config file](private.private_config.yaml) so that there is no chance of duplicate clientid connections; setting one system to have an id offset of 1, the next offset 1000, and so on should be sufficient.

# Code and configuration management

Your trading strategy will consist of pysystemtrade, plus some specific configuration files, plus possibly some bespoke code. You can eithier implement this as:

- seperate environment, pulling in pysystemtrade as a 'yet another library'
- everything in pysystemtrade, with all specific code and configuration in the 'private' directory that is excluded from git uploads.

Personally I prefer the latter as it makes a neat self contained unit, but this is up to you.

### Managing your seperate directories of code and configuration

I strongly recommend that you use a code repo system or similar to manage your non pysystemtrade code and configuration. Since code and configuration will mostly be in text (or text like) yaml files a code repo system like git will work just fine. I do not recommend storing configuration in database files that will need to be backed up seperately, because this makes it more complex to store old configuration data that can be archived and retrieved if required. 

### Managing your private directory

Since the private directory is excluded from the git system (since you don't want it appearing on github!), you need to ensure it is managed seperately. I use a script which I run in lieu of a normal git add/ commit / push cycle:

```
# pass commit quote as an argument
# For example:
# . commit "this is a commit description string"
#
# copy the contents of the private directory to another, git controlled, directory
#
cp -R ~/pysystemtrade/private/ ~/private/
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
cp -R ~/private/ ~/pysystemtrade/
# git pull from main pysystemtrade github repo
cd ~/pysystemtrade/
git pull
```

I use a local git repo for my private directory. Github are now offering free private repos, so that is another option.


# Finalise your backtest configuration

You can just re-run a daily backtest to generate your positions. This will probably mean that you end up refitting parameters like instrument weights and forecast scalars. This is pointless, a waste of time, and potentially dangerous. Instead I'd suggest using fixed values for all fitted parameters in a live trading system.

The following convenience function *FIX ME NEED TO WRITE THIS* will take your backtested system, and create a new configuration object which includes fixed values for all estimated parameters (and will turn off all optimisation flags in the config). This object can then be written to YAML.

# Linking to a broker

You are probably going to want to link your system to a broker, to do one or more of the following things:

- get prices 
- get account value and profitability
- do trades
- get trade fills

... although one or more of these can also be done manually.

You should now read [connecting pysystemtrade to interactive brokers](/docs/IB.md). 


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

The default option is to store these all into a mongodb database, except for configuration files which are stored as .yaml files.

## Data backup

Assuming that you are using the default mongob for storing, then I recommend using [mongodump](https://docs.mongodb.com/manual/reference/program/mongodump/#bin.mongodump) on a daily basis to back up your files. Other more complicated alternatives are available (see the [official mongodb man page](https://docs.mongodb.com/manual/core/backups/)). 

Linux:
```
# dumps everything into dump directory
# make sure a mongo-db instance is running with correct directory, but ideally without any load; command line: `mongod --dbpath $MONGO_DATA`
mongodump

# copy dump directory to another machine or drive, here we assume there is a shared network drive mounted on all local machine
cp -rf dump /media/shared-drive/mongo_backup/

# To restore:
# FIX ME DOES THIS OVERWRITE???
cp -rf /media/shared-drive/mongo_backup/dump/ ~

# Now make sure a mongo-db instance is running with correct directory
mongorestore 
```

To avoid conflicts you should schedule your backup during the 'deadtime' for your system (see scheduling FIX ME LINK).

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

Over time echo files can get... large. To avoid this a regularly scheduled crontab script [FIX ME LINK AND ADD TO CRON] chops them down to the last 20,000 lines.

## Logging 

Logging in pysystemtrade is done via loggers. See the [userguide for more detail](/docs/userguide.md#logging).

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

    # note use of log.setup when passing log to other components
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

- type: the argument passed when the logger is setup. Should be the name of the top level calling function.
- stage: Used by stages in System objects
- component: other parts of the top level function that have their own loggers
- currency_code: Currency code (used for fx)
- instrument_code: Self explanatory

FIX ME TO DO: CRITICAL LOGS SHOULD EMAIL THE USER

### Getting log data back

Python:
```python
from syslogdiag.log import accessLogFromMongodb
```
# can optionally pass mongodb connection attributes here
mlog = accessLogFromMongodb()
# Return a list of strings per log line
mlog.get_log_items(dict(type="top-level-function")) # any attribute directory here is fine as a filter, defaults to last days results
# Printout log entries
mlog.print_log_items(dict(type="top-level-function"), lookback_days=7) # get last weeks worth
# Return a list of logEntry objects, useful for dissecting
mlog.get_log_items_as_entries(dict(type="top-level-function"))
```


### Cleaning old logs


Python:
```python
from syslogdiag.log import accessLogFromMongodb
from sysdata.mongodb.mongo_connection import mongoDb

# can optionally pass mongodb connection attributes here
mongo_db=mongoDb()
mlog = accessLogFromMongodb(mongo_db=mongo_db)

mlog.delete_log_items_from_before_n_days(days=365) # this is also the default
```

Linux script: (defaults to last 365 days and default database
```
. $SCRIPT_PATH/truncate_log_files
```

FIX ME THIS SHOULD BE DONE EVERY DAY ONCE WE HAVE ENOUGH LOGS ADD TO CRONTAB

## Reporting


# Scripts

Scripts are used to run python code which:

- runs different parts of the trading system, such as:
   - get price data
   - get FX data
   - calculate positions
   - execute trades
   - get accounting data
- runs reports, eithier regular or ad-hoc

Script are then called by schedulers (FIX ME LINK), or on an ad-hoc basis from the command line.

## Production system components

### Get spot FX data from interactive brokers, write to MongoDB


Python:
```python
from sysproduction.updateFxPrices import update_fx_prices

update_fx_prices()
```

Linux script:
```
. $SCRIPT_PATH/update_fx_prices
```


## Ad-hoc diagnostics

### Recent FX prices

Python:
```python
from sysproduction.readFxPrices import read_fx_prices
read_fx_prices("GBPUSD", tail_size=20) # print last 20 rows for cable
```

Linux command line: (arguments are asked for after script is run)
```
cd $SCRIPT_PATH
. read_fx_prices
```

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

- Midnight: Launch processes for monitoring account value, executing trades, and gathering intraday prices
- 6am: Get daily spot FX prices
- 6am: Run some lightweight morning reports
- 8pm: Stop processes for monitoring account value, executing trades, and gathering intraday prices
- 8pm: Clear client id tracker used by IB to avoid conflicts
- 8:30pm: Get daily 'closing' prices (some of these may not be technically closes if markets have not yet closed)
- 9:00pm: Run daily reports, and any computationally intensive processes (like running a backtest based on new prices)
- 11pm: Run backups
- 11pm: Truncate echo files, discard log file entries more than one year old, 

There will be flexibility in this schedule depending on how long different processes take. Notice that I don't shut down and then launch a new interactive brokers gateway daily. Some people may prefer to do this, but I am using an authentication protocol which requires manual intervention. [This product](https://github.com/ib-controller/ib-controller/) is popular for automating the lauch of the IB gateway.

## Choice of scheduling systems

You need some sort of scheduling system to kick off the various processes.

### Linux cron

Because I use cron myself, there are is a [cron tab included in pysystemtrade](https://github.com/robcarver17/pysystemtrade/blob/master/sysproduction/linux/crontab). 

### Windows task scheduler

I have not used this product (I don't use Windows or Mac products for ideological reasons, also they're rubbish and overpriced respectively), but in theory it should do the job.

### Python

You can use python itself as a scheduler, using something like [this](https://github.com/dbader/schedule), which gives you the advantage of being platform independent. However you will still need to ensure there is a python instance running all the time. You also need to be careful about whether you are spawning new threads or new processes, since only one connection to IB Gateway or TWS can be launched within a single process.

### Manual system

It's possible to run pysystemtrade without any scheduling, by manually starting the neccessary processes as required. This option might make sense for traders who are not running a fully automated system (see FIX ME REF). 


