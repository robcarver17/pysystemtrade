This document is specifically about storing and processing *futures data*. 

Related documents:

- [Using pysystemtrade as a production trading environment](/docs/production.md)
- [Backtesting with pysystemtrade](/docs/backtesting.md)
- [Connecting pysystemtrade to interactive brokers](/docs/IB.md)

It is broken into four parts. The first, [A futures data workflow](#futures_data_workflow), gives an overview of how data is typically processed. It describes how you would get some data from, store it, and create data suitable for simulation and as an initial state for trading. Reading this will also give you a feel for the data in pysystemtrade. The rest of the document goes into much more detail. In [part two](#part-2-overview-of-futures-data-in-pysystemtrade), I provide an overview of how the various data objects fit together. The third part, [storing futures data](#storing_futures_data), then describes in detail each of the components used to futures data. In the [final part](#part-4-interfaces),  you will see how we provide an interface between the data storage objects and the simulation / production code.


Table of Contents
=================

* [Part 1: A futures data workflow](#part-1-a-futures-data-workflow)
   * [A note on data storage](#a-note-on-data-storage)
   * [Setting up some instrument configuration](#setting-up-some-instrument-configuration)
   * [Roll parameter configuration](#roll-parameter-configuration)
   * [Getting historical data for individual futures contracts](#getting-historical-data-for-individual-futures-contracts)
      * [Getting data from the broker (Interactive brokers)](#getting-data-from-the-broker-interactive-brokers)
      * [Getting data from an external data source (Barchart)](#getting-data-from-an-external-data-source-barchart)
   * [Roll calendars](#roll-calendars)
      * [Generate a roll calendar from actual futures prices](#generate-a-roll-calendar-from-actual-futures-prices)
         * [Calculate the roll calendar](#calculate-the-roll-calendar)
         * [Checks](#checks)
         * [Manually editing roll calendars](#manually-editing-roll-calendars)
      * [Roll calendars from existing 'multiple prices' .csv files](#roll-calendars-from-existing-multiple-prices-csv-files)
      * [Roll calendars shipped in .csv files](#roll-calendars-shipped-in-csv-files)
   * [Creating and storing multiple prices](#creating-and-storing-multiple-prices)
      * [Creating multiple prices from contract prices](#creating-multiple-prices-from-contract-prices)
      * [Writing multiple prices from .csv to database](#writing-multiple-prices-from-csv-to-database)
      * [Updating shipped multiple prices](#updating-shipped-multiple-prices)
   * [Creating and storing back adjusted prices](#creating-and-storing-back-adjusted-prices)
      * [Changing the stitching method](#changing-the-stitching-method)
   * [Getting and storing FX data](#getting-and-storing-fx-data)
   * [Finished!](#finished)
* [Part 2: Overview of futures data in pysystemtrade](#part-2-overview-of-futures-data-in-pysystemtrade)
   * [Hierarchy of data storage and access objects](#heirarchy-of-data-storage-and-access-objects)
   * [Directory structure (not the whole package! Just related to data objects, storage and interfaces)](#directory-structure-not-the-whole-package-just-related-to-data-objects-storage-and-interfaces)
* [Part 3: Storing and representing futures data](#part-3-storing-and-representing-futures-data)
   * [Futures data objects and their generic data storage objects](#futures-data-objects-and-their-generic-data-storage-objects)
      * [<a href="/sysobjects/instruments.py">Instruments</a>: futuresInstrument()](#instruments-futuresinstrument)
      * [<a href="/sysobjects/contract_dates_and_expiries.py">Contract dates and expiries</a>: singleContractDate(), contractDate(), listOfContractDateStr(), and expiryDate()](#contract-dates-and-expiries-singlecontractdate-contractdate-listofcontractdatestr-and-expirydate)
      * [<a href="/sysobjects/rolls.py">Roll cycles</a>: rollCycle()](#roll-cycles-rollcycle)
      * [<a href="/sysobjects/rolls.py">Roll parameters</a>: rollParameters()](#roll-parameters-rollparameters)
      * [<a href="/sysobjects/rolls.py">Contract date with roll parameters</a>: contractDateWithRollParameters()](#contract-date-with-roll-parameters-contractdatewithrollparameters)
      * [<a href="/sysobjects/contracts.py">Futures contracts</a>: futuresContract() and listOfFuturesContracts()](#futures-contracts-futurescontract-and-listoffuturescontracts)
      * [<a href="/sysobjects/futures_per_contract_prices.py">Prices for individual futures contracts</a>: futuresContractPrices(),  futuresContractFinalPrices()](#prices-for-individual-futures-contracts-futurescontractprices--futurescontractfinalprices)
      * [<a href="/sysobjects/dict_of_futures_per_contract_prices.py">Final prices for individual futures contracts</a>: dictFuturesContractFinalPrices(), dictFuturesContractVolumes(), dictFuturesContractPrices()](#final-prices-for-individual-futures-contracts-dictfuturescontractfinalprices-dictfuturescontractvolumes-dictfuturescontractprices)
      * [<a href="/sysobjects/dict_of_named_futures_per_contract_prices.py">Named futures contract dicts</a>: dictNamedFuturesContractFinalPrices, futuresNamedContractFinalPricesWithContractID, setOfNamedContracts, dictFuturesNamedContractFinalPricesWithContractID](#named-futures-contract-dicts-dictnamedfuturescontractfinalprices-futuresnamedcontractfinalpriceswithcontractid-setofnamedcontracts-dictfuturesnamedcontractfinalpriceswithcontractid)
      * [<a href="/sysobjects/roll_calendars.py">Roll calendars</a>: rollCalendar()](#roll-calendars-rollcalendar)
      * [<a href="/sysobjects/multiple_prices.py">Multiple prices</a>: futuresMultiplePrices()](#multiple-prices-futuresmultipleprices)
      * [<a href="/sysobjects/adjusted_prices.py">Adjusted prices</a>: futuresAdjustedPrices()](#adjusted-prices-futuresadjustedprices)
      * [<a href="/sysobjects/spot_fx_prices.py">Spot FX data</a>: fxPrices()](#spot-fx-data-fxprices)
   * [Data storage objects for specific sources](#data-storage-objects-for-specific-sources)
      * [.csv data files](#csv-data-files)
      * [mongo DB](#mongo-db)
         * [Specifying a mongoDB connection](#specifying-a-mongodb-connection)
      * [Arctic](#arctic)
         * [Specifying an arctic connection](#specifying-an-arctic-connection)
      * [Interactive Brokers](#interactive-brokers)
   * [Creating your own data storage objects for a new source](#creating-your-own-data-storage-objects-for-a-new-source)
* [Part 4: Interfaces](#part-4-interfaces)
   * [Data blobs](#data-blobs)
   * [simData objects](#simdata-objects)
      * [Provided simData objects](#provided-simdata-objects)
         * [<a href="/sysdata/sim/csv_futures_sim_data.py">csvFuturesSimData()</a>](#csvfuturessimdata)
         * [<a href="/sysdata/sim/db_futures_sim_data.py">dbFuturesSimData()</a>](#dbfuturessimdata)
         * [A note about multiple configuration files](#a-note-about-multiple-configuration-files)
      * [Modifying simData objects](#modifying-simdata-objects)
         * [Getting data from another source](#getting-data-from-another-source)
   * [Production interface](#production-interface)


Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)


<a name="futures_data_workflow"></a>
# Part 1: A futures data workflow

This section describes a typical workflow for setting up futures data from scratch, and setting up a mongoDB database full of the required data:

1. [Set up some static configuration information](#set_up_instrument_config) for instruments, and [roll parameters](#set_up_roll_parameter_config)
2. Get, and store, [some historical data](#get_historical_data)
3. Create, and store, [roll calendars](#roll_calendars)  (these are not actually used once multiple prices are created, so the storage is temporary)
4. Create and store ['multiple' price series](#create_multiple_prices) containing the relevant contracts we need for any given time period
5. Create and store [back-adjusted prices](#back_adjusted_prices): a single price series
6. Get, and store, [spot FX prices](#create_fx_data)

In general each step relies on the previous step to work; more formally:

- Roll parameters & Individual contract prices -> Roll calendars
- Roll calendars &  Individual contract prices -> Multiple prices
- Multiple prices -> Adjusted prices
- Instrument config, Adjusted prices, Multiple prices, Spot FX prices -> Simulation & Production data


## A note on data storage

Before we start, another note: Confusingly, data can be stored or come from various places, which include: 

1. .csv files containing data that pysystemtrade is shipped with (stored in [this set of directories](/data/futures/)). Any .csv data 'pipeline' object defaults to using this data set.
2. configuration .csv files used to initialise the system, such as [this file](/data/futures/csvconfig/spreadcosts.csv)
3. Temporary .csv files created in the process of initialising the databases
4. Backup .csv files, created by the production system.
5. External sources such as our broker, or data providers like Barchart and Quandl
6. Mongo DB or other databases

It's important to be clear where data is coming from, and where it is going to, during the initialisation process. Once we're actually running, the main storage will usually be in mongo DB (for production and possibly simulation).

For simulation we could just use the provided .csv files (1), and this is the default for how the backtesting part of pysystemtrade works, since you probably don't want to start down the road of building up your data stack before you've even tested out any ideas. I don't advise using .csv files for production - it won't work. As we'll see later, you can use mongoDB data for simulation and production.

Hence there are five possible use cases:

- You are happy to use the stale shipped .csv files data and are only backtesting. You don't need to do any of this!
- You want to update the .csv data used for backtests that is shipped with pysystemtrade
- You want to run backtests, but from faster databases rather than silly old .csv files, as I discuss how to do [later](#dbfuturessimdata)
- You want to run pysystemtrade in [production](/docs/production.md), which requires database storage.
- You want both database storage and updated .csv files, maybe because you want to keep a backup of your data in .csv (something that the production code does automatically, FWIW) or use that for backtesting

Because of this it's possible at (almost) every stage to store data in either .csv or databases (the exception are roll calendars, which only live in .csv format).


<a name="set_up_instrument_config"></a>
## Instrument configuration and spread costs

Instrument configuration consists of static information that enables us to trade an instrument like EDOLLAR: the asset class, futures contract point size, and traded currency (it also includes cost levels, that are required in the simulation environment). This is now mostly stored in [this file](/data/futures/csvconfig/instrumentconfig.csv) for both sim and production. The file includes a number of futures contracts that I don't actually trade or get prices for. Any configuration information for these may not be accurate and you use it at your own risk. The exception is spread costs, which are stored in [this file](/data/futures/csvconfig/spreadcosts.csv) for sim, but usually in a database for production, as they should be periodically updated with more accurate information.

To copy spread costs into the database we are going to *read* from .csv files, and *write* to a [Mongo Database](https://www.mongodb.com/). 

The relevant script to setup *information configuration* is in sysinit - the part of pysystemtrade used to initialise a new system. Here is the script you need to run [repocsv_spread_costs.py](/sysinit/futures/repocsv_spread_costs.py). 

Make sure you are running a [Mongo Database](#mongoDB) before running this.

The information is sucked out of [this file](/data/futures/csvconfig/spreadcosts.csv) and into the mongo database. 

<a name="set_up_roll_parameter_config"></a>
## Roll parameter configuration

*Roll configuration* is now stored in [a csv file](/data/futures/csvconfig/rollconfig.csv) for both sim and production.

It's worth explaining the available options for roll configuration. First of all we have two *roll cycles*: 'priced' and 'hold'. Roll cycles use the usual definition for futures months (January is F, February G, March H, and the rest of the year is JKMNQUVX, with December Z). The 'priced' contracts are those that we can get prices for, whereas the 'hold' cycle contracts are those we actually hold. We may hold all the priced contracts (like for equities), or only only some because of liquidity issues (eg Gold), or to keep a consistent seasonal position (i.e. CRUDE_W is Winter Crude, so we only hold December).

'RollOffsetDays': This indicates how many calendar days before a contract expires that we'd normally like to roll it. These vary from zero (Korean bonds KR3 and KR10 which you can't roll until the expiry date) up to -1100 (Eurodollar where I like to stay several years out on the curve).

'ExpiryOffset': How many days to shift the expiry date in a month, eg (the day of the month that a contract expires)-1. These values are just here so we can build roughly correct roll calendars (of which more later). In live trading you'd get the actual expiry date for each contract.

Using these two dates together will indicate when we'd ideally roll an instrument, relative to the first of the month.

For example for Bund futures, the ExpiryOffset is 6; the contract notionally expires on day 1+6 = 7th of the month. The RollOffsetDays is -5, so we roll 5 days before this. So we'd normally roll on the 1+6-5 = 2nd day of the month.

Let's take a more extreme example, Eurodollar. The ExpiryOffset is 18, and the roll offset is -1100 (no not a typo!). We'd roll this product 1100 days before it expired on the 19th day of the month.

<a name="carry-offset"></a>
'CarryOffset': Whether we take carry from an earlier dated contract (-1, which is preferable) or a later dated contract (+1, which isn't ideal but if we hold the front contract we have no choice). This calculation is done based on the *priced* roll cycle, so for example for winter crude where the *hold* roll cycle is just 'Z' (we hold December), and the carry offset is -1 we take the previous month in the *priced* roll cycle (which is a full year FGHJKMNQUVXZ) i.e. November (whose code is 'X'). You read more in Appendix B of [my first book](https://www.systematicmoney.org/systematic-trading).


<a name="get_historical_data"></a>
## Getting historical data for individual futures contracts

Now let's turn our attention to getting prices for individual futures contracts. 

This step is necessary if you're going to run production code or you want newer data, newer than the data that is shipped by default. If you just want to run backtests,  but with data in a database rather than .csv, and you're not bothered about using old data, you can skip ahead to [multiple prices](#mult_adj_csv_to_arctic).

### Getting data from the broker (Interactive brokers)

You can use [this script](/sysinit/futures/seed_price_data_from_IB.py) to get as much historical data as possible from Interactive Brokers. This will include expired contracts, but in any case will go back for a year of daily data. 

### Getting data from an external data source (Barchart)

OK, so we are limited in the historical data we can get from Interactive Brokers. What are the alternatives?

We could get this from anywhere, but I'm going to use Barchart. As you'll see, the code is quite adaptable to any kind of data source that produces .csv files. You could also use an API; in live trading we use the IB API to update our prices (Barchart also has an API but I don't support that). 

(Don't get data from both Barchart and IB. If you get the IB data first, the Barchart code will overwrite it. If you get the Barchart data first, the IB data won't be written.)

Once we have the data we can also store it, in principle, anywhere but I will be using the open source [Arctic library](https://github.com/manahl/arctic) which was released by my former employers [AHL](https://www.ahl.com). This sits on top of Mongo DB (so we don't need yet another database) but provides straightforward and fast storage of pandas DataFrames. Once we have the data we can also copy it to .csv files.

By the way I can't just pull down this data myself and put it on github to save you time. Storing large amounts of data in github isn't a good idea regardless of whether it is in .csv or Mongo files, and there would also be licensing issues with me basically just copying and pasting raw data that belongs to someone else. You have to get, and then store, this stuff yourself. And of course at some point in a live system you would be updating this yourself.

An easy way to bulk download data from [Barchart](https://www.barchart.com) is to create a Premier account, which allows for up to 250 data downloads per day, and to use [bc-utils](https://github.com/bug-or-feature/bc-utils). That project has a [guide for pysystemtrade users](https://github.com/bug-or-feature/bc-utils?tab=readme-ov-file#for-pysystemtrade-users).

Alternatively, if you are very patient, you can manually download the data from the Barchart historical data pages, such as [this one 
for Cotton #2](https://www.barchart.com/futures/quotes/KG*0/historical-download). 
Then, to read the data, you can use [this script](/sysinit/futures/barchart_futures_contract_prices.py), which in turn calls this [other more general script](/sysinit/futures/contract_prices_from_csv_to_arctic.py). Although it's very specific to Barchart, with some work you should be able to adapt it. You will need to call it with the directory where your Barchart .csv files are stored.

The script does two things:

1. Rename the files so they have the name expected
2. Read in the data from the Barchart files and write them into Arctic / Mongo DB.

Barchart data (when manually downloaded through the website) is saved with the file format: `XXMYY_Barchart_Interactive_Chart*.csv`
Where XX is the two character barchart instrument identifier, eg ZW is Wheat, M is the future contract month (F=January, G=February... Z =December), YY is the two digit year code, and the rest is fluff. The little function `strip_file_names` renames them so they have the expected format: `NNNN_YYYYMMDD.csv`, where NNNN is my instrument code (at least four letters and usually way more), and YYYYMM00 is a numeric date format eg 20201200 (the last two digits are notionally the days, but these are never used - I might need them if I trade weekly expiries at some point). If I was a real programmer, I'd probably have used perl or even a bash script to do this.

The next thing we do is define the internal format of the files, by setting `barchart_csv_config`:

```python
barchart_csv_config = ConfigCsvFuturesPrices(input_date_index_name="Date Time",
                                input_skiprows=1, input_skipfooter=1,
                                input_column_mapping=dict(OPEN='Open',
                                                          HIGH='High',
                                                          LOW='Low',
                                                          FINAL='Close',
                                                          VOLUME='Volume'
                                                          ))
```

Here we can see that the barchart files have one initial row we can ignore, and one final footer row we should also ignore. The second row contains the column names; of which the `Date Time` column includes our date time index. The column mapping shows how we can map between my preferred names (in caps) and those in the file. An unused option is the `input_date_format` which defaults to `%Y-%m-%d %H:%M:%S`. Changing these options should give you flexibility to read 99% of third party data files; for others you might have to write your own parser. 

The actual reading and writing is done here:

```python
def init_arctic_with_csv_futures_contract_prices_for_code(instrument_code: str, datapath: str,
                                                          csv_config=arg_not_supplied):
    print(instrument_code)
    csv_prices = csvFuturesContractPriceData(datapath, config=csv_config)
    arctic_prices = arcticFuturesContractPriceData()

    csv_price_dict = csv_prices.get_merged_prices_for_instrument(instrument_code)

    for contract_date_str, prices_for_contract in csv_price_dict.items():
        print(contract_date_str)
        contract = futuresContract(instrument_code, contract_date_str)
        arctic_prices.write_merged_prices_for_contract_object(contract, prices_for_contract, ignore_duplication=True)
```

The objects `csvFuturesContractPriceData` and `arcticFuturesContractPriceData` are 'data pipelines', which allow us to read and write a specific type of data (in this case OHLC price data for individual futures contracts). They have the same methods (and they inherit from a more generic object, futuresContractPriceData), which allows us to write code that abstracts the actual place and way the data is stored. We'll see much more of this kind of thing later.

<a name="roll_calendars"></a>
## Roll calendars

We're now ready to set up a *roll calendar*. A roll calendar is the series of dates on which we roll from one futures contract to the next. It might be helpful to read [my blog post](https://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html) on rolling futures contracts (though bear in mind some of the details relate to my original defunct trading system and do not reflect how pysystemtrade works).

You can see a roll calendar for Eurodollar futures, [here](/data/futures/roll_calendars_csv/EDOLLAR.csv). On each date we roll from the current_contract shown to the next_contract. We also see the current carry_contract; we use the differential between this and the current_contract to calculate forecasts for carry trading rules. The key thing is that on each roll date we *MUST* have prices for both the price and forward contract (we don't need carry). Here is a snippet from another roll calendar. This particular contract rolls quarterly on IMM dates (HMUZ), trades the first contract, and uses the second contract for carry. 

```
DATE_TIME,current_contract,next_contract,carry_contract
2020-02-28,20200300,20200600,20200600
2020-06-01,20200600,20200900,20200900
2020-08-31,20200900,20201200,20201200
```

- Before 28th February we are trading 202003 and using 20206 for carry
- Then on 28th February we roll into 202006. Between 28th February and 1st June we are trading 20206, and using 202009 for carry
- Then on 1st June we roll into 202009. Between 1st June and 31st August we are trading 202009, and using 202012 for carry.
- Then on 31st August we roll into 202012. After 31st August we are trading 202012 (it isn't shown, but we'd obviously use 202103 for carry)

There are three ways to generate roll calendars:

1. Generate a calendar based on [the individual contract data you have](#roll_calendars_from_approx). 
2. Infer the roll calendar from [existing 'multiple price' data](#roll_calendars_from_multiple). [Multiple price data](/data/futures/multiple_prices_csv) are data series that include the prices for three types of contract: the current, next, and carry contract (though of course there may be overlaps between these). pysystemtrade is shipped with .csv files for multiple and adjusted price data. Unless the multiple price data is right up to date, this may mean your rolls are a bit behind. 
3. Use the provided roll calendars, saved [here](/data/futures/roll_calendars_csv/). Again, these may be a bit behind. I generate these from multiple prices, so it's basically like step 2 except I've done the work for you.

Roll calendars are always saved as .csv files, which have the advantage of being readable and edited by human. So you can add extra rolls (if you've used method 2 or 3, and there would have been rolls since then) or do any manual hacking you need to get your multiple price data build to work. 

Once we have the roll calendar we can also adjust it so it is viable given the individual contract futures prices we have from the [previous stage](#get_historical_data). As an arbitrary example, you might assume you can roll 10 days before the expiry but that happens to be Thanksgiving so there are no prices available. The logic would find the closest date when you can actually trade. 

Then the roll calendar, plus the individual futures contract prices, can be used together to build multiple prices, from which we can get a single continuous backadjusted price series.

<a name="roll_calendars_from_approx"></a>
### Generate a roll calendar from actual futures prices

This is the method you'd use if you were really starting from scratch, and you'd just got some prices for each futures contract. The relevant script is [here](/sysinit/futures/rollcalendars_from_arcticprices_to_csv.py); you should call the function `build_and_write_roll_calendar`. It is only set up to run a single instrument at a time: creating roll calendars is careful craftsmanship, not suited to a batch process.

In this script (which you should run for each instrument in turn):

- We get prices for individual futures contract [from Arctic](#arcticFuturesContractPriceData) that we created in the [previous stage](#get_historical_data)
- We get roll parameters [from the csv file](#csvRollParametersData), that [we made earlier](#set_up_roll_parameter_config) 
- We calculate the roll calendar: 
`roll_calendar = rollCalendar.create_from_prices(dict_of_futures_contract_prices, roll_parameters)` based on the `ExpiryOffset` parameter stored in the instrument roll parameters we already setup. 
- We do some checks on the roll calendar, for monotonicity and validity (these checks will generate warnings if things go wrong)
- If we're happy with the roll calendar we [write](#csvRollCalendarData) our roll calendar into a csv file 

I strongly suggest putting an output datapath here; somewhere you can store temporary data. Otherwise you will overwrite the provided roll calendars [here](/data/futures/roll_calendars_csv/). OK, you can restore them with a git pull, but it's nice to be able to compare the 'official' and generated roll calendars.


#### Calculate the roll calendar
The actual code that generates the roll calendar is [here](/sysobjects/roll_calendars.py) which mostly calls code from [here](/sysinit/futures/build_roll_calendars.py):

The interesting part is:

```python
    @classmethod
    def create_from_prices(
        rollCalendar, dict_of_futures_contract_prices:dictFuturesContractFinalPrices,
            roll_parameters_object: rollParameters
    ):

        approx_calendar = generate_approximate_calendar(
            roll_parameters_object, dict_of_futures_contract_prices
        )

        adjusted_calendar = adjust_to_price_series(
            approx_calendar, dict_of_futures_contract_prices
        )

        roll_calendar = rollCalendar(adjusted_calendar)
```

So we first generate an approximate calendar, for when we'd ideally want to roll each of the contracts, based on our roll parameter `RollOffsetDays`. However we may find that there weren't *matching* prices for a given roll date. A matching price is when we have prices for both the current and next contract on the relevant day. If we don't have that, then we can't calculate an adjusted price. The *adjustment* stage finds the closest date to the ideal date (looking both forwards and backwards in time). If there are no dates with matching prices, then the process will return an error. You will need to either modify the roll parameters (maybe using the next rather than the previous contract), get some extra individual futures contract price data from somewhere, or manually add fake prices to your underlying futures contract prices to ensure some overlap (obviously this is cheating slightly, as without matching prices you have no way of knowing what the roll spread would have been in reality).


#### Checks

We then check that the roll calendar is monotonic and valid.

```python
    # checks - this might fail
    roll_calendar.check_if_date_index_monotonic()

    # this should never fail
    roll_calendar.check_dates_are_valid_for_prices(
        dict_of_futures_contract_prices
    )
```

A *monotonic* roll calendar will have increasing datestamps in the index. It's possible, if your data is messy, to get non-monotonic calendars. Unfortunately there is no automatic way to fix this, you need to dive in and rebuild the data (this is why I store the calendars as .csv files to make such hacking easy).

A *valid* roll calendar will have current and next contract prices on the roll date. Since when we created the calendar using individual prices we've already adjusted the roll calendars they should always pass this test (if we couldn't find a date when we have aligned prices then the calendar generation would have failed with an exception).


#### Manually editing roll calendars

Roll calendars are stored in .csv format [and here is an example](/data/futures/roll_calendars_csv/EDOLLAR.csv). Of course you could put these into Mongo DB, or Arctic, but I like the ability to hack them if required; plus we only use them when starting the system up from scratch. If you have to manually edit your .csv roll calendars, you can easily load them up and check they are monotonic and valid. The function [`check_saved_roll_calendar`](/sysinit/futures/rollcalendars_from_arcticprices_to_csv.py) is your friend. Just make sure you are using the right datapath.


<a name="roll_calendars_from_multiple"></a>
### Roll calendars from existing 'multiple prices' .csv files

In the next section we learn how to use roll calendars, and price data for individual contracts, to create DataFrames of *multiple prices*: the series of prices for the current, forward and carry contracts; as well as the identity of those contracts. But it's also possible to reverse this operation: work out roll calendars from multiple prices.

Of course you can only do this if you've already got these prices, which means you already need to have a roll calendar. A catch 22? Fortunately there are sets of multiple prices provided in pysystemtrade, and have been for some time, [here](/data/futures/multiple_prices_csv), which I built myself.

We run [this script](/sysinit/futures/rollcalendars_from_providedcsv_prices.py) which by default will loop over all the instruments for which we have data in the multiple prices directory, and output to a provided temporary directory. 

The downside is that I don't keep the data constantly updated, and thus you might be behind. For example, if you're trading quarterly with a hold cycle of HMUZ, and the data was last updated 6 months ago, there will probably have been one or two rolls since then. You will need to manually edit the calendars to add these extra rows (in theory you could generate these automatically - perhaps some kind person wants to write the code that will do this).


<a name="roll_calendars_from_provided"></a>
### Roll calendars shipped in .csv files

If you are too lazy even to do the previous step, I've done it for you and you can just use the calendars provided [here](/data/futures/roll_calendars_csv/EDOLLAR.csv). Of course they could also be out of date, and again you'll need to fix this manually.


<a name="create_multiple_prices"></a>
## Creating and storing multiple prices

The next stage is to create and store *multiple prices*. Multiple prices are the price and contract identifier for the current contract we're holding, the next contract we'll hold, and the carry contract we compare with the current contract for the carry trading rule. They are required for the next stage, calculating back-adjusted prices, but are also used directly by the carry trading rule in a backtest. Constructing them requires a roll calendar, and prices for individual futures contracts. You can see an example of multiple prices [here](/data/futures/multiple_prices_csv/AEX.csv). Obviously this is a .csv, but the internal representation of a dataframe will look pretty similar.


### Creating multiple prices from contract prices

The [relevant script is here](/sysinit/futures/multipleprices_from_db_prices_and_csv_calendars_to_db.py).

The script should be reasonably self explanatory in terms of data pipelines, but it's worth briefly reviewing what it does:

1. Get the roll calendars from `csv_roll_data_path` (which defaults to [this](/data/futures/roll_calendars_csv), so make sure you change it if you followed my advice to store your roll calendars somewhere else more temporary), which we have spent so much time and energy creating.
2. Get some closing prices for each individual future (we don't use OHLC data in the multiple and adjusted prices stage).
3. Optionally but recommended: adjust the roll calendar so it aligns to the closing prices. This isn't strictly necessary if you've used method 1 above, deriving the calendar from individual futures contract prices. But it is if you've used methods 2 or 3, and strongly advisable if you've done any manual hacking of the roll calendar files. 
4. Add a 'phantom' roll a week in the future. Otherwise the data won't be complete up the present day. This will fix itself the first time you run the live production code to update prices, but some people find it annoying.
5. Create the multiple prices; basically stitching together contract data for different roll periods. 
6. Depending on flags, write the multiple prices data to`csv_multiple_data_path` (which defaults to [this](/data/futures/multiple_prices_csv)) and / or to Arctic. I like to write to both: Arctic for production, .csv as a backup and sometimes I prefer to use that for backtesting.

Step 5 can sometimes throw up warnings or outright errors if things don't look right. Sometimes you can live with these, sometimes you are better off trying to fix them by changing your roll calendar. 99.9% of the time you will have had a problem with your roll calendar that you've ignored, so it's most likely because you haven't checked your roll calendar properly: make sure it's verified, monotonic, and adjusted to actual prices.


<a name="mult_adj_csv_to_arctic"></a>
### Writing multiple prices from .csv to database

The use case here is you are happy to use the shipped .csv data, even though it's probably out of date, but you want to use a database for backtesting. You don't want to try and find and upload individual futures prices, or create roll calendars.... the good news is you don't have to. Instead you can just use [this script](/sysinit/futures/multiple_and_adjusted_from_csv_to_arctic.py) which will just copy from .csv (default ['shipping' directory](/data/futures/multiple_prices_csv)) to Arctic.

This will also copy adjusted prices, so you can now skip ahead to [creating FX data](#create_fx_data).


<a name="update-shipped-data"></a>
### Updating shipped multiple prices

Assuming that you have an Interactive Brokers account, you might want to update the (stale) data that you have [downloaded from the repo](/docs/backtesting.md#setting-up-your-arctic-and-mongo-db-databases) before [calculating back adjusted prices](#back_adjusted_prices).

A first step is to [update the sampled contracts available](/docs/production.md#update-sampled-contracts-daily), and [their historical prices](/docs/production.md#update-futures-contract-historical-price-data-daily).  This might entail [manually checking](/docs/production.md#manual-check-of-futures-contract-historical-price-data) historical prices with spikes.

We'll then need to splice the new data onto the end of the repo data, with a few checks along the way.

*Nb: some of the repo multiple prices, particularly where the historical prices for mini contracts have been calculated from main-size contracts, have the [carry offset](#carry-offset) different to as per the [rollconfig.csv](/data/futures/csvconfig/rollconfig.csv).  If you use a carry trading rule you might want to check this is consistent (by temporarily altering the rollconfig.csv, for example)*

First we'll create some temporary working folders, then [build a roll calendar from the downloaded contract prices](#roll_calendars_from_approx):
```python
import os

roll_calendars_from_arctic = os.path.join('data', 'futures', 'roll_calendars_from_arctic')
if not os.path.exists(roll_calendars_from_arctic):
    os.makedirs(roll_calendars_from_arctic)

multiple_prices_from_arctic = os.path.join('data', 'futures', 'multiple_from_arctic')
if not os.path.exists(multiple_prices_from_arctic):
    os.makedirs(multiple_prices_from_arctic)

spliced_multiple_prices = os.path.join('data', 'futures', 'multiple_prices_csv_spliced')
if not os.path.exists(spliced_multiple_prices):
    os.makedirs(spliced_multiple_prices)

from sysinit.futures.rollcalendars_from_arcticprices_to_csv import build_and_write_roll_calendar
instrument_code = 'GAS_US_mini' # for example
build_and_write_roll_calendar(instrument_code, 
    output_datapath=roll_calendars_from_arctic)
```
We use our updated prices and the roll calendar just built to [calculate multiple prices](#/sysinit/futures/multipleprices_from_arcticprices_and_csv_calendars_to_arctic):

```python
from sysinit.futures.multipleprices_from_db_prices_and_csv_calendars_to_db import
    process_multiple_prices_single_instrument

process_multiple_prices_single_instrument(instrument_code,
                                          csv_multiple_data_path=multiple_prices_from_arctic, ADD_TO_ARCTIC=False,
                                          csv_roll_data_path=roll_calendars_from_arctic, ADD_TO_CSV=True)
```

...which we splice onto the repo data (checking that the price and forward contracts match):

```python
supplied_file = os.path.join('data', 'futures', 'multiple_prices_csv', instrument_code + '.csv') # repo data
generated_file = os.path.join(multiple_prices_from_arctic, instrument_code + '.csv')

import pandas as pd
supplied = pd.read_csv(supplied_file, index_col=0, parse_dates=True)
generated = pd.read_csv(generated_file, index_col=0, parse_dates=True)

# get final datetime of the supplied multiple_prices for this instrument
last_supplied = supplied.index[-1] 

print(f"last datetime of supplied prices {last_supplied}, first datetime of updated prices is {generated.index[0]}")

# assuming the latter is later than the former, truncate the generated data:
generated = generated.loc[last_supplied:]

# if first datetime in generated is the same as last datetime in repo, skip that row
first_generated = generated.index[0] 
if first_generated == last_supplied:
    generated = generated.iloc[1:]

# check we're using the same price and forward contracts (i.e. no rolls missing, which there shouldn't be if there is date overlap)
assert(supplied.iloc[-1].PRICE_CONTRACT == generated.loc[last_supplied:].iloc[0].PRICE_CONTRACT)
assert(supplied.iloc[-1].FORWARD_CONTRACT == generated.loc[last_supplied:].iloc[0].FORWARD_CONTRACT)
# nb we don't assert that the CARRY_CONTRACT is the same for supplied and generated, as some of the rolls implicit in the supplied multiple_prices don't match the pattern in the rollconfig.csv
```

...finally, we splice these multiple prices onto the repo's multiple prices and [save to Arctic](#mult_adj_csv_to_arctic):

```python
spliced = pd.concat([supplied, generated])
spliced.to_csv(os.path.join(spliced_multiple_prices, instrument_code+'.csv'))

from sysinit.futures.multiple_and_adjusted_from_csv_to_arctic import init_arctic_with_csv_prices_for_code
init_arctic_with_csv_prices_for_code(instrument_code, multiple_price_datapath=spliced_multiple_prices)
```

<a name="back_adjusted_prices"></a>
## Creating and storing back adjusted prices

Once we have multiple prices we can then create a backadjusted price series. The [relevant script](/sysinit/futures/adjustedprices_from_db_multiple_to_db.py) will read multiple prices from Arctic, do the backadjustment, and then write the prices to Arctic (and optionally to .csv if you want to use that for backup or simulation purposes). It's easy to modify this to read/write to/from different sources.


### Changing the stitching method

The default method for stitching the prices is 'panama' stitching. If you don't like panama stitching then you can modify the method. More details later in this document, [here](#futuresAdjustedPrices).


<a name="create_fx_data"></a>
## Getting and storing FX data

Although strictly not futures prices we also need spot FX prices to run our system (unless you are very dull, and have a USD account, and all of your futures are USD denominated. How do you survive with such an epically dull life? Never having to worry about sweeping your currency margin, or tracking error? I feel for you). The github for pysystemtrade contains spot FX data, but you will probably wish to update it. 

In live trading we'd use interactive brokers, but to get some backfilled data I'm going to use one of the many free data websites: [investing.com](https://www.investing.com)

You need to register with investing.com and then download enough history. To see how much FX data there already is in the .csv data provided:

```python
from sysdata.csv.csv_spot_fx import *
data=csvFxPricesData()
data.get_fx_prices("GBPUSD")
```

Save the files in a directory with no other content, using the filename format "GBPUSD.csv". Using [this simple script](/sysinit/futures/spotfx_from_csvAndInvestingDotCom_to_db.py) they are written to Arctic and/or .csv files. You will need to modify the script to point to the right directory, and you can also change the column and formatting parameters to use data from other sources.

You can also run the script with `ADD_EXTRA_DATA = False, ADD_TO_CSV = True`. Then it will just do a straight copy from provided .csv data to Arctic. Your data will be stale, but in production it will automatically be updated with data from IB (as long as the provided data isn't more than a year out of date, since IB will give you only a year of daily prices).


## Updating the data

If you want your data to update:

- [Ensure you are sampling all the contracts you want to sample](/docs/production.md#update-sampled-contracts-daily)
- [Update the individual contract data](/docs/production.md#update-futures-contract-historical-price-data-daily)
- [Update multiple and adjusted prices](/docs/production.md#update-multiple-and-adjusted-prices-daily)

These will be run daily if you're using the pysystemtrade production environment, and have set your [scheduler](/docs/production.md#scheduling) up to do `run_daily_price_updates`. But it's worth running them manually just the once (in the above order), especially after you've added data for a new market.


## Finished!

That's it. You've got all the price and configuration data you need to start live trading, or run backtests using the database rather than .csv files. The rest of the document goes into much more detail about how the data storage works in pysystemtrade.



<a name="Overview"></a>
# Part 2: Overview of futures data in pysystemtrade

The paradigm for data storage is that we have a bunch of [*data objects*](#generic_objects) for specific types of data used in both backtesting and simulation, i.e. `futuresInstrument` is the generic class for storing static information about instruments. [Another set](#production_data_objects) of data objects is only used in production.

Each of those data objects then has a matching *data storage object* which accesses data for that object, i.e. futuresInstrumentData. Then we have [specific instances of those for different data sources](#specific_data_storage), i.e. `csvFuturesInstrumentData` for storing instrument data in a csv file. 

I use [`dataBlob`s](/sysdata/data_blob.py) to access collections of data storage objects in both simulation and production. This also hides the exact source of the data and ensures that data objects are using a common database, logging method, and brokerage connection (since the broker is also accessed via data storage objects). More [later](#data_blobs).

To further hide the data, I use two kinds of additional interface which embed `dataBlob`s, one in backtesting and the other in production trading. For backtesting, data is accessed through the interface of `simData` objects (I discuss these [later](#simdata-objects)). These form part of the giant `System` objects that are used in backtesting ([as the `data` stage](backtesting.md#data)), and they provide the appropriate methods to get certain kinds of data which are needed for backtesting (some instrument configuration and cost data, spot FX, multiple, and adjusted prices). 

Finally in production I use the objects in [this module](/sysproduction/data) to act as [interfaces](#production_interface) between production code and data blobs, so that production code doesn't need to be too concerned about the exact implementation of the data storage. These also include some business logic. 

## Hierarchy of data storage and access objects

Generic data storage objects, used in both production and backtesting:

- `baseData`: Does basic logging. Has `__getitem__` and `keys()` methods so it looks sort of like a dictionary
    - `futuresAdjustedPricesData`
        - `csvFuturesAdjustedPricesData`
        - `arcticFuturesAdjustedPricesData`
    - `futuresContractData`
        - `csvFuturesContractData`
        - `ibFuturesContractData`
        - `mongoFuturesContractData`
    - `futuresContractPriceData`
        - `csvFuturesContractPriceData`
        - `ibFuturesContractPriceData`
        - `arcticFuturesContractPriceData`
    - `futuresInstrumentData`
        - `csvFuturesInstrumentData`
        - `ibFuturesInstrumentData`
    - `futuresMultiplePricesData`
        - `csvFuturesMultiplePricesData`
        - `arcticFuturesMultiplePricesData`
    - `rollCalendarData`
        - `csvRollCalendarData`
    - `rollParametersData`
        - `csvRollParametersData`
    - `fxPricesData`
        - `csvFxPricesData`
        - `arcticFxPricesData`
        - `ibFxPricesData`

Production only data storage objects:

- `baseData`: Does basic logging. Has `__getitem__` and `keys()` methods so it looks sort of like a dictionary
    - `listOfEntriesData`: generic 'point in time' data used for capital and positions
        - `mongoListOfEntriesData`
        - `strategyCapitalData`
            - `mongocapitalData`
        - `strategyPositionData`
            - `mongoStrategyPositionData`
        - `contractPositionData`
            - `mongoContractPositionData`
        - `optimalPositionData`
            - `mongoOptimalPositionData`
    - `genericOrdersData`
        - `mongoGenericHistoricOrdersData`
        - `strategyHistoricOrdersData`
            - `mongoStrategyHistoricOrdersData`
        - `contractHistoricOrdersData`
            - `mongoContractHistoricOrdersData`
            - `mongoBrokerHistoricOrdersData`
    - `lockData`
        - `mongoLockData`
    - `overrideData`
        - `mongoOverrideData`
    - `positionLimitData`
        - `mongoPositionLimitData`
    - `controlProcessData`
        - `mongoControlProcessData`
    - `rollStateData`
        - `mongoRollStateData`
    - `tradeLimitData`
        - `mongoTradeLimitData`
    - `emailControlData`
        - `mongoEmailControlData`
    - `orderStackData`
        - `mongoOrderStackData`
        - `brokerOrderStackData`
            - `mongoBrokerOrderStackData`
        - `contractOrderStackData`
            - `mongoContractOrderStackData`
        - `brokerOrderStackData`
            - `mongoBrokerOrderStackData`

    
Specific data sources

- Mongo / Arctic
    - `mongoDb`: Connection to a database (arctic or mongo) specifying port, databasename and hostname. Usually created by a `dataBlob`, and the instance is used to create various `mongoConnection`
    - `mongoConnection`: Creates a connection (combination of database and specific collection) that is created inside object like `mongoPositionLimitData`, using a `mongoDb`
    - `mongoData`: Provides a common abstract interface to mongo, assuming the data is in dicts. Has different classes for single or multiple keys.
    - `arcticData`: Provides a common abstract interface to arctic, assuming the data is passed as pd.DataFrame
- Interactive brokers: see [this file](/docs/IB.md)


Data collection and abstraction:

- `dataBlob`: Holds collection of data storage objects, whose names are abstracted to hide the source


Simulation interface layer:

- [baseData](/sysdata/base_data.py): Does basic logging. Has __getitem__ and keys() methods so it looks sort of like a dictionary
    - [simData](/sysdata/sim/sim_data.py): Can be plugged into a backtesting system object, provides expected API methods to run backtests
        - [futuresSimData](/sysdata/sim/futures_sim_data.py): Adds methods specifically for futures
            - [genericBlobUsingFuturesSimData](/sysdata/sim/futures_sim_data_with_data_blob.py): Provides API methods for backtesting once a data blob has been passed in
                - [csvFuturesSimData](/sysdata/sim/csv_futures_sim_data.py): Access to sim data in .csv files
                - [dbFuturesSimData](/sysdata/sim/db_futures_sim_data.py): Access to sim data in arctic / mongodb files

    
## Directory structure (not the whole package! Just related to data objects, storage and interfaces)

- [/sysbrokers/IB/](/sysbrokers/IB/): IB specific data storage / access objects
- [/syscontrol/](/syscontrol/): Process control data objects
- [/sysdata/](/sysdata/): Generic data storage objects and dataBlobs 
    - [/sysdata/futures/](/sysdata/futures/): Data storage objects for futures (backtesting and production), including execution and logging
    - [/sysdata/production/](/sysdata/production/): Data storage objects for production only 
    - [/sysdata/fx/](/sysdata/fx/): Data storage object for spot FX
    - [/sysdata/mongodb/](/sysdata/mongodb/): Data storage objects, mongo specific
    - [/sysdata/arctic/](/sysdata/arctic/): Data storage objects, Arctic specific
    - [/sysdata/csv/](/sysdata/csv/): Data storage objects, csv specific
    - [/sysdata/sim/](/sysdata/sim/): Backtesting interface layer
- [/sysexecution/](/sysexecution/): Order and order stack data objects
- [/sysobjects/](/sysobjects/): Most production and generic (backtesting and production) data objects live here
- [/sysproduction/data/](/sysproduction/data/): Production interface layer



<a name="storing_futures_data"></a>
# Part 3: Storing and representing futures data

<a name="generic_objects"></a>
## Futures data objects and their generic data storage objects

<a name="futuresInstrument"></a>
### [Instruments](/sysobjects/instruments.py): futuresInstrument() 

Futures instruments are the things we actually trade, eg Eurodollar futures, but not specific contracts. Apart from the instrument code we can store *metadata* about them. This isn't hard wired into the class, but currently includes things like the asset class, cost parameters, and so on.

<a name="contractDate"></a>
### [Contract dates and expiries](/sysobjects/contract_dates_and_expiries.py): singleContractDate(), contractDate(), listOfContractDateStr(), and expiryDate()

Note: There is no data storage for contract dates, they are stored only as part of [futures contracts](#futuresContracts).

A contract date allows us to identify a specific [futures contract](#futuresContracts) for a given [instrument](#futuresInstrument). Futures contracts can either be for a specific month (eg '201709') or for a specific day (eg '20170903'). The latter is required to support weekly futures contracts, or if we already know the exact expiry date of a given contract. A monthly date will be represented with trailing zeros, eg '20170900'.

A contract date is made up of one or more singleContractDate. Depending on the context, it can make sense to have multiple contract dates. For example, if we're using it to refer to a multi leg intra-market spread there would be multiple dates.

The 'yyyymmdd' representation of a contractDate is known as a date string (no explicit class). A list of these is a listOfContractDateStr().

We can also store expiry dates expiryDate() in contract dates. This can be done either by passing the exact date (which we'd do if we were getting the contract specs from our broker) or an approximate expiry offset, where 0 (the default) means the expiry is on day 1 of the relevant contract month.

<a name="rollCycle"></a>
### [Roll cycles](/sysobjects/rolls.py): rollCycle()

Note: There is no data storage for roll cycles, they are stored only as part of [roll parameters](#rollParameters).

Roll cycles are the mechanism by which we know how to move forwards and backwards between contracts as they expire, or when working out carry trading rule forecasts. Roll cycles use the usual definition for futures months (January is F, February G, March H, and the rest of the year is JKMNQUVX, with December Z). 

<a name="rollParameters"></a>
### [Roll parameters](/sysobjects/rolls.py): rollParameters()

The roll parameters include all the information we need about how a given instrument rolls:

- `hold_rollcycle` and `priced_rollcycle`. The 'priced' contracts are those that we can get prices for, whereas the 'hold' cycle contracts are those we actually hold. We may hold all the priced contracts (like for equities), or only only some because of liquidity issues (eg Gold), or to keep a consistent seasonal position (i.e. CRUDE_W is Winter Crude, so we only hold December).
- `roll_offset_day`: This indicates how many calendar days before a contract expires that we'd normally like to roll it. These vary from zero (Korean bonds KR3 and KR10 which you can't roll until the expiry date) up to -1100 (Eurodollar where I like to stay several years out on the curve).
- `carry_offset`: Whether we take carry from an earlier dated contract (-1, which is preferable) or a later dated contract (+1, which isn't ideal but if we hold the front contract we have no choice). This calculation is done based on the *priced* roll cycle, so for example for winter crude where the *hold* roll cycle is just 'Z' (we hold December), and the carry offset is -1 we take the previous month in the *priced* roll cycle (which is a full year FGHJKMNQUVXZ) i.e. November (whose code is 'X'). You read more in Appendix B of [my first book](https://www.systematicmoney.org/systematic-trading) and in [my blog post](https://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html).
- `approx_expiry_offset`: How many days to shift the expiry date in a month, eg (the day of the month that a contract expires)-1. These values are just here so we can build roughly correct roll calendars (of which more later). In live trading you'd get the actual expiry date for each contract.

<a name="contractDateWithRollParameters"></a>
### [Contract date with roll parameters](/sysobjects/rolls.py): contractDateWithRollParameters()

Combining a contract date with some roll parameters means we can answer important questions like, what is the next (or previous) contract in the priced (or held) roll cycle? What is the contract I should compare this contract to when calculating carry? On what date would I want to roll this contract?

<a name="listOfFuturesContracts"></a>
<a name="futuresContracts"></a>
### [Futures contracts](/sysobjects/contracts.py): futuresContract() and listOfFuturesContracts()


The combination of a specific [instrument](#futuresInstrument) and a [contract date](#contractDate) is a `futuresContract`. 

`listOfFuturesContracts`: This dull class exists purely so we can generate a series of historical contracts from some roll parameters.

<a name="futuresContractPrices"></a>
### [Prices for individual futures contracts](/sysobjects/futures_per_contract_prices.py): futuresContractPrices(),  futuresContractFinalPrices()

The price data for a given contract is just stored as a DataFrame with specific column names. Notice that we store Open, High, Low, and Final prices; but currently in the rest of pysystemtrade we effectively throw away everything except Final.

A 'final' price is either a close or a settlement price depending on how the data has been parsed from it's underlying source. There is no data storage required for these since we don't need to store them separately, just extract them from either `futuresContractPrices` or `dictFuturesContractPrices` objects.


`dictFuturesContractPrices`: When calculating roll calendars we work with prices from multiple contracts at once.

<a name="futuresContractDictPrices"></a>
### [Final prices for individual futures contracts](/sysobjects/dict_of_futures_per_contract_prices.py): dictFuturesContractFinalPrices(), dictFuturesContractVolumes(), dictFuturesContractPrices()

All these dicts have the contract date string as the key (eg `20201200`), and a dataframe like object as the value.

### [Named futures contract dicts](/sysobjects/dict_of_named_futures_per_contract_prices.py): dictNamedFuturesContractFinalPrices, futuresNamedContractFinalPricesWithContractID, setOfNamedContracts, dictFuturesNamedContractFinalPricesWithContractID
 
'Named' contracts are those we are currently trading (priced), the next contract(forward), and the carry contract.

`dictNamedFuturesContractFinalPrices`: keys are PRICE,CARRY,FORWARD; values are `futuresContractFinalPrices`
`setOfNamedContracts`: A dictionary, keys are PRICE,CARRY,FORWARD; values are date strings for each contract eg '20201200'
`futuresNamedContractFinalPricesWithContractID`: Dataframe like object, two columns, one for price, one for contract as a date string eg '20201200'
`dictFuturesNamedContractFinalPricesWithContractID`: keys are PRICE,CARRY,FORWARD; values are `futuresNamedContractFinalPricesWithContractID`


<a name="rollCalendar"></a>
### [Roll calendars](/sysobjects/roll_calendars.py): rollCalendar() 

A roll calendar is a pandas DataFrame with columns for: 

- current_contract
- next_contract
- carry_contract

Each row shows when we'd roll from holding current_contract (and using carry_contract) on to next_contract. As discussed [earlier](#roll_calendars) they can be created from a set of [roll parameters](#rollParameters) and [price data](#futuresContractPrices), or inferred from existing [multiple price data](#futuresMultiplePrices).

<a name="futuresMultiplePrices"></a>
### [Multiple prices](/sysobjects/multiple_prices.py): futuresMultiplePrices() 

A multiple prices object is a pandas DataFrame with columns for:PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD, and FORWARD_CONTRACT. 

We'd normally create these from scratch using a roll calendar, and some individual futures contract prices (as discussed [here](#create_multiple_prices)). Once created they can be stored and reloaded.


<a name="futuresAdjustedPrices"></a>
### [Adjusted prices](/sysobjects/adjusted_prices.py): futuresAdjustedPrices()

The representation of adjusted prices is boring beyond words; they are a pandas Series. More interesting is the fact you can create one with a back adjustment process given a [multiple prices object](#futuresMultiplePrices):

```python
from sysobjects.adjusted_prices import futuresAdjustedPrices
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData

# assuming we have some multiple prices
arctic_multiple_prices = arcticFuturesMultiplePricesData()
multiple_prices = arctic_multiple_prices.get_multiple_prices("EDOLLAR")

adjusted_prices = futuresAdjustedPrices.stitch_multiple_prices(multiple_prices)
```

The adjustment defaults to the panama method. If you want to use your own stitching method then override the method `futuresAdjustedPrices.stitch_multiple_prices`.


<a name="fxPrices"></a>
### [Spot FX data](/sysobjects/spot_fx_prices.py): fxPrices()

Technically bugger all to do with futures, but implemented in pysystemtrade as it's required for position scaling.


<a name="specific_data_storage"></a>
## Data storage objects for specific sources

This section covers the various sources for reading and writing [data objects](#storing_futures_data) I've implemented in pysystemtrade. 

### .csv data files

Storing data in .csv files has some obvious disadvantages, and doesn't feel like the sort of thing a 21st century trading system ought to be doing. However it's good for roll calendars, which sometimes need manual hacking when they're created. It's also good for the data required to run backtests that lives as part of the github repo for pysystemtrade (storing large binary files in git is not a great idea, although various workarounds exist I haven't yet found one that works satisfactorily).

For obvious (?) reasons we only implement get and read methods for .csv files (So... you want to delete the .csv file? Do it through the filesystem. Don't get python to do your dirty work for you).


<a name="mongoDB"></a>
### mongo DB

For production code, and storing large amounts of data (eg for individual futures contracts) we probably need something more robust than .csv files. [MongoDB](https://mongodb.com) is a no-sql database which is rather fashionable at the moment, though the main reason I selected it for this purpose is that it is used by [Arctic](#arctic). 

Obviously you will need to make sure you already have a Mongo DB instance running. You might find you already have one running, in Linux use `ps wuax | grep mongo` and then kill the relevant process.

Personally I like to keep my Mongo data in a specific subdirectory; that is achieved by starting up with `mongod --dbpath ~/data/mongodb/` (in Linux). Of course this isn't compulsory.

#### Specifying a mongoDB connection

You need to specify an IP address (host), and database name when you connect to MongoDB. These are set with the following priority:

- Firstly, arguments passed to a `mongoDb()` instance, which is then optionally passed to any data object with the argument `mongo_db=mongoDb(mongo_host='localhost', mongo_database_name='production', mongo_port = 27017)` All arguments are optional. 
- Then, variables set in the private `.yaml` configuration file /private/private_config.yaml: mongo_host, mongo_db, mongo_port
- Finally, default arguments in the [system defaults configuration file](/sysdata/config/defaults.yaml): mongo_host, mongo_db, mongo_port

Note that `localhost` is equivalent to `127.0.0.1`, i.e. this machine. Note also that if you have a non-standard mongo port, you must use the url format for specifying the mongo host, eg

```mongo_host: mongodb://username:p4zzw0rd@localhost:28018```

If your mongoDB is running on your local machine then you can stick with the defaults (assuming you are happy with the database name `production`). If you have different requirements, eg mongo running on another machine or you want a different database name, then you should set them in the private .yaml file. If you have highly bespoke needs, eg you want to use a different database or different host for different types of data, then you will need to add code like this:

```python
# Instead of:
adj_data=arcticFuturesAdjustedPricesData()

# Do this
from sysdata.mongodb import mongoDb
adj_data=arcticFuturesAdjustedPricesData(mongo_db = mongoDb(mongo_database_name='another database')) # could also change host
```

<a name="arctic"></a>
### Arctic 

[Arctic](https://github.com/manahl/arctic) is a superb open source time series database which sits on top of [Mongo DB](#mongoDB) and provides straightforward and fast storage of pandas DataFrames. It was created by my former colleagues at [Man AHL](https://www.ahl.com) (in fact I beta tested a very early version of Arctic whilst I was still working there), and then very generously released as open source. You don't need to run multiple instances of Mongo DB when using my data objects for Mongo DB and Arctic, they use the same one. 

Basically my mongo DB objects are for storing static information, whilst Arctic is for time series.

Arctic has several *storage engines*, in my code I use the default VersionStore.

#### Specifying an arctic connection

You need to specify an IP address (host), and database name when you connect to Arctic. Arctic data objects will default to using the same settings as Mongo data objects.


```python
# Instead of:
afcpdata=arcticFuturesContractPriceData()

# Do this (could also be done by passing another mongo connection to dataBlob)
from sysdata.mongodb import mongoDb
afcpdata=arcticFuturesContractPriceData(mongo_db = mongoDb(database_name='another database')) # could also change host
```


### Interactive Brokers

We don't use IB as a data store, but we do implement certain data storage methods to get futures and FX price data, as well as providing an interface to production layer services like creating orders and getting fills. 

See [here](/docs/IB.md) for more information.


## Creating your own data storage objects for a new source

Creating your own data storage objects is trivial, assuming they are for an existing kind of data object. 

They should live in a subdirectory of [sysdata](/sysdata), named for the data source i.e. [sysdata/arctic](/sysdata/arctic).

Look at an existing data storage object for a different source to see which methods you'd need to implement, and to see the generic data storage object you should inherit from. Normally you'd need to override all the methods in the generic object which return `NotImplementedError`; the exception is if you have a read-only source like Quandl, or if you're working with .csv or similar files in which case I wouldn't recommend implementing delete methods.

Use the naming convention `sourceNameOfObjectData`, i.e. `class arcticFuturesContractPriceData(futuresContractPriceData)`. They must be prefixed with the source, and suffixed with Data. And they must be camel cased in the middle.

**YOU MUST DO THIS OR THE `dataBlob` RENAMING WILL NOT WORK!!** `dataBlob` renames `sourceSomethingInCamelCaseData` to `db_something_in_camel_case`. If you add another source you'll need to add that to the dataBlob resolution dictionary.

For databases you may want to create connection objects (like [this](/sysdata/arctic/arctic_connection.py) for Arctic) which abstract the database implementation to a set of simple read/write/update/delete methods.



<a name="interfaces"></a>
# Part 4: Interfaces

This section of the file describes various interfaces to different data storage objects: `dataBlobs`, `simData`, and the production data interface layer.

For simulation:

- Data storage objects (eg `arcticFuturesContractPriceData`)
- ... live inside `dataBlob`s
- ... are accessed by `simData` object
- ... which live inside backtesting `System`s

And for production:

- Data storage objects (eg `arcticFuturesContractPriceData`)
- ... live inside `dataBlob`s
- ... are accessed by production data interfaces
- ... which are called by production code



<a name="data_blobs"></a>
## Data blobs

What is a data blob? Let's create one:

```python
from sysdata.data_blob import dataBlob
data = dataBlob()
data

dataBlob with elements: 
```

Let's suppose we wanted to get adjusted price data from arctic. Then we'd do this:


```python
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
data.add_class_object(arcticFuturesAdjustedPricesData)
Library created, but couldn't enable sharding: ...

data.db_futures_adjusted_prices.get_list_of_instruments()
['EDOLLAR', 'CAC', 'KR3', 'SMI', 'V2X', 'JPY', ....]
```

OK, why does it say `db_futures_adjusted_prices` here? It's because dataBlob knows we don't really care where our data is stored. It dynamically creates an instance of any valid data storage class that is passed to it, renaming it by replacing the source with `db` (or `broker` if it's an interface to the broker), stripping off the 'Data' at the end, and replacing the CamelCase in the middle with `_` separated strings (since this is an instance now not a class).

(In fact a further layer of abstraction is achieved by the use of interface objects in backtesting or production, so you'd not normally write code that directly accessed the method of a data object, even one that is renamed. These interfaces all have data blobs as attributes. More on these below.) 

Let's suppose we wanted to access the futures adjusted price data from csv files. Then:

```python
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData
data.add_class_list([csvFuturesAdjustedPricesData]) # see we can pass a list of classes, although this list is quite short.

2020-11-30:1535.48 {'type': ''} [Warning] No datapaths provided for .csv, will use defaults  (may break in production, should be fine in sim)

data.db_futures_adjusted_prices.get_list_of_instruments()
['EDOLLAR', 'CAC', 'KR3', 'SMI', 'V2X', 'JPY', ....]
```

A .csv is just another type of database as far as dataBlob is concerned. It's replaced the attribute we had before with a new one that now links to .csv files. 

Here's a quick whistle-stop tour of dataBlob's other features:


- you can create it with a starting class list by passing the `parameter class_list=...`
- it includes a `log` attribute that is passed to create data storage instances (you can override this by passing in a logger via the `log=` parameter when dataBlob is created), the log will have top level type attribute as defined by the log_name parameter
- when required it creates a `mongoDb` instance that is passed to create data storage instances (you can override this by passing in a `mongoDb` instance via the `mongo_db=` parameter when dataBlob is created)
- when required it creates a `connectionIB` instance that is passed to create data storage instances (you can override this by passing in a connection instance via the `ib_conn=` parameter when dataBlob is created)
- The parameter `csv_data_paths` will allow you to use different .csv data paths, not the defaults. The dict should have the keys of the class names, and values will be the paths to use.
- Setting `keep_original_prefix=True` will prevent the source renaming. Thus `add_class_list([csvFuturesAdjustedPricesData])` will create a method `csv_futures_adjusted_prices`, and `add_class_object(arcticFuturesAdjustedPricesData)` will create `arctic_futures_adjusted_prices`. This is useful if you're copying from one type of data to another.

<a name="simData_objects"></a>
## simData objects

The `simData` object is a compulsory part of the pysystemtrade system object which runs simulations (or in live trading generates desired positions). The API required for that is laid out in the user guide, [here](/docs/backtesting.md#using-the-standard-data-objects). It's an interface between the contents of a dataBlob, and the simulation code.

This modularity allows us to easily replace the data objects, so we could load our adjusted prices from mongo DB, or do 'back adjustment' of futures prices 'on the fly'.

For futures simData objects need to know the source of:

- back adjusted prices
- multiple price data
- spot FX prices
- instrument configuration and cost information

Direct access to other kinds of information isn't necessary for simulations.

### Provided simData objects

I've provided two complete simData objects which get their data from different sources: [csvSimData](#csvSimData) and [mongoSimData](#mongoSimData). 

<a name="csvFuturesSimData"></a>
#### [csvFuturesSimData()](/sysdata/sim/csv_futures_sim_data.py)

The simplest simData object gets all of its data from .csv files, making it ideal for simulations if you haven't built a process yet to get your own data. 

<a name="mongoSimData"></a>
#### [dbFuturesSimData()](/sysdata/sim/db_futures_sim_data.py)

This is a simData object which gets it's data out of Mongo DB (static) and Arctic (time series). 

Because the mongoDB data isn't included in the github repo, before using this you need to write the required data into Mongo and Arctic.
You can do this from scratch, as per the ['futures data workflow'](#a-futures-data-workflow) at the start of this document:

- [Setting up spread cost data](#instrument-configuration-and-spread-costs)
- [Adjusted prices](#creating-and-storing-back-adjusted-prices)
- [Multiple prices](#creating-and-storing-multiple-prices)
- [Spot FX prices](#create_fx_data)

Alternatively you can run the following scripts which will copy the data from the existing github .csv files:

- [Spread cost data](/sysinit/futures/repocsv_spread_costs.py)
- [Adjusted prices](/sysinit/futures/repocsv_adjusted_prices.py)
- [Multiple prices](/sysinit/futures/repocsv_multiple_prices.py)
- [Spot FX prices](/sysinit/futures/repocsv_spotfx_prices.py)

Of course it's also possible to mix these two methods. Once you have the data it's just a matter of replacing the default csv data object:

```python
from systems.provided.futures_chapter15.basesystem import futures_system
from sysdata.sim.db_futures_sim_data import dbFuturesSimData
system = futures_system(data = dbFuturesSimData())
print(system.data.get_instrument_list())
```
#### A note about multiple configuration files

Configuration information about futures instruments is stored in a number of different places:

- Instrument configuration and cost levels in [instrumentconfig.csv](/data/futures/csvconfig/instrumentconfig.csv) and [spreadcosts.csv](/data/futures/csvconfig/spreadcosts.csv)
- Roll configuration information in [this .csv file](/data/futures/csvconfig/rollconfig.csv)
- Interactive brokers configuration in [this file](/sysbrokers/IB/config/ib_config_spot_FX.csv) and [this file](/sysbrokers/IB/config/ib_config_futures.csv).

The instruments in these lists won't necessarily match up, however under the principle of DRY there shouldn't be duplicated column headings across files.

The `system.get_instrument_list()` method is used by the simulation to decide which markets to trade; if no explicit list of instruments is included then it will fall back on the method `system.data.get_instrument_list()`. In both the provided simData objects this will resolve to the method `get_instrument_list` in the class which gets back adjusted prices, or in whatever overrides it for a given data source (.csv or Mongo DB). In practice this means it's okay if your instrument configuration (or roll configuration, when used) is a superset of the instruments you have adjusted prices for. But it's not okay if you have adjusted prices for an instrument, but no configuration information.

<a name="modify_SimData"></a>
### Modifying simData objects

Constructing simData objects in the way I've done makes it relatively easy to modify them. Here are a few examples.

#### Getting data from another source

Let's suppose you want to use Arctic and Mongo DB data, but get your spot FX prices from a .csv file in a custom directory. OK this is a silly example, but hopefully it will be easy to generalise this to doing more sensible things. Modify the file [db_futures_sim_data.py](/sysdata/sim/db_futures_sim_data.py):

```python
# add import
from sysdata.csv.csv_spot_fx import csvFxPricesData

# replace this class: class  dbFuturesSimData()
# with:


class dbFuturesSimData2(genericBlobUsingFuturesSimData):
    def __init__(self, data: dataBlob = arg_not_supplied,
                 log =get_logger("dbFuturesSimData")):

        if data is arg_not_supplied:
            data = dataBlob(log = log,
                              class_list=[arcticFuturesAdjustedPricesData, arcticFuturesMultiplePricesData,
                         csvFxPricesData, csvFuturesInstrumentData], csv_data_paths = {'csvFxPricesData': 'some_path'})

        super().__init__(data=data)

    def __repr__(self):
        return "dbFuturesSimData object with %d instruments" % len(
            self.get_instrument_list())


>>> system = futures_system(data = dbFuturesSimData2())
>>> system.data.data.db_futures_multiple_prices

simData connection for multiple futures prices, arctic production/futures_multiple_prices @ 127.0.0.1 

>>> system.data.data.db_fx_prices

csvFxPricesData accessing data.futures.fx_prices_csv

```


<a name="production_interface"></a>
## Production interface

In production I use the objects in [this module](/sysproduction/data) to act as interfaces between production code and data blobs, so that production code doesn't need to be too concerned about the exact implementation of the data storage. These also include some business logic. 

`diag` classes are read only, `update` are write only, `data` are read/write (created because it's not worth creating a separate read and write class):
- `dataBacktest`: read/write pickled backtests from production `run_systems`
- `dataBroker`: interact with broker
- `dataCapital`: read/write total and strategy capital
- `diagContracts`, `updateContracts`: read/write information about individual futures contracts
- `dataLocks`: read/write information on locks (temporarily preventing instrument from trading because of position level conflict)
- `diagOverrides`, `updateOverrides`: read/write information about overrides (cut position size or prevent positions from increasing)
- `dataControlProcess`, `diagProcessConfig`: control starting and stopping of production processes
- `dataPositionLimits`: read/write position limits 
- `dataTradeLimits`: read/write limits on individual trades
- `diagInstruments`: get configuration for instruments
- `dataOrders`: read/write historic orders and order 'stacks' (current orders)
- `diagPositions`, `updatePositions`: Read/Write historic and current positions
- `dataOptimalPositions`: Read/Write optimal position data
- `diagPrices`, `updatePrices`: Read/Write futures price data (adjusted, multiple, per contract)
- `dataCurrency`: Read/write FX data and do currency conversions
- `dataSimData`: Create a simData object to be used by production backtests
- `diagStrategiesConfig`: Configuration data for strategies (capital allocation, backtest configuration, order generator...)
- `diagVolumes`: volume data





