This document is specifically about *futures data*. It is broken into three sections. The first, [A futures data workflow](#futures_data_workflow), gives an overview of how data is typically processed. It describes how you would get some data from quandl, store it, and create back-adjusted prices. The next section [Storing futures data](#storing_futures_data) then describes in detail each of the components of the API for storing futures data. In the third and final section [simData objects](#simData_objects) you will see how we hook together individual data components to create a `simData` object that is used by the main simulation system.

Although this document is about futures data, parts two and three are necessary reading if you are trying to create or modify any data objects.

Table of Contents
=================

   * [Table of Contents](#table-of-contents)
   * [A futures data workflow](#a-futures-data-workflow)
      * [Setting up some instrument configuration](#setting-up-some-instrument-configuration)
      * [Roll parameter configuration](#roll-parameter-configuration)
      * [Getting historical data for individual futures contracts](#getting-historical-data-for-individual-futures-contracts)
      * [Roll calendars](#roll-calendars)
         * [Approximate roll calendars, adjusted with actual prices](#approximate-roll-calendars-adjusted-with-actual-prices)
            * [Calculate the roll calendar](#calculate-the-roll-calendar)
            * [Checks](#checks)
            * [Write CSV prices](#write-csv-prices)
         * [Roll calendars from existing 'multiple prices' .csv files](#roll-calendars-from-existing-multiple-prices-csv-files)
      * [Creating and storing multiple prices](#creating-and-storing-multiple-prices)
      * [Creating and storing back adjusted prices](#creating-and-storing-back-adjusted-prices)
      * [Backadjusting 'on the fly'](#backadjusting-on-the-fly)
      * [Changing the stitching method](#changing-the-stitching-method)
      * [Getting and storing FX data](#getting-and-storing-fx-data)
   * [Storing and representing futures data](#storing-and-representing-futures-data)
      * [Futures data objects and their generic data storage objects](#futures-data-objects-and-their-generic-data-storage-objects)
         * [<a href="/sysdata/futures/instruments.py">Instruments</a>: futuresInstrument() and futuresInstrumentData()](#instruments-futuresinstrument-and-futuresinstrumentdata)
         * [<a href="/sysdata/futures/contract_dates_and_expiries.py">Contract dates</a>: contractDate()](#contract-dates-contractdate)
         * [<a href="/sysdata/futures/rolls.py">Roll cycles</a>: rollCycle()](#roll-cycles-rollcycle)
         * [<a href="/sysdata/futures/rolls.py">Roll parameters</a>: rollParameters() and rollParametersData()](#roll-parameters-rollparameters-and-rollparametersdata)
         * [<a href="/sysdata/futures/rolls.py">Contract date with roll parameters</a>: contractDateWithRollParameters()](#contract-date-with-roll-parameters-contractdatewithrollparameters)
         * [<a href="/sysdata/futures/contracts.py">Futures contracts</a>: futuresContracts() and futuresContractData()](#futures-contracts-futurescontracts-and-futurescontractdata)
         * [<a href="/sysdata/futures/futures_per_contract_prices.py">Prices for individual futures contracts</a>: futuresContractPrices(), dictFuturesContractPrices() and futuresContractPriceData()](#prices-for-individual-futures-contracts-futurescontractprices-dictfuturescontractprices-and-futurescontractpricedata)
         * [<a href="/sysdata/futures/roll_calendars.py">Roll calendars</a>: rollCalendar() and rollCalendarData()](#roll-calendars-rollcalendar-and-rollcalendardata)
         * [<a href="/sysdata/futures/multiple_prices.py">Multiple prices</a>: futuresMultiplePrices() and futuresMultiplePricesData()](#multiple-prices-futuresmultipleprices-and-futuresmultiplepricesdata)
         * [<a href="/sysdata/futures/adjusted_prices.py">Adjusted prices</a>: futuresAdjustedPrices() and futuresAdjustedPricesData()](#adjusted-prices-futuresadjustedprices-and-futuresadjustedpricesdata)
         * [<a href="/sysdata/fx/spotfx.py">Spot FX data</a>: fxPrices() and fxPricesData()](#spot-fx-data-fxprices-and-fxpricesdata)
      * [Creating your own data objects, and data storage objects; a few pointers](#creating-your-own-data-objects-and-data-storage-objects-a-few-pointers)
      * [Data storage objects for specific sources](#data-storage-objects-for-specific-sources)
         * [Static csv files used for initialisation](#static-csv-files-used-for-initialisation)
         * [CSV data](#csv_files)
         * [mongo DB](#mongo-db)
         * [Quandl](#quandl)
         * [Arctic](#arctic)
      * [Creating your own data storage objects for a new source](#creating-your-own-data-storage-objects-for-a-new-source)
      * [Provided simData objects](#provided-simdata-objects)
         * [Getting data from another source](#getting-data-from-another-source)
         * [Back-adjustment 'on the fly'](#back-adjustment-on-the-fly)
         * [Back-adjustment 'on the fly' over several days](#back-adjustment-on-the-fly-over-several-days)
      * [Constructing your own simData objects](#constructing-your-own-simdata-objects)
         * [Naming convention and inheritance](#naming-convention-and-inheritance)
         * [Multiple inheritance](#multiple-inheritance)
         * [Hooks into data storage objects](#hooks-into-data-storage-objects)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)


<a name="futures_data_workflow"></a>
# A futures data workflow

This section describes a typical workflow for setting up futures data from scratch:

1. [Set up some static configuration information](#set_up_instrument_config) for instruments, and [roll parameters](#set_up_roll_parameter_config)
2. Get, and store, [some historical data](#get_historical_data)
3. Build, and store, [roll calendars](#roll_calendars)
4. Create and store ['multiple' price series](#create_multiple_prices) containing the relevant contracts we need for any given time period
5. Create and store [back-adjusted prices](#back_adjusted_prices)
6. Get, and store, [spot FX prices](#create_fx_data)

In future versions of pysystemtrade there will be code to keep your prices up to date.

<a name="set_up_instrument_config"></a>
## Setting up some instrument configuration

The first step is to store some instrument configuration information. In principal this can be done in any way, but we are going to *read* from .csv files, and *write* to a [Mongo Database](https://www.mongodb.com/). There are two kinds of configuration; instrument configuration and roll configuration. Instrument configuration consists of static information that enables us to map from the instrument code like EDOLLAR (it also includes cost levels, that are required in the simulation environment).

The relevant script to setup *information configuration* is in sysinit - the part of pysystemtrade used to initialise a new system. Here is the script you need to run [instruments_csv_mongo.py](/sysinit/futures/instruments_csv_mongo.py). Notice it uses two types of data objects: the object we write to [`mongoFuturesInstrumentData`](#mongoFuturesInstrumentData) and the object we read from [`csvFuturesInstrumentData`](#csvFuturesInstrumentData). These objects both inherit from the more generic futuresInstrumentData, and are specialist versions of that. You'll see this pattern again and again, and I describe it further in [part two of this document](#storing_futures_data). 

Make sure you are running a [Mongo Database](#mongoDB) before running this.

The information is sucked out of [this file](/sysinit/futures/config/instrumentconfig.csv) and into the mongo database whose connections are defined [here](/sysdata/mongodb/mongo_connection.py). The file includes a number of futures contracts that I don't actually trade or get prices for. Any configuration information for these may not be accurate and you use it at your own risk.

<a name="set_up_roll_parameter_config"></a>
## Roll parameter configuration

For *roll configuration* we need to initialise by running the code in this file [roll_parameters_csv_mongo.py](/sysinit/futures/roll_parameters_csv_mongo.py). Again it uses two types of data objects: we read from [a csv file](/sysinit/futures/config/rollconfig.csv) with [`initCsvFuturesRollData`](#initCsvFuturesRollData), and write to a mongo db with [`mongoRollParametersData`](#mongoRollParametersData). Again you need to make sure you are running a [Mongo Database](#mongoDB) before executing this script.

It's worth explaining the available options for roll configuration. First of all we have two *roll cycles*: 'priced' and 'hold'. Roll cycles use the usual definition for futures months (January is F, February G, March H, and the rest of the year is JKMNQUVX, with December Z). The 'priced' contracts are those that we can get prices for, whereas the 'hold' cycle contracts are those we actually hold. We may hold all the priced contracts (like for equities), or only only some because of liquidity issues (eg Gold), or to keep a consistent seasonal position (i.e. CRUDEW is Winter Crude, so we only hold December).

'RollOffsetDays': This indicates how many calendar days before a contract expires that we'd normally like to roll it. These vary from zero (Korean bonds KR3 and KR10 which you can't roll until the expiry date) up to -1100 (Eurodollar where I like to stay several years out on the curve).

'CarryOffset': Whether we take carry from an earlier dated contract (-1, which is preferable) or a later dated contract (+1, which isn't ideal but if we hold the front contract we have no choice). This calculation is done based on the *priced* roll cycle, so for example for winter crude where the *hold* roll cycle is just 'Z' (we hold December), and the carry offset is -1 we take the previous month in the *priced* roll cycle (which is a full year FGHJKMNQUVXZ) i.e. November (whose code is 'X'). You read more in Appendix B of [my first book](http://www.systematicmoney.org/systematic-trading).

'ExpiryOffset': How many days to shift the expiry date in a month, eg (the day of the month that a contract expires)-1. These values are just here so we can build roughly correct roll calendars (of which more later). In live trading you'd get the actual expiry date for each contract.


<a name="get_historical_data"></a>
## Getting historical data for individual futures contracts

Now let's turn our attention to getting prices for individual futures contracts. We could get this from anywhere, but we'll use [Quandl](https://wwww.quandl.com). Obviously you will need to [get the python Quandl library](#getQuandlPythonAPI), and you may want to [set a Quandl key](#setQuandlKey). 

We can also store it, in principal, anywhere but I will be using the open source [Arctic library](https://github.com/manahl/arctic) which was released by my former employers [AHL](https://ahl.com). This sits on top of Mongo DB (so we don't need yet another database) but provides straightforward and fast storage of pandas DataFrames.

We'll be using [this script](/sysinit/futures/historical_contract_prices_quandl_mongo.py). Unlike the first two initialisation scripts this is set up to run for a single market. 

By the way I can't just pull down this data myself and put it on github to save you time. Storing large amounts of data in github isn't a good idea regardless of whether it is in .csv or Mongo files, and there would also be licensing issues with basically just copying and pasting raw data from Quandl. You have to get, and then store, this stuff yourself. And of course at some point in a live system you would be updating this yourself.

This uses quite a few data objects:

- Price data for individual futures contracts: [quandlFuturesContractPriceData](#quandlFuturesContractPriceData) and [arcticFuturesContractPriceData](#arcticFuturesContractPriceData)
- Configuration needed when dealing with Quandl: [quandlFuturesConfiguration](#quandlFuturesConfiguration) - this reads [this .csv](/sysdata/quandl/QuandlFuturesConfig.csv) and defines the code and market; but also the first contract in Quandl's database.
- Instrument data (that we prepared earlier): [mongoFuturesInstrumentData](#mongoFuturesInstrumentData)
- Roll parameters data (that we prepared earlier): [mongoRollParametersData](#mongoRollParametersData)
- Two generic data objects (not for a specific source):  [listOfFuturesContracts](#listOfFuturesContracts), [futuresInstrument](#futuresInstrument)
 
The script does two things:

1. Generate a list of futures contracts, starting with the first contract defined in [this .csv](/sysdata/quandl/QuandlFuturesConfig.csv) and following the *price cycle*. The last contract in that series is the contract we'll currently hold, given the 'ExpiryOffset' parameter.
2. For each contract, get the prices from Quandl and write them into Arctic / Mongo DB.

<a name="roll_calendars"></a>
## Roll calendars

We're now ready to set up a *roll calendar*. A roll calendar is the series of dates on which we roll from one futures contract to the next. It might be helpful to read [my blog post](https://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html) on rolling futures contracts (though bear in mind some of the details relate to my current trading system and do no reflect how pysystemtrade works).

You can see a roll calendar for Eurodollar futures, [here](/data/futures/roll_calendars_csv/EDOLLAR.csv). On each date we roll from the current_contract shown to the next_contract. We also see the current carry_contract; we use the differential between this and the current_contract to calculate forecasts for carry trading rules.

There are two ways to generate roll calendars:

1. Generate an [approximate calendar](#roll_calendars_from_approx) based on the 'ExpiryOffset' parameter, and then adjust it so it is viable given the futures prices we have from the [previous stage](#get_historical_data).
2. Infer from [existing 'multiple price' data](#roll_calendars_from_multiple). [Multiple price data](/data/futures/multiple_prices_csv) are data series that include the prices for three types of contract: the current, next, and carry contract (though of course there may be overlaps between these). 

<a name="roll_calendars_from_approx"></a>
### Approximate roll calendars, adjusted with actual prices

This is the method you'd use if you were starting from scratch, and you'd just got some prices for each futures contract. The relevant script is [here](/sysinit/futures/rollcalendars_from_arcticprices_to_csv.py). Again it is only set up to run a single instrument at a time. 

In this script:

- We get prices for individual futures contract [from Arctic](#arcticFuturesContractPriceData) that we created in the [previous stage](#get_historical_data)
- We get roll parameters [from Mongo](#mongoRollParametersData), that [we made earlier](#set_up_roll_parameter_config) 
- We calculate the roll calendar: 
`roll_calendar = rollCalendar.create_from_prices(dict_of_futures_contract_prices, roll_parameters)`
- We do some checks on the roll calendar, for monotonicity and validity (these checks will generate warnings if things go wrong)
- If we're happy with the roll calendar we [write](#csvRollCalendarData) our roll calendar into a csv file 

#### Calculate the roll calendar

The actual code that generates the roll calendar is [here](/sysdata/futures/roll_calendars.py)

The interesting part is:

```python
approx_calendar = _generate_approximate_calendar(list_of_contract_dates, roll_parameters_object)
adjusted_calendar = _adjust_to_price_series(approx_calendar, dict_of_futures_contract_prices)
adjusted_calendar_with_carry = _add_carry_calendar(adjusted_calendar, roll_parameters_object)
```

So we first generate an approximate calendar, for when we'd ideally want to roll each of the contracts, based on our roll parameter `RollOffsetDays`. However we may find that there weren't *matching* prices for a given roll date. A matching price is when we have prices for both the current and next contract on the relevant day. If we don't have that, then we can't calculate an adjusted price. The *adjustment* stage finds the closest date to the ideal date (looking both forwards and backwards in time). If there are no dates with matching prices, then the process will return an error. Finally we add the carry contract on to the roll calendar - this isn't used for back adjustment but we still need it for forecasting using the carry trading rule.


#### Checks

We then check that the roll calendar is monotonic and valid.

A *monotonic* roll calendar will have increasing datestamps in the index. It's possible, if your data is messy, to get non-monotonic calendars. Unfortunately there is no automatic way to fix this, you need to dive in and rebuild the  (this is why I store the calendars as .csv files to make such hacking easy).

A *valid* roll calendar will have current and next contract prices on the roll date. Since this is how we generate the roll calendars they should always pass this test (if we couldn't find a date when we have aligned prices then the calendar generation would have failed with an exception).

#### Write CSV prices

Roll calendars are stored in .csv format [here](/data/futures/roll_calendars_csv/EDOLLAR.csv). Of course you could put these into Mongo DB, or Arctic, but I like the ability to hack them if required.

<a name="roll_calendars_from_multiple"></a>
### Roll calendars from existing 'multiple prices' .csv files

In the next section we learn how to use roll calendars, and price data for individual contracts, to create DataFrames of *multiple prices*: the series of prices for the current, forward and carry contracts; as well as the identify of those contracts. But it's also possible to reverse this operation: work out roll calendars from multiple prices.

Of course you can only do this if you've already got these prices, which means you already need to have a roll calendar: a catch 22. Fortunately there are sets of multiple prices provided in pysystemtrade, and have been for some time, [here](/data/futures/multiple_prices_csv). These are copies of the data in my legacy trading system, for which I had to generate historic roll calendars, and for the data since early 2014 include the actual dates when I rolled.

We run [this script](/sysinit/futures/rollcalendars_from_providedcsv_prices.py) which by default will loop over all the instruments for which we have data in the multiple prices directory. 


<a name="create_multiple_prices"></a>
## Creating and storing multiple prices

The next stage is to store *multiple prices*. Multiple prices are the price and contract identifier for the current contract we're holding, the next contract we'll hold, and the carry contract we compare with the current contract for the carry trading rule. They are required for the next stage, calculating back-adjusted prices, but are also used directly by the carry trading rule in a backtest. Constructing them requires a roll calendar, and prices for individual futures contracts.

We can store these prices in eithier Arctic or .csv files. The [relevant script ](/sysinit/futures/multipleprices_from_arcticprices_and_csv_calendars_to_arctic.py) gives you the option of doing eithier or both of these. 

<a name="back_adjusted_prices"></a>
## Creating and storing back adjusted prices

Once we have multiple prices we can then create a backadjusted price series. The [relevant script](/sysinit/futures/multipleprices_from_arcticprices_and_csv_calendars_to_arctic.py) will read multiple prices from Arctic, do the backadjustment, and then write the prices to Arctic. It's easy to modify this to read/write to/from different sources.


## Backadjusting 'on the fly'

It's also possible to implement the back-adjustment 'on the fly' within your backtest. More details later in this document, [here](#back_adjust_on_the_fly).

## Changing the stitching method

If you don't like panama stitching then you can modify the method. More details later in this document, [here](#futuresAdjustedPrices).

<a name="storing_futures_data"></a>


<a name="create_fx_data"></a>
## Getting and storing FX data

Although strictly not futures prices we also need spot FX prices to run our simulation. Again we'll get these from Quandl, and in [this simple script](/sysinit/futures/spotfx_from_quandl_to_arctic_and_csv.py) they are written to Arctic and/or .csv files.

# Storing and representing futures data

The paradigm for data storage is that we have a bunch of [data objects](#generic_objects) for specific types of data, i.e. futuresInstrument is the generic class for storing static information about instruments. Each of those objects then has a matching *data storage object* which accesses data for that object, i.e. futuresInstrumentData. Then we have [specific instances of those for different data sources](#specific_data_storage), i.e. mongoFuturesInstrumentData for storing instrument data in a mongo DB database. 


<a name="generic_objects"></a>
## Futures data objects and their generic data storage objects

<a name="futuresInstrument"></a>
### [Instruments](/sysdata/futures/instruments.py): futuresInstrument() and futuresInstrumentData()

Futures instruments are the things we actually trade, eg Eurodollar futures, but not specific contracts. Apart from the instrument code we can store *metadata* about them. This isn't hard wired into the class, but currently includes things like the asset class, cost parameters, and so on.

<a name="contractDate"></a>
### [Contract dates](/sysdata/futures/contract_dates_and_expiries.py): contractDate()

Note: There is no data storage for contract dates, they are stored only as part of [futures contracts](#futuresContracts).

A contract date allows us to identify a specific [futures contract](#futuresContracts) for a given [instrument](#futuresInstrument). Futures contracts can eithier be for a specific month (eg '201709') or for a specific day (eg '20170903'). The latter is required to support weekly VIX contracts (although in practice I haven't actually written the code to support them fully yet). A monthly date will be represented with trailing zeros, eg '20170900'.

We can also store expiry dates in contract dates. This can be done eithier by passing the exact date (which we'd do if we were getting the contract specs from our broker) or an approximate expiry offset, where 0 (the default) means the expiry is on day 1 of the relevant contract month.

<a name="rollCycle"></a>
### [Roll cycles](/sysdata/futures/rolls.py): rollCycle()

Note: There is no data storage for roll cycles, they are stored only as part of [roll parameters](#rollParameters).

Roll cycles are the mechanism by which we know how to move forwards and backwards between contracts as they expire, or when working out carry trading rule forecasts. Roll cycles use the usual definition for futures months (January is F, February G, March H, and the rest of the year is JKMNQUVX, with December Z). 

<a name="rollParameters"></a>
### [Roll parameters](/sysdata/futures/rolls.py): rollParameters() and rollParametersData()

The roll parameters include all the information we need about how a given instrument rolls:

- `hold_rollcycle` and `priced_rollcycle`. The 'priced' contracts are those that we can get prices for, whereas the 'hold' cycle contracts are those we actually hold. We may hold all the priced contracts (like for equities), or only only some because of liquidity issues (eg Gold), or to keep a consistent seasonal position (i.e. CRUDEW is Winter Crude, so we only hold December).
- `roll_offset_day`: This indicates how many calendar days before a contract expires that we'd normally like to roll it. These vary from zero (Korean bonds KR3 and KR10 which you can't roll until the expiry date) up to -1100 (Eurodollar where I like to stay several years out on the curve).
- `carry_offset`: Whether we take carry from an earlier dated contract (-1, which is preferable) or a later dated contract (+1, which isn't ideal but if we hold the front contract we have no choice). This calculation is done based on the *priced* roll cycle, so for example for winter crude where the *hold* roll cycle is just 'Z' (we hold December), and the carry offset is -1 we take the previous month in the *priced* roll cycle (which is a full year FGHJKMNQUVXZ) i.e. November (whose code is 'X'). You read more in Appendix B of [my first book](https://www.systematicmoney.org/systematic-trading) and in [my blog post](https://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html).
- `approx_expiry_offset`: How many days to shift the expiry date in a month, eg (the day of the month that a contract expires)-1. These values are just here so we can build roughly correct roll calendars (of which more later). In live trading you'd get the actual expiry date for each contract.

<a name="contractDateWithRollParameters"></a>
### [Contract date with roll parameters](/sysdata/futures/rolls.py): contractDateWithRollParameters()

Note: There is no data storage for contract dates, they are stored only as part of [futures contracts](#futuresContracts).

Combining a contract date with some roll parameters means we can answer important questions like, what is the next (or previous) contract in the priced (or held) roll cycle? What is the contract I should compare this contract to when calculating carry? On what date would I want to roll this contract?

<a name="listOfFuturesContracts"></a>
<a name="futuresContracts"></a>
### [Futures contracts](/sysdata/futures/contracts.py): futuresContracts() and futuresContractData()


The combination of a specific [instrument](#futuresInstrument) and a [contract date](#contractDate) (possibly [with roll parameters](#contractDateWithRollParameters)) is a `futuresContract`. 

`listOfFuturesContracts`: This dull class exists purely so we can generate a series of historical contracts from some roll parameters.

<a name="futuresContractPrices"></a>
### [Prices for individual futures contracts](/sysdata/futures/futures_per_contract_prices.py): futuresContractPrices(), dictFuturesContractPrices() and futuresContractPriceData()


The price data for a given contract is just stored as a DataFrame with specific column names. Notice that we store Open, High, Low, Close and Settle prices; but currently in the rest of pysystemtrade we effectively throw away everything except Settle.

`dictFuturesContractPrices`: When calculating roll calendars we work with prices from multiple contracts at once.

<a name="rollCalendar"></a>
### [Roll calendars](/sysdata/futures/roll_calendars.py): rollCalendar() and rollCalendarData()

A roll calendar is a pandas DataFrame with columns for: 

- current_contract
- next_contract
- carry_contract

Each row shows when we'd roll from holding current_contract (and using carry_contract) on to next_contract. As discussed [earlier](#roll_calendars) they can be created from a set of [roll parameters](#rollParameters) and [price data](#futuresContractPrices), or inferred from existing [multiple price data](#futuresMultiplePrices).

<a name="futuresMultiplePrices"></a>
### [Multiple prices](/sysdata/futures/multiple_prices.py): futuresMultiplePrices() and futuresMultiplePricesData()

A multiple prices object is a pandas DataFrame with columns for:PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD, and FORWARD_CONTRACT. 

We'd normally create these from scratch using a roll calendar, and some individual futures contract prices (as discussed [here](#create_multiple_prices)). Once created they can be stored and reloaded.


<a name="futuresAdjustedPrices"></a>
### [Adjusted prices](/sysdata/futures/adjusted_prices.py): futuresAdjustedPrices() and futuresAdjustedPricesData()

The representation of adjusted prices is boring beyond words; they are a pandas Series. More interesting is the fact you can create one with a back adjustment process given a [multiple prices object](#futuresMultiplePrices):

```python
from sysdata.futures.adjusted_prices import futuresAdjustedPrices
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData

# assuming we have some multiple prices
arctic_multiple_prices = arcticFuturesMultiplePricesData()
multiple_prices = arctic_multiple_prices.get_multiple_prices("EDOLLAR")

adjusted_prices = futuresAdjustedPrices.stich_multiple_prices(multiple_prices)
```

The adjustment defaults to the panama method. If you want to use your own stitching method then override the method `futuresAdjustedPrices.stich_multiple_prices`.


<a name="fxPrices"></a>
### [Spot FX data](/sysdata/fx/spotfx.py): fxPrices() and fxPricesData()

Technically bugger all to do with futures, but implemented in pysystemtrade as it's required for position scaling.

## Creating your own data objects, and data storage objects; a few pointers

You should store your objects in [this directory](/sysdata/futures) (for futures) or a new subdirectory of the [sysdata](/sysdata/) directory (for new asset classes). Data objects and data storage objects should live in the same file. Data objects may inherit from other objects (for example for options you might want to inherit from the underlying future), but they don't have to. Data storage objects should all inherit from [baseData](/sysdata/data.py). 

Data objects should be prefixed with the asset class if there is any potential confusion, i.e. futuresInstrument, equitiesInstrument. Data storage objects should have the same name as their data object, but with a Data suffix, eg futuresInstrumentData.

Methods you'd probably want to include in a data object:

- `create_from_dict` (`@classmethod`): Useful when reading data from a source
- `as_dict`: Useful when writing data to a source
- `create_empty` (`@classmethod`): Useful when reading data from a source if the object is unavailable, better to return one of these than throw an error in case the calling process is indifferent about missing data
- `empty`: returns True if this is an empty object

Methods you'd probably want to include in a data storage object:
 
- `keys()` and `__getitem__`. It's nice if data storage objects look like dicts. `keys()` should be mapped to `get_list_of_things_with_data`. `__getitem__` should be mapped to `get_some_data`
- `get_list_of_things_with_data`, i.e. the list of instrument codes with valid data. Should `raise NotImplementedError`
- `get_some_data`: Check to see if `is_thing_in_data` is True, then call `_get_some_data_without_checking`. If not in data, return an empty instance of the data object.
- `is_thing_in_data` i.e. is a particular instrument code in the list of codes with valid data
- `_get_some_data_without_checking`: `raise NotImplementedError`
- `delete_data_for_thing`: Check that a 'are you sure' flag is set, and that `is_thing_in_data` is True, then call `_delete_data_for_thing_without_checking`
- `_delete_data_for_thing_without_checking`: `raise NotImplementedError`
- `add_data_for_thing`: Check to see if `is_thing_in_data` is False (or that an ignore duplicates flag is set), then call `_add_data_for_thing_without_checking`
- `_add_data_for_thing_without_checking`: `raise NotImplementedError`

By the way you shouldn't actually use method names like `get_list_of_things_with_data`, that's just plain silly. Instead use `get_list_of_instruments` or what not.

Notice the use of private methods to interact with the data inside public methods that perform standard checks; these methods that actually interact with the data (rather than just mapping to other methods, or performing checks) should raise a NotImplementedError; this will then be overriden in the [data storage object for a specific data source](#specific_data_storage).

<a name="specific_data_storage"></a>
## Data storage objects for specific sources

This section covers the various sources for reading and writing [data objects](#storing_futures_data) I've implemented in pysystemtrade. 

### Static csv files used for initialisation of databases

In the initialisation part of the workflow (in [section one](#futures_data_workflow) of this document) I copied some information from .csv files to initialise a database. To acheive this we need to create some read-only access methods to the relevant .csv files (which are stored [here](/sysinit/futures/config/)).

<a name="init_instrument_config"></a>
#### csvFuturesInstrumentData()(/sysdata/csv/csv_instrument_config.py) inherits from [futuresInstrumentData](#futuresInstrumentData)

Using this script, [instruments_csv_mongo.py](/sysinit/futures/instruments_csv_mongo.py), reads instrument object data from [here](/sysinit/futures/config/instrumentconfig.csv) using [csvFuturesInstrumentData](#csvFuturesInstrumentData). This class is not specific for initialising the database, and is also used later [for simulation data](#csvFuturesSimData).

<a name="initCsvFuturesRollData"></a>
#### [initCsvFuturesRollData()](/sysinit/futures/csv_data_readers/rolldata_from_csv.py) inherits from [rollParametersData](#rollParametersData)

Using this script, [roll_parameters_csv_mongo.py](/sysinit/futures/roll_parameters_csv_mongo.py), reads roll parameters for each instrument from [here](/sysinit/futures/config/rollconfig.csv)

<a name="csv_files"></a>
### Csv files for time series data

Storing data in .csv files has some obvious disadvantages, and doesn't feel like the sort of thing a 21st century trading system ought to be doing. However it's good for roll calendars, which sometimes need manual hacking when they're created. It's also good for the data required to run backtests that lives as part of the github repo for pysystemtrade (storing large binary files in git is not a great idea, although various workarounds exist I haven't yet found one that works satisfactorily).

For obvious (?) reasons we only implement get and read methods for .csv files (So... you want to delete the .csv file? Do it through the filesystem. Don't get python to do your dirty work for you).

<a name="csvFuturesInstrumentData"></a>
#### [csvFuturesInstrumentData()](/sysdata/csv/csv_instrument_config.py) inherits from [futuresInstrumentData](#futuresInstrumentData)

Reads futures configuration information from [here](/data/futures/csvconfig/instrumentconfig.csv) (note this is a seperate file from the one used to initialise the mongoDB database [earlier](#init_instrument_config) although this uses the same class method to get the data). Columns currently used by the simulation engine are: Instrument, Pointsize, AssetClass, Currency, Slippage, PerBlock, Percentage, PerTrade. Extraneous columns don't affect functionality. 

<a name="csvRollCalendarData"></a>
#### [csvRollCalendarData()](/sysdata/csv/csv_roll_calendars.py) inherits from [rollParametersData](#rollParametersData)

Reads roll calendars from [here](/data/futures/roll_calendars_csv). File names are just instrument names. File format is index DATE_TIME; columns: current_contract, next_contract, carry_contract. Contract identifiers should be in yyyymmdd format, with dd='00' for monthly contracts (currently weekly contracts aren't supported).

<a name="csvFuturesMultiplePricesData"></a>
#### [csvFuturesMultiplePricesData()](/sysdata/csv/csv_multiple_prices.py) inherits from [futuresMultiplePricesData](#futuresMultiplePricesData)

Reads multiple prices (the prices of contracts that are currently interesting) from [here](/data/futures/multiple_prices_csv). File names are just instrument names. File format is index DATETIME; columns: PRICE, CARRY, FORWARD, CARRY_CONTRACT, PRICE_CONTRACT, FORWARD_CONTRACT. Prices are floats. Contract identifiers should be in yyyymmdd format, with dd='00' for monthly contracts (currently weekly contracts aren't supported). 



<a name="csvFuturesAdjustedPriceData"></a>
#### [csvFuturesAdjustedPricesData()](/sysdata/csv/csv_adjusted_prices.py) inherits from [futuresAdjustedPricesData](#futuresAdjustedPricesData)

Reads back adjusted prices from [here](/data/futures/adjusted_prices_csv). File names are just instrument names. File format is index DATETIME; columns: PRICE.


<a name="csvFxPricesData"></a>
#### [csvFxPricesData()](/sysdata/csv/csv_spot_fx.py) inherits from [fxPricesData](#fxPricesData)

Reads back adjusted prices from [here](/data/futures/fx_prices_csv). File names are CC1CC2, where CC1 and CC12 are three letter ISO currency abbreviations (eg  GBPEUR). Cross rates do not have to be stored, they will be calculated on the fly. File format is index DATETIME; columns: FX.


<a name="mongoDB"></a>
### mongo DB

For production code, and storing large amounts of data (eg for individual futures contracts) we probably need something more robust than .csv files. [MongoDB](https://mongodb.com) is a no-sql database which is rather fashionable at the moment, though the main reason I selected it for this purpose is that it is used by [Arctic](#arctic). 

Obviously you will need to make sure you already have a Mongo DB instance running. You might find you already have one running, in Linux use `ps wuax | grep mongo` and then kill the relevant process.

All Mongo code uses the connection information defined in [this class](/sysdata/mongodb/mongo_connection.py). Personally I like to keep my Mongo data in a specific subdirectory; that is achieved by starting up with `mongod --dbpath ~/pysystemtrade/data/futures/mongodb/` (in Linux). Of course this isn't compulsory.


<a name="mongoFuturesInstrumentData"></a>
#### [mongoFuturesInstrumentData()](/sysdata/mongodb/mongo_futures_instruments.py) inherits from [futuresInstrumentData](#futuresInstrumentData)

This stores instrument static data in a dictionary format.


<a name="mongoRollParametersData"></a>
#### [mongoRollParametersData()](/sysdata/mongodb/mongo_roll_data.py) inherits from [rollParametersData](#rollParametersData)

This stores roll parameters in a dictionary format.

<a name="mongoFuturesContractData"></a>
#### [mongoFuturesContractData()](/sysdata/mongodb/mongo_futures_contracts.py) inherits from [futuresContractData](#futuresContractData)

This stores futures contract data in a dictionary format.


### Quandl

[Quandl](https://quandl.com) is an awesome way of getting data, much of which is free, via a simple Python API. 

<a name="getQuandlPythonAPI"></a>
#### Getting the Quandl python API

At the time of writing you get this from [here](https://docs.quandl.com/docs/python-installation) (external link, may fail).

<a name="setQuandlKey"></a>
#### Setting a Quandl API key

Having a Quandl API key means you can download a fair amount of data for free without being throttled. If you have one then you should first create a file 'private_config.yaml' in the private directory of [pysystemtrade](#/private). Then add this line:

```
quandl_key: 'your_key_goes_here'
```

<a name="quandlFuturesConfiguration"></a>

#### [quandlFuturesConfiguration()](/sysdata/quandl/quandl_futures.py)

Acceses [this .csv file](/sysdata/quandl/QuandlFuturesConfig.csv) which contains the codes and markets required to get data from Quandl.

<a name="quandlFuturesContractPriceData"></a>
#### [quandlFuturesContractPriceData()](/sysdata/quandl/quandl_futures.py) inherits from [futuresContractPriceData](#futuresContractPriceData)

Reads price data and returns in the form of [futuresContractPrices](#futuresContractPrices) objects. Notice that as this is purely a source of data we don't implement write methods.


#### [quandlFxPricesData()](/sysdata/quandl/quandl_spotfx_prices.py) inherits from [fxPricesData](#fxPricesData)

Reads FX spot prices from QUANDL. Acceses [this .csv file](/sysdata/quandl/QuandlFXConfig.csv) which contains the codes required to get data from Quandl for a specific currency.


<a name="arctic"></a>
### Arctic 

[Arctic](https://github.com/manahl/arctic) is a superb open source time series database which sits on top of [Mongo DB](#mongoDB) and provides straightforward and fast storage of pandas DataFrames. It was created by my former colleagues at [Man AHL](https://ahl.com) (in fact I beta tested a very early version of Arctic), and then very generously released as open source. You don't need to run multiple instances of Mongo DB when using my data objects for Mongo DB and Arctic, they use the same one. However we configure them seperately; the configuration for Arctic objects is [here](/sysdata/arctic/arctic_connection.py) (so in theory you could use two instances on different machines with seperate host names).

Basically my mongo DB objects are for storing static information, whilst Arctic is for time series.

Arctic has several *storage engines*, in my code I use the default VersionStore. 

<a name="arcticFuturesContractPriceData"></a>
#### [arcticFuturesContractPriceData()](/sysdata/arctic/arctic_futures_per_contract_prices.py) inherits from [futuresContractPriceData](#futuresContractPriceData)

Read and writes per contract futures price data.

#### [arcticFuturesMultiplePricesData()](/sysdata/arctic/arctic_multiple_prices.py) inherits from [futuresMultiplePricesData()](#futuresMultiplePricesData)

Read and writes multiple price data for each instrument.

#### [arcticFuturesAdjustedPricesData()](/sysdata/arctic/arctic_adjusted_prices.py) inherits from [futuresAdjustedPricesData()](#futuresAdjustedPricesData)

Read and writes adjusted price data for each instrument.

#### [arcticFxPricesData()](/sysdata/arctic/arctic_spotfx_prices.py) inherits from [fxPricesData()](#fxPricesData)

Read and writes spot FX data for each instrument.

## Creating your own data storage objects for a new source

Creating your own data storage objects is trivial, assuming they are for an existing kind of data object. 

They should live in a subdirectory of [sysdata](/sysdata), named for the data source i.e. [sysdata/arctic](/sysdata/arctic).

Look at an existing data storage object for a different source to see which methods you'd need to implement, and to see the generic data storage object you should inherit from. Normally you'd need to override all the methods in the generic object which return `NotImplementedError`; the exception is if you have a read-only source like Quandl, or if you're working with .csv or similar files in which case I wouldn't recommend implementing delete methods.

Use the naming convention sourceNameOfGenericDataObject, i.e. `class arcticFuturesContractPriceData(futuresContractPriceData)`. 

For databases you may want to create connection objects (like [this](#/sysdata/arctic/arctic_connection.py) for Arctic) 


<a name="simData_objects"></a>
# simData objects

The `simData` object is a compulsory part of the psystemtrade system object which runs simulations (or in live trading generates desired positions). The API required for that is laid out in the userguide, [here](/docs/userguide.md#using-the-standard-data-objects). For maximum flexibility as of version 0.17 these objects are in turn constructed of methods that hook into data storage objects for specific sources. So for example in the default [`csvFuturesSimData`](/sysdata/csv/csv_sim_futures_data.py) the compulsory method (for futures) get_backadjusted_futures_price is hooked into an instance of `csvFuturesAdjustedPricesData`.

This modularity allows us to easily replace the data objects, so we could load our adjusted prices from mongo DB, or do 'back adjustment' of futures prices 'on the fly'.

For futures simData objects need to know the source of:

- back adjusted prices
- multiple price data
- spot FX prices
- instrument configuration and cost information

Direct access to other kinds of information isn't neccessary for simulations.

## Provided simData objects

I've provided two complete simData objects which get their data from different sources: [csvSimData](#csvSimData) and [mongoSimData](#mongoSimData).

<a name="csvFuturesSimData"></a>
### [csvFuturesSimData()](/sysdata/csv/csv_sim_futures_data.py)

The simplest simData object gets all of its data from .csv files, making it ideal for simulations if you haven't built a process yet to get your own data. It's essentially a like for like replacement for the simpler csvSimData objects that pysystemtrade used in versions before 0.17.0.

<a name="mongoSimData"></a>
### [arcticFuturesSimData()](/sysdata/arctic/arctic_and_mongo_sim_futures_data.py)

This is a simData object which gets it's data out of Mongo DB (static) and Arctic (time series) (*Yes the class name should include both terms. Yes I shortened it so it isn't ridiculously long, and most of the interesting stuff comes from Arctic*). It is better for live trading.

Because the mongoDB data isn't included in the github repo, before using this you need to write the required data into Mongo and Arctic.
You can do this from scratch, as per the ['futures data workflow'](#a-futures-data-workflow) at the start of this document:

- [Instrument configuration and cost data](#setting-up-some-instrument-configuration)
- [Adjusted prices](#creating-and-storing-back-adjusted-prices)
- [Multiple prices](#creating-and-storing-multiple-prices)
- [Spot FX prices](#create_fx_data)

Alternatively you can run the following scripts which will copy the data from the existing github .csv files:

- [Instrument configuration and cost data](/sysinit/futures/repocsv_instrument_config.py)
- [Adjusted prices](/sysinit/futures/repocsv_adjusted_prices.py)
- [Multiple prices](/sysinit/futures/repocsv_multiple_prices.py)
- [Spot FX prices](/sysinit/futures/repocsv_spotfx_prices.py)

Of course it's also possible to mix these two methods. Once you have the data it's just a matter of replacing the default csv data object:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
from sysdata.arctic.arctic_and_mongo_sim_futures_data import arcticFuturesSimData
system = futures_system(data = arcticFuturesSimData(), log_level="on")
print(system.accounts.portfolio().sharpe())
```
### A note about multiple configuration files

Configuration information about futures instruments is stored in a number of different places:

- Instrument configuration and cost levels in this [.csv file](/data/futures/csvconfig/instrumentconfig.csv), used by default with `csvFuturesSimData` or will be copied to the database with [this script](/sysinit/futures/repocsv_instrument_config.py)
- Instrument configuration and cost levels in the sysinit module in [this .csv file](/sysinit/futures/config/instrumentconfig.csv), which will be copied to Mongo DB with [this script](/sysinit/futures/instruments_csv_mongo.py)
- Roll configuration information in [this .csv file](/sysinit/futures/config/rollconfig.csv), which will be copied to Mongo DB with [this script](/sysinit/futures/roll_parameters_csv_mongo.py)

The instruments in these lists won't neccessarily match up; not all contracts have prices available in Quandl, and in some places I've included information for contracts that I don't currently trade (so which aren't included in the main simulation .csv configuration file).

The `system.get_instrument_list()` method is used by the simulation to decide which markets to trade; if no explicit list of instruments is included then it will fall back on the method `system.data.get_instrument_list()`. In both the provided simData objects this will resolve to the method `get_instrument_list` in the class which gets back adjusted prices, or in whatever overrides it for a given data source (.csv or Mongo DB). In practice this means it's okay if your instrument configuration (or roll configuration, when used) is a superset of the instruments you have adjusted prices for. But it's not okay if you have adjusted prices for an instrument, but no configuration information.

<a name="modify_SimData"></a>
## Modifying simData objects

Constructing simData objects in the way I've done makes it relatively easy to modify them. Here are a few examples.

### Getting data from another source

Let's suppose you want to use Arctic and Mongo DB data, but get your spot FX prices from a .csv file. OK this is a silly example, but hopefully it will be easy to generalise this to doing more sensible things. Modify the file [arctic_and_mongo_sim_futures_data.py](/sysdata/arctic/arctic_and_mongo_sim_futures_data.py):

```python
# add import
from sysdata.csv.csv_sim_futures_data import csvFXData

# replace this class: class arcticFuturesSimData()
# with:

class arcticFuturesSimData(csvFXData, arcticFuturesAdjustedPriceSimData,
                           mongoFuturesConfigDataForSim, arcticFuturesMultiplePriceSimData):

    def __repr__(self):
        return "arcticFuturesSimData for %d instruments getting FX data from csv land" % len(self.get_instrument_list())


```

If you want to specify a custom .csv directory or you'll also need to write a special __init__ class to achieve that (bearing in mind that these are specified in the __init__ for `csvPaths` and `dbconnections`, which ultimately are both inherited by `arcticFuturesSimData`)- I haven't tried it myself.

<a name="back_adjust_on_the_fly"></a>
### Back-adjustment 'on the fly'

This is a modification to csvSimData which calculates back adjustment prices 'on the fly', rather than getting them pre-loaded from another database. This would allow you to use different back adjustments and see what effects they had. Note that this will work 'out of the box' for any 'single point' back adjustment where the roll happens on a single day, and where you can use multiple price data (which we already have). For any back adjustment where the process happens over several days you'd need to add extra methods to access individual futures contract prices and roll calendars. This is explained [in the next section](#back_adjust_on_the_fly_multiple_days).

Create a new class:
```python
from sysdata.futures.futuresDataForSim import futuresAdjustedPriceData, futuresAdjustedPrice
from sysdata.futures.adjusted_prices import futuresAdjustedPrices

class backAdjustOnTheFly(futuresAdjustedPriceData):
    def get_backadjusted_futures_price(self, instrument_code):
        multiple_prices = self._get_all_price_data(instrument_code)
        adjusted_prices = futuresAdjustedPrices.stitch_multiple_prices(multiple_prices)

        return adjusted_prices
```

In the file [csv_sim_futures_data](/sysdata/csv/csv_sim_futures_data.py) replace: 

```python
class csvFuturesSimData(csvFXData, csvFuturesAdjustedPriceData, csvFuturesConfigDataForSim, csvFuturesMultiplePriceData):
```

with:

```python
class csvFuturesSimData(csvFXData, backAdjustOnTheFly, csvFuturesConfigDataForSim, csvFuturesMultiplePriceData):
```

If you want to test different adjustment techniques other than the default 'Panama stich', then you need to override `futuresAdjustedPrices.stitch_multiple_prices()`.


<a name="back_adjust_on_the_fly_multiple_days"></a>
### Back-adjustment 'on the fly' over several days
For any back adjustment where the process happens over multiple days you'd need to add extra methods to access individual futures contract prices and roll calendars. Let's suppose we want to get these from Arctic (prices) and .csv files (roll calendars).


You'll need to override `futuresAdjustedPrices.stitch_multiple_prices()` so it uses roll calendars and individual contract; I assume you inherit from futuresAdjustedPrices and have a new class with the override: `futuresAdjustedPricesExtraData`. Then create the following classes:

```python
from sysdata.futures.futuresDataForSim import futuresAdjustedPriceData, futuresAdjustedPrice
from somewhere import futuresAdjustedPricesExtraData # you need to provide this yourself
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.csv.csv_roll_calendars import csvRollCalendarData

class backAdjustOnTheFlyExtraData(futuresAdjustedPriceData):
    def get_backadjusted_futures_price(self, instrument_code):
        individual_contract_prices = self._get_individual_contract_prices(instrument_code)
        roll_calendar = self._get_roll_calendar(instrument_code)
        adjusted_prices = futuresAdjustedPricesExtraData.stich_multiple_prices(roll_calendar, individual_contract_prices)

        return adjusted_prices

class arcticContractPricesForSim():
    def _get_individual_contract_prices(instrument_code):
        arctic_contract_prices_data_object = self._get_arctic_contract_prices_data_object()
        
        return arctic_contract_prices_data_object.get_all_prices_for_instrument(instrument_code)

    def _get_arctic_contract_prices_data_object(self):
        # this will just use the default connection but you change if you like
        arctic_contract_prices_data_object = arcticFuturesContractPriceData()
        arctic_contract_prices_data_object.log = self.log
        return arctic_contract_prices_data_object

class csvRollCalendarForSim():
    def _get_roll_calendar(self, instrument_code):
        roll_calendar_data_object = self.__get_csv_roll_calendar_data_object()
        
        return roll_calendar_data_object.get_roll_calendar(instrument_code)

    def _get_csv_roll_calendar_data_object(self):
        pathname =self._resolve_path("roll_calendars")
        roll_calendar_data_object  = csvRollCalendarData(data_path)
        roll_calendar_data_object.log = self.log

        return roll_calendar_data_object 

```


In the file [csv_sim_futures_data](/sysdata/csv/csv_sim_futures_data.py) replace: 

```python
class csvFuturesSimData(csvFXData, csvFuturesAdjustedPriceData, csvFuturesConfigDataForSim, csvFuturesMultiplePriceData):
```

with:

```python
class csvFuturesSimData(csvFXData, backAdjustOnTheFlyExtraData, csvRollCalendarForSim, arcticContractPricesForSim, csvFuturesConfigDataForSim, csvFuturesMultiplePriceData):
```


## Constructing your own simData objects

If you want to construct your own simData objects it's worth understanding their detailed internals in a bit more detail.

### Naming convention and inheritance

The base class is [simData](/sysdata/data.py). This in turn inherits from baseData, which is also the parent class for the [data storage objects](#storing_futures_data described) earlier in this document. simData implements a number of compulsory methods that we need to run simulations. These are described in more detail in the main [user guide](/docs/userguide.md#data) for pysystemtrade.

We then inherit from simData for a specific asset class implementation, i.e. for futures we have the method futuresSimData in [futuresDataForSim.py](/sysdata/futures/futuresDataForSim.py). This adds methods for additional types of data (eg carry) but can also override methods (eg get_raw_price is overriden so it gets backadjusted futures prices).

We then inherit for specific data source implementations. For .csv files we have the method csvSimFuturesData in [csv_sim_futures_data.py](/sysdata/csv/csv_sim_futures_data.py).

Notice the naming convention: sourceAssetclassSimData.

### Multiple inheritance

Because they are quite complex I've broken down the futures simData objects into sub-classes, bringing everything back together with multiple inheritance in the final simData classes we actually use.

So for futures we have the following classes in [futuresDataForSim.py](/sysdata/futures/futuresDataForSim.py), which are generic regardless of source (all inheriting from simData):

1. futuresAdjustedPriceData(simData)
2. futuresMultiplePriceData(simData)
3. futuresConfigDataForSim(simData)
4. futuresSimData: This class is redundant for reasons that will become obvious below

Then for csv files we have the following in [csv_sim_futures_data.py](/sysdata/csv/csv_sim_futures_data.py):

1. csvPaths(simData): To ensure consistent resolution of path names when locating .csv files
2. csvFXData(csvPaths, simData): Covers methods unrelated to futures, so directly inherits from the base simData class
3. csvFuturesConfigDataForSim(csvPaths, futuresConfigDataForSim)
4. csvFuturesAdjustedPriceData(csvPaths, futuresAdjustedPriceData)
5. csvMultiplePriceData(csvPaths, futuresMultiplePriceData)
6. csvFuturesSimData(csvFXData, csvFuturesAdjustedPriceData, csvFuturesConfigDataForSim, csvMultiplePriceData)

Classes 3,4 and 5 each inherit from one of the futures sub classes (class 2 bypasses the futures specific classes and inherits directly from simData - strictly speaking we should probably have an fxSimData class in between these). Then class 6 ties all these together. Notice that futuresSimData isn't referenced anywhere; it is included only as a template to show how you should do this 'gluing' together.

### Hooks into data storage objects

The methods we write for specific sources to override the methods in simData or simFuturesData type objects should all 'hook' into a [data storage object for the appropriate source](#specific_data_storage). I suggest using common methods to get the relevant data storage object, and to look up path names or otherwise configure the storage options (eg database hostname).

Eg here is the code for csvFuturesMultiplePriceData in [csv_sim_futures_data.py](/sysdata/csv/csv_sim_futures_data.py), with additional annotations:

```python
class csvMultiplePriceData(csvPaths, futuresMultiplePriceData):
    def _get_all_price_data(self, instrument_code): # overides a method in futuresMultiplePriceData
        csv_multiple_prices_data = self._get_all_prices_data_object() # get a data storage object (see method below)
        instr_all_price_data = csv_multiple_prices_data.get_multiple_prices(instrument_code) # Call relevant method of data storage object

        return instr_all_price_data

    def _get_all_prices_data_object(self): # data storage object

        pathname = self._resolve_path("multiple_price_data") # call to csvPaths class method to get path

        csv_multiple_prices_data = csvFuturesMultiplePricesData(datapath=pathname) # create a data storage object for .csv files with the pathname
        csv_multiple_prices_data.log = self.log # ensure logging is consistent

        return csv_multiple_prices_data # return the data storage object instance


```

