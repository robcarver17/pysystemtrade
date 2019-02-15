This document is specifically about using pysystemtrade for *live production trading*. 

*This is NOT a complete document, and is currently a work in progress. It is not possible to run a full production system with pysystemtrade at present*

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


# Overview of a production system

Here are the steps you need to follow to set up a production system. I assume you already have a backtested system in pysystemtrade, with appropriate python libraries etc.

1. Consider your implementation tactics
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

## Automatation options

You don't have to run pysystemtrade .

## Containers and clouds

## Backup machine

# Private code and configuration management

## Multiple systems

## Managing your private directory

# Finalise your backtest configuration


# Linking to a broker

This section describes a typical workflow for setting up futures data from scratch:

# Other data sources

This section describes a typical workflow for setting up futures data from scratch:

# Data storage

Various kinds of data files are used by the pysystemtrade production system. Broadly speaking they fall int

## Data backup

Assuming that you are using the default mongob for storing, then I recommend using [mongodump](https://docs.mongodb.com/manual/reference/program/mongodump/#bin.mongodump) on a daily basis to back up your files. Other more complicated alternatives are available (see the [official mongodb man page](https://docs.mongodb.com/manual/core/backups/)). 

To avoid conflicts you should schedule your backup during the 'deadtime' for your system (see scheduling).

# Reporting, logging and diagnostics

This section describes a typical workflow for setting up futures data from scratch:


# Scripts

## Spot FX prices


# Scheduling

## Scheduling systems

You need some sort of scheduling system to kick off the various processes.

### Linux cron

Because I use cron myself, there are is a cron tab included in pysystemtrade. To use it type:


### Windows task scheduler

I have not used this product, but in theory it should do the job.

### Python

You can use python itself as a scheduler, using something like [this](https://github.com/dbader/schedule), which gives you the advantage of being platform independent. However you will still need to ensure there is a python instance running all the time. You also need to be careful about .

### Manual system

It's possible to run pysystemtrade without any scheduling, by manually starting the neccessary processes as required. This option might make especial sense for traders who are not running a fully automated system (see REF). I would advise writing scripts to automate this and reduce the typing involved.

## Issues to consider when constructing the schedule


## A suggested schedule in pseudocode


# Monitoring your system

## System recovery

The worse can happen; you might end up with a dead

