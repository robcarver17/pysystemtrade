
This document is specifically about *futures data*. It is broken into three sections. The first, [A futures data workflow](#futures_data_workflow), gives an overview of how data is typically processed. It describes how you would get some data from quandl, store it, and create back-adjusted prices. The next section [Storing futures data](#storing_futures_data) then describes in detail each of the components of the API for storing futures data. In the third and final section [simData objects](#simData_objects) you will see how we hook together individual data components to create a `simData` object that is used by the main simulation system.

Although this document is about futures data, parts two and three are necessary reading if you are trying to create or modify any data objects.


Table of Contents
=================

TBC

<a name="futures_data_workflow">
</a>
# A futures data workflow

## Setting up some instrument configuration

The first step is to store some instrument configuration information. In principal this can be done in any way, but we are going to *read* from .csv files, and *write* to a [Mongo Database](#mongoDB). There are two kinds of configuration; instrument configuration and roll configuration. Instrument configuration consists of static information that enables us to map from the instrument code like EDOLLAR.

The relevant file to setup *information configuration* is in sysinit - the part of pysystemtrade used to initialise a new system. Here is the relevant module [instruments_csv_mongo](/sysinit/futures/instruments_csv_mongo.py). Notice it uses two types of data objects: the object we write to [mongoFuturesInstrumentData](#mongoFuturesInstrumentData) and the object we read from [initCsvFuturesInstrumentData](#initCsvFuturesInstrumentData). These objects both inherit from the more generic futuresInstrumentData, and are specialist versions of that . You'll see this pattern again and again, but I won't describe 

Make sure you are running a [Mongo Database](#mongoDB) before running this.

The information is sucked out of [this file](/sysinit/futures/config/instrumentconfig.csv) and into the mongo database whose connections are defined [here](/sysdata/mongodb/mongo_connection.py). The file includes a number of futures contracts that I don't actually trade or get prices for. Any configuration information for these may not be accurate and you use it at your own risk.


## Roll parameter configuration

For *roll configuration* we need to initialise by running the code in this file [roll_parameters_csv_mongo.py](/sysinit/futures/roll_parameters_csv_mongo.py). Again it uses two types of data objects, again we read from [a csv file](/sysinit/futures/config/rollconfig.csv) with [initCsvFuturesRollData](#initCsvFuturesRollData), and write to a mongo db [mongoRollParametersData](#mongoRollParametersData). Again you need to make sure you are running a [Mongo Database](#mongoDB) before running this.

It's worth explaining the available options for roll configuration. First of all we have two *roll cycles*: 'priced' and 'hold'. Roll cycles use the usual definition for futures months (January is F, February G, March H, and the rest of the year is JKMNQUVX, with December Z). The 'priced' contracts are those that we can get prices for, whereas the 'hold' cycle contracts are those we actually hold. We may hold all the priced contracts (like for equities), or only only some because of liquidity issues (eg Gold), or to keep a consistent seasonal position (i.e. CRUDEW is Winter Crude, so we only hold December).

'RollOffsetDays': This indicates how many calendar days before a contract expires that we'd normally like to roll it. These vary from zero (Korean bonds KR3 and KR10 which you can't roll until the expiry date) up to -1100 (Eurodollar where I like to stay several years out on the curve).

'CarryOffset': Whether we take carry from an earlier dated contract (-1, which is preferable) or a later dated contract (+1, which isn't ideal but if we hold the front contract we have no choice). This calculation is done based on the *priced* roll cycle, so for example for winter crude where the *hold* roll cycle is just 'Z' (we hold December), and the carry offset is -1 we take the previous month in the *priced* roll cycle (which is a full year FGHJKMNQUVXZ) i.e. November (whose code is 'X').

'ExpiryOffset': How many days to shift the expiry date in a month, eg (the day of the month that a contract expires)-1. These values are just here so we can build roughly correct roll calendars (of which more later). In live trading you'd get the actual expiry date for each contract.

*FIXME: not all of these parameters are completed accurately (especially ExpiryOffset and RollOffsetDays): I intend to update it properly for everything I actually trade.*


## Getting historical data for individual futures contracts

Now let's turn our attention to getting prices for individual futures contracts. We could get this from anywhere, but we'll use [Quandl](wwww.quandl.com). Obviously you will need to [get the python quandl library](#getQuandlPythonAPI), and you may want to [set a Quandl key](#setQuandlKey). 

We can also store it, in principal, anywhere but I will be using the open source [Arctic library](https://github.com/manahl/arctic) which was released by my former employers [AHL](ahl.com). This sits on top of Mongo DB (so we don't need yet another database) but provides straightforward and fast storage of pandas DataFrames.

We'll be using [this code](/sysinit/futures/historical_contract_prices_quandl_mongo.py). Unlike the first two initialisation scripts this is set up to run for a single market. 

By the way I can't just pull down this data myself and put it on github to save you time. Storing large amounts of data in github isn't a good idea regardless of whether it is in .csv or Mongo files, and there would also be licensing issues with basically just copying and pasting raw data from Quandl. You have to get, and then store, this stuff yourself. And of course at some point in a live system you would be updating this yourself.

This uses quite a few data objects:

- Price data for individual futures contracts: quandlFuturesContractPriceData and arcticFuturesContractPriceData
- Configuration needed when dealing with Quandl: quandlFuturesConfiguration - this reads [this .csv](/sysdata/quandl/QuandlFuturesConfig.csv) and defines the code and market; but also the first contract in Quandl's database (*FIXME: these values aren't defined except for Eurodollar*)
- Instrument data (that we prepared earlier): [mongoFuturesInstrumentData](#mongoFuturesInstrumentData)
- Roll parameters data (that we prepared earlier): [mongoRollParametersData](#mongoRollParametersData)
- Two generic data objects (not for a specific source):  [listOfFuturesContracts](#listOfFuturesContracts), [futuresInstrument](#futuresInstrument)
 
The script does two things:

1. Generate a list of futures contracts, starting with the first contract defined in [this .csv](/sysdata/quandl/QuandlFuturesConfig.csv) and following the price cycle. The last contract in that series is the contract we'll currently hold, given the 'ExpiryOffset' parameter.
2. For each contract, get the prices from Quandl and write them into Mongo DB.


## Roll calendars

### Roll calendars from arctice prices

### Roll calendars from existing 'multiple prices' .csv files


## Creating multiple prices


## Creating back adjusted prices

### From arctic prices

### From existing 'multiple prices' .csv files



<a name="storing_futures_data"></a>

# Storing futures data

## General notes

## Types of data: generic objects

<a name="futuresInstrument"></a>
### Instruments: futuresInstrument

### Futures contracts: 

<a name="listOfFuturesContracts"></a>
### Lists of futures contracts: listOfFuturesContracts


## Data sources

### Static csv files used for initialisation

<a name="initCsvFuturesInstrumentData"></a>
#### initCsvFuturesInstrumentData()

<a name="initCsvFuturesRollData"></a>
#### initCsvFuturesRollData()

### Csv files

<a name="mongoDB"></a>
### mongo DB

https://github.com/robcarver17/pysystemtrade/blob/master/sysdata/mongodb/mongo_connection.py

<a name="mongoFuturesInstrumentData"></a>
#### mongoFuturesInstrumentData()


<a name="mongoRollParametersData"></a>
### mongoRollParametersData()

### Quandl

<a name="getQuandlPythonAPI"></a>
#### Getting the Quandl python API

At the time of writing you get this from here.

<a name="setQuandlKey"></a>
#### Setting a Quandl API key

In [this file](/sysdata/quandl/quandl_futures.py), add this command after the import statements:

```python
quandl.ApiConfig.api_key = 'your_key_goes_here'
```

<a name="quandlFuturesContractPriceData"></a>
<a name="quandlFuturesConfiguration"></a>

#### quandlFuturesContractPriceData() and quandlFuturesConfiguration()


### Arctic 

<a name="arcticFuturesContractPriceData"></a>
#### arcticFuturesContractPriceData()



<a name="simData_objects">
</a>
# simData objects

