THIS DOCUMENT IS NOT FINISHED AND CONTAINS MANY GAPS AND 'TO DO'!

This document is specifically about *futures data*. It is broken into three sections. The first, [A futures data workflow](#futures_data_workflow), gives an overview of how data is typically processed. It describes how you would get some data from quandl, store it, and create back-adjusted prices. The next section [Storing futures data](#storing_futures_data) then describes in detail each of the components of the API for storing futures data. In the third and final section [simData objects](#simData_objects) you will see how we hook together individual data components to create a `simData` object that is used by the main simulation system.

Although this document is about futures data, parts two and three are necessary reading if you are trying to create or modify any data objects.


Table of Contents
=================

TBC

<a name="futures_data_workflow"></a>
# A futures data workflow

This section describes a typical workflow for setting up futures data from scratch:

1. [Set up some static configuration information](#set_up_instrument_config) for instruments, and [roll parameters](#set_up_roll_parameter_config)
2. Get, and store, [some historical data](#get_historical_data)
3. Build, and store, [roll calendars](#roll_calendars)
4. Create and store ['multiple' price series](create_multiple_prices) containing the relevant contracts we need for any given time period
5. Create and store [back-adjusted prices](#back_adjusted_prices)

In future versions of pysystemtrade there will be code to keep your prices up to date.

<a name="set_up_instrument_config"></a>
## Setting up some instrument configuration

The first step is to store some instrument configuration information. In principal this can be done in any way, but we are going to *read* from .csv files, and *write* to a [Mongo Database](https://www.mongodb.com/). There are two kinds of configuration; instrument configuration and roll configuration. Instrument configuration consists of static information that enables us to map from the instrument code like EDOLLAR.

The relevant script to setup *information configuration* is in sysinit - the part of pysystemtrade used to initialise a new system. Here is the script you need to run [instruments_csv_mongo](/sysinit/futures/instruments_csv_mongo.py). Notice it uses two types of data objects: the object we write to [mongoFuturesInstrumentData](#mongoFuturesInstrumentData) and the object we read from [initCsvFuturesInstrumentData](#initCsvFuturesInstrumentData). These objects both inherit from the more generic futuresInstrumentData, and are specialist versions of that. You'll see this pattern again and again, and I describe it further in [part two of this document](#storing_futures_data). 

Make sure you are running a [Mongo Database](#mongoDB) before running this.

The information is sucked out of [this file](/sysinit/futures/config/instrumentconfig.csv) and into the mongo database whose connections are defined [here](/sysdata/mongodb/mongo_connection.py). The file includes a number of futures contracts that I don't actually trade or get prices for. Any configuration information for these may not be accurate and you use it at your own risk.

<a name="set_up_roll_parameter_config"></a>
## Roll parameter configuration

For *roll configuration* we need to initialise by running the code in this file [roll_parameters_csv_mongo.py](/sysinit/futures/roll_parameters_csv_mongo.py). Again it uses two types of data objects: we read from [a csv file](/sysinit/futures/config/rollconfig.csv) with [initCsvFuturesRollData](#initCsvFuturesRollData), and write to a mongo db [mongoRollParametersData](#mongoRollParametersData). Again you need to make sure you are running a [Mongo Database](#mongoDB) before executing this script.

It's worth explaining the available options for roll configuration. First of all we have two *roll cycles*: 'priced' and 'hold'. Roll cycles use the usual definition for futures months (January is F, February G, March H, and the rest of the year is JKMNQUVX, with December Z). The 'priced' contracts are those that we can get prices for, whereas the 'hold' cycle contracts are those we actually hold. We may hold all the priced contracts (like for equities), or only only some because of liquidity issues (eg Gold), or to keep a consistent seasonal position (i.e. CRUDEW is Winter Crude, so we only hold December).

'RollOffsetDays': This indicates how many calendar days before a contract expires that we'd normally like to roll it. These vary from zero (Korean bonds KR3 and KR10 which you can't roll until the expiry date) up to -1100 (Eurodollar where I like to stay several years out on the curve).

'CarryOffset': Whether we take carry from an earlier dated contract (-1, which is preferable) or a later dated contract (+1, which isn't ideal but if we hold the front contract we have no choice). This calculation is done based on the *priced* roll cycle, so for example for winter crude where the *hold* roll cycle is just 'Z' (we hold December), and the carry offset is -1 we take the previous month in the *priced* roll cycle (which is a full year FGHJKMNQUVXZ) i.e. November (whose code is 'X'). You read more in Appendix B of [my first book](www.systematicmoney.org/systematic-trading).

'ExpiryOffset': How many days to shift the expiry date in a month, eg (the day of the month that a contract expires)-1. These values are just here so we can build roughly correct roll calendars (of which more later). In live trading you'd get the actual expiry date for each contract.

*FIXME: not all of these parameters are completed accurately (especially ExpiryOffset and RollOffsetDays): I intend to update it properly for everything I actually trade.*

It might be helpful to read [my blog post](qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html) on rolling futures contracts (though bear in mind some of the details relate to my current trading system and do no reflect how pysystemtrade works). 

<a name="get_historical_data"></a>
## Getting historical data for individual futures contracts

Now let's turn our attention to getting prices for individual futures contracts. We could get this from anywhere, but we'll use [Quandl](wwww.quandl.com). Obviously you will need to [get the python quandl library](#getQuandlPythonAPI), and you may want to [set a Quandl key](#setQuandlKey). 

We can also store it, in principal, anywhere but I will be using the open source [Arctic library](https://github.com/manahl/arctic) which was released by my former employers [AHL](ahl.com). This sits on top of Mongo DB (so we don't need yet another database) but provides straightforward and fast storage of pandas DataFrames.

We'll be using [this code](/sysinit/futures/historical_contract_prices_quandl_mongo.py). Unlike the first two initialisation scripts this is set up to run for a single market. 

By the way I can't just pull down this data myself and put it on github to save you time. Storing large amounts of data in github isn't a good idea regardless of whether it is in .csv or Mongo files, and there would also be licensing issues with basically just copying and pasting raw data from Quandl. You have to get, and then store, this stuff yourself. And of course at some point in a live system you would be updating this yourself.

This uses quite a few data objects:

- Price data for individual futures contracts: [quandlFuturesContractPriceData](#quandlFuturesContractPriceData) and [arcticFuturesContractPriceData](#arcticFuturesContractPriceData)
- Configuration needed when dealing with Quandl: [quandlFuturesConfiguration](#quandlFuturesConfiguration) - this reads [this .csv](/sysdata/quandl/QuandlFuturesConfig.csv) and defines the code and market; but also the first contract in Quandl's database (*FIXME: these values aren't defined except for Eurodollar*)
- Instrument data (that we prepared earlier): [mongoFuturesInstrumentData](#mongoFuturesInstrumentData)
- Roll parameters data (that we prepared earlier): [mongoRollParametersData](#mongoRollParametersData)
- Two generic data objects (not for a specific source):  [listOfFuturesContracts](#listOfFuturesContracts), [futuresInstrument](#futuresInstrument)
 
The script does two things:

1. Generate a list of futures contracts, starting with the first contract defined in [this .csv](/sysdata/quandl/QuandlFuturesConfig.csv) and following the *price cycle*. The last contract in that series is the contract we'll currently hold, given the 'ExpiryOffset' parameter.
2. For each contract, get the prices from Quandl and write them into Mongo DB.

<a name="roll_calendars"></a>
## Roll calendars

We're now reading to set up a *roll calendar*. A roll calendar is the series of dates on which we roll from one futures contract to the next. It might be helpful to read [my blog post](qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html) on rolling futures contracts (though bear in mind some of the details relate to my current trading system and do no reflect how pysystemtrade works).

You can see a roll calendar for Eurodollar futures, [here](/data/futures/roll_calendars_csv/EDOLLAR.csv). It is just a pandas DataFrame. On each date we roll from the current_contract shown to the next_contract. We also see the current carry_contract; we use the differential between this and the current_contract to calculate forecasts for carry trading rules.

There are two ways to generate roll calendars:

1. Generate an [approximate calendar](#roll_calendars_from_approx) based on the 'ExpiryOffset' parameter, and then adjust it so it is viable given the futures prices we have from the [previous stage](#get_historical_data).
2. Infer from [existing 'multiple price' data](#roll_calendars_from_multiple). [Multiple price data](/data/futures/multiple_prices_csv) are data series that include the prices for three types of contract: the current, next, and carry contract (though of course there may be overlaps between these). 

<a name="roll_calendars_from_approx"></a>
### Approximate roll calendars, adjusted with actual prices

This is the method you'd use if you were starting from scratch, and you'd just got some prices for each futures contract. The relevant script is [here](#/sysinit/futures/rollcalendars_from_arcticprices_to_csv.py). Again it is only set up to run a single instrument at a time. 

In this script:

- We get prices for individual futures contract [from Arctic](#arcticFuturesContractPriceData) that we created in the [previous stage](#get_historical_data)
- We get roll parameters [from Mongo](#mongoRollParametersData), that [we made earlier](#set_up_roll_parameter_config) 
- We calculate the roll calendar `roll_calendar = rollCalendar.create_from_prices(dict_of_futures_contract_prices, roll_parameters)`
- We do some checks on the roll calendar, for monotonicity and validity (these checks will generate warnings if things go wrong)
- If we're happy with the roll calendar we [write](#csvRollCalendarData) our roll calendar into a csv file 

#### Calculate the roll calendar

The actual code that generates the roll calendar is [here](#/sysdata/futures/roll_calendars.py)

The relevant part is:

```python
approx_calendar = _generate_approximate_calendar(list_of_contract_dates, roll_parameters_object)
adjusted_calendar = _adjust_to_price_series(approx_calendar, dict_of_futures_contract_prices)
adjusted_calendar_with_carry = _add_carry_calendar(adjusted_calendar, roll_parameters_object)
```

So we first generate an approximate calendar, for when we'd ideally want to roll each of the contracts, based on our roll parameter 'RollOffsetDays'. However we may find that there weren't *matching* prices for a given roll date. A matching price is when we have prices for both the current and next contract on the relevant day. If we don't have that, then we can't calculate an adjusted price. The *adjustment* stage finds the closest date to the ideal date (looking both forwards and backwards in time). Finally we add the carry contract on to the roll calendar - this isn't used for back adjustment but we still need it for forecasting using the carry trading rule.


#### Checks

We then check that the roll calendar is monotonic and valid.

A *monotonic* roll calendar will have increasing datestamps in the index. It's possible, if your data is messy, to get non-monotonic calendars. Unfortunately there is no automatic way to fix this, you need to dive in and rebuild the  (this is why I store the calendars as .csv files to make such hacking easy).

A *valid* roll calendar will have current and next contract prices on the roll date. Since this is how we generate the roll calendars they should always pass this test (if we couldn't find a date when we have aligned prices then the calendar generation would have failed with an exception).

#### Write CSV prices

Roll calendars are stored in .csv format [here](/data/futures/roll_calendars_csv/EDOLLAR.csv). Of course you could put these into Mongo DB, or Arctic, but I like the ability to hack them if required.

<a name="roll_calendars_from_multiple"></a>
### Roll calendars from existing 'multiple prices' .csv files

In the next section we learn how to use roll calendars, and price data for individual contracts, to create DataFrames of *multiple prices*: the series of prices for the current, forward and carry contracts; as well as the identify of those contracts. But it's also possible to reverse this operation: work out roll calendars from multiple prices.

Of course you can only do this if you've already got these prices, which means you already need to have a roll calendar: a catch 22. Fortunately there are sets of multiple prices provided in pysystemtrade, and have been for some time, [here](#/data/futures/multiple_prices_csv). These are copies of the data in my legacy trading system, for which I had to generate historic roll calendars, and for the data since early 2014 include the actual dates when I rolled.

We run [this script](#/sysinit/futures/rollcalendars_from_providedcsv_prices.py) which by default will loop over all the instruments for which we have data in the multiple prices directory. 


<a name="create_multiple_prices"></a>
## Creating and storing multiple prices

FIXME: TO BE IMPLEMENTED

<a name="back_adjusted_prices"></a>
## Creating and storing back adjusted prices

FIXME: TO BE IMPLEMENTED

### From Arctic prices

FIXME: TO BE IMPLEMENTED

### From existing 'multiple prices' .csv files

FIXME: TO BE IMPLEMENTED

<a name="storing_futures_data"></a>

# Storing futures data

All data objects in pysystemtrade inherit from ...

Specific instances 

## Types of data: generic objects

<a name="futuresInstrument"></a>
### Instruments: futuresInstrument

### Contract dates

### Roll cycles

### Roll parameters

### Contract date with roll parameters

### Futures contracts: 

<a name="listOfFuturesContracts"></a>
### Lists of futures contracts: listOfFuturesContracts

### Prices for individual futures contracts

### Roll calendars

### Multiple prices

### Adjusted prices

### Spot FX data

## Data sources

### Static csv files used for initialisation

<a name="initCsvFuturesInstrumentData"></a>
#### initCsvFuturesInstrumentData()

<a name="initCsvFuturesRollData"></a>
#### initCsvFuturesRollData()

### Csv files


<a name="csvRollCalendarData"></a>
#### csvRollCalendarData()

#### csvFuturesMultiplePricesData()

#### csvFuturesAdjustedPricesData()

#### csvFxPricesData()



<a name="mongoDB"></a>
### mongo DB

https://github.com/robcarver17/pysystemtrade/blob/master/sysdata/mongodb/mongo_connection.py

<a name="mongoFuturesInstrumentData"></a>
#### mongoFuturesInstrumentData()


<a name="mongoRollParametersData"></a>
#### mongoRollParametersData()



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

#### arcticFuturesMultiplePricesData()
FIXME: TO BE IMPLEMENTED

#### arcticFuturesAdjustedPricesData()
FIXME: TO BE IMPLEMENTED

#### arcticFxPricesData()
FIXME: TO BE IMPLEMENTED

<a name="simData_objects">
</a>
# simData objects

The `simData` object is a compulsory part of the psystemtrade system object which runs simulations (or in live trading generates desired positions). The API required for that is laid out in the userguide, [here](#/docs/userguide.md#using-the-standard-data-objects). For maximum flexibility as of version 0.17 these objects are in turn constructed of methods that hook into data storage objects for specific sources. So for example in the default [`csvFuturesSimData`](/sysdata/csv/csv_sim_futures_data.py) the compulsory method (for futures) get_backadjusted_futures_price is hooked into an instance of [`csvFuturesAdjustedPricesData`](#csvFuturesAdjustedPricesData).

This modularity allows us to easily replace the data objects, so we could load our adjusted prices from mongo DB, or do 'back adjustment' of futures prices 'on the fly'.

## Provided simData objects

### csvSimData

### mongoSimData

## Modifying simData objects

### Getting data from another source

### Back-adjustment 'on the fly'

## Detailed internals of simData objects

### Naming convention and inheritance

### Construction from multiple parent classes

### Use of _get_object methods


