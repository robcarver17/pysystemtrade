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

- Install [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git), install or update [python3](https://docs.python-guide.org/starting/install3/linux/). You may also find a simple text editor (like emacs) is useful for fine tuning, and if you are using a headless server then [x11vnc](http://www.karlrunge.com/x11vnc/) is helpful.
- Install the pysystemtrade package, and install or update, any dependencies
- [Set up interactive brokers](/docs/IB.md), download and install their python code, and get a gateway running.
- [Install mongodb](https://docs.mongodb.com/manual/administration/install-on-linux/) 
- Create the following directories: (and any subdirectories)
   - /data/mongodb/
- create a file 'private_config.yaml' in the private directory of [pysystemtrade](#/private)
- [Initialise the spot FX data from .csv files](/sysinit/futures/repocsv_spotfx_prices.py) (this will be out of date, but you will update it in a moment)
- Initialise the supplied crontab

Before trading, and each time you restart the machine you should:

- [check a mongodb server is running with the right data directory](/docs/futures.md#mongo-db) mongod --dbpath ~/data/mongodb/
- launch an IB gateway
- 

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


# Implementation details

Standard implementation for pysystemtrade is a fully automated system running on a single local machine. In this section I briefly describe some alternatives you may wish to consider.

My own implementation runs on a Linux machine, and some of the implementation details in this document are Linux specific. Windows and Mac users are welcome to contribute with respect to any differences.

## Automatation options

You can run pysystemtrade as a fully automated system, which does everything from getting prices through to executing orders. But other patterns make sense. In particular you may wish to do your trading manually, after pulling in prices and generating optimal positions manually. It will also possible to trade manually, but allow pysystemtrade to pick up your fills from the broker rather than entering them manually.

## Machines, containers and clouds

Pysystemtrade can be run locally in the normal way, on a single machine. But you may also want to consider containerisation (see [my blog post](https://qoppac.blogspot.com/2017/01/playing-with-docker-some-initial.html)), or even implementing on AWS or another cloud solution. You could also spread your implemetation across several local machines.

If spreading your implementation across several machines bear in mind:

- Interactive brokers
   - interactive brokers Gateway will need to have the ip address of all relevant machines in the whitelist
   - you will need to modify the `private_config.yaml` system configuration file so it connects to a different IP address `ib_ipaddress: '192.168.0.10'`
- Mongodb
   - Add an ip address the `bind_ip` line in the `/etc/mongod.conf` file to allow connections from other machines `eg bind_ip=localhost, 192.168.0.10`
   - you will need to modify the `private_config.yaml` system configuration file so it connects to a different IP address `mongo_host: 192.168.0.13`
   - you may want to enforce [further security protocol](https://docs.mongodb.com/manual/administration/security-checklist/)

## Backup machine

If you are running your implementation locally, or on a remote server that is not a cloud, then you should seriously consider a backup machine. The backup machine should have an up to date environment containing all the relevant applications, code and libaries, and on a regular basis you should update the local data stored on that machine (see INSERT BACKUP LINK). The backup machine doesn't need to be turned on at all times, unless you are trading in such a way that a one hour period without trading would be critical (in my experience, one hour is the maximum time to get a backup machine on line assuming the code is up to date, and the data is less than 24 hours stale). I also encourage you to perform a scheduled 'failover' on regular basis: stop the live machine running, copy across any data to the backup machine, start up the backup machine. The live machine then becomes the backup.

# Code and configuration management


## Multiple systems

You may want to run multiple trading systems. Common use cases are:

- You want different systems for different asset classes
- You want different systems for different time frames (eg intra day and slower trading). This is a specific use case with it's own problems, namely executing the aggregated orders from both systems, which I'll be specifically considering in future versions of pysystemtrade.
- You want to run the same system, but in different trading accounts
- You want a paper trading and live trading system

(There may be problems with trying to connect to your broker API multiple times in some of these use cases, again I will consider solutions to this)

Broadly speaking there are two ways to handle this:

- common code, with some kind of parameter switching and database field malarky so it's clear which system you are interacting with.
- seperated environments, each containing a unique version of code and parameters for each system.

For various reasons, and based on my own experience, the latter is preferable. A parallel decision is with regard to data. If you have a single environment, then you also have a single data storage point. But if not you can do one of these:

- store general data (eg prices) in files that are accessible by all your systems, and store specific data for each system in it's own environment. 
- keep multiple copies of general data with specific data for each system
- keep all data in a single place, with specific tables or records for each system's private data. 

For a flat file solution (eg sqllite or .csv) it's possible to have some tables stored in public and others in specific directories. But it is not okay for a database server (eg mongodb). In the latter case we need to be able to access both generic and specific tables accessible by a single database server (it's tricky to run multiple database servers, and it imposes an uneccessary load on the system). To solve this I propose using the third solution, and incorporating database field flags in the configuration for each environment, to allow specific tables in the mongodb 'cloud' to be accessed for different systems (I prefer seperate tables for each seperate system, rather than flagged records in a single table, although the concept of 'table' is a bit outdated for a nosql database like mongodb, strictly speaking they are 'collections').


## Private directory or seperate library

Your trading strategy will consist of pysystemtrade, plus some specific configuration files, plus possibly some bespoke code. You can eithier implement this as:

- seperate environment, pulling in pysystemtrade as a 'yet another library'
- everything in pysystemtrade, with all specific code and configuration in the 'private' directory that is excluded from git uploads.

Personally I prefer the latter as it makes a neat self contained unit, but this is up to you.

### Managing your seperate directories of code and configuration

I strongly recommend that you use a code repo system or similar to manage your non pysystemtrade code and configuration. Since code and configuration will mostly be in text (or text like) yaml files a code repo system like git will work just fine. I do not recommend storing configuration in database files that will need to be backed up seperately, because this makes it more complex to store old configuration data that can be archived and retrieved if required. 

### Managing your private directory

Since the private directory is excluded from the git system (since you don't want it appearing on github!), you need to ensure it is managed seperately. I use a script which I run in lieu of a normal git add/ commit / push cycle:

- copy the contents of the private directory to another, git controlled, directory
- git add/commit/push cycle on the main pysystemtrade directory
- git add/commit/push cycle on the copied private directory

A second script is run instead of a git pull:

- git pull within git controlled private directory copy
- copy the updated contents of the private directory to pysystemtrade private directory
- git pull from main pysystemtrade github repo

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

The default option is to store these all into a mongodb database. 

## Data backup

Assuming that you are using the default mongob for storing, then I recommend using [mongodump](https://docs.mongodb.com/manual/reference/program/mongodump/#bin.mongodump) on a daily basis to back up your files. Other more complicated alternatives are available (see the [official mongodb man page](https://docs.mongodb.com/manual/core/backups/)). 

To avoid conflicts you should schedule your backup during the 'deadtime' for your system (see scheduling).

# Reporting, logging and diagnostics

We need to know what our system is doing, especially if it is fully automated. Here are the methods by which this should be done:

- logging of stdout output from processes that are running
- storage of diagnostics in a database, tagged with keys to identify them 
- the option to run reports both scheduled and ad-hoc, which can optionally be automatically emailed


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
- 8:30pm: Get daily 'closing' prices (some of these may not be technically closes if markets have not yet closed)
- 9:00pm: Run daily reports, and any computationally intensive processes (like running a backtest based on new prices)
- 11pm: Run backups

There will be flexibility in this schedule depending on how long different processes take. Notice that I don't launch a new interactive brokers gateway daily. Some people may prefer to do this, but I am using an authentication protocol which requires manual intervention. [This product](https://github.com/ib-controller/ib-controller/) is popular for automating the lauch of the IB gateway.

## Choice of scheduling systems

You need some sort of scheduling system to kick off the various processes.

### Linux cron

Because I use cron myself, there are is a cron tab included in pysystemtrade. To use it type: FIXME


### Windows task scheduler

I have not used this product (I don't use Windows or Mac products for ideological reasons, also they're rubbish and overpriced respectively), but in theory it should do the job.

### Python

You can use python itself as a scheduler, using something like [this](https://github.com/dbader/schedule), which gives you the advantage of being platform independent. However you will still need to ensure there is a python instance running all the time. You also need to be careful about whether you are spawning new threads or new processes, since only one connection to IB Gateway or TWS can be launched within a single process.

### Manual system

It's possible to run pysystemtrade without any scheduling, by manually starting the neccessary processes as required. This option might make sense for traders who are not running a fully automated system (see FIX ME REF). I would advise writing scripts (FIX ME REF) to automate this and reduce the typing involved.



