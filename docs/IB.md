This document is specifically about using pysystemtrade to connect with [*Interactive Brokers (IB)*](https://www.interactivebrokers.com/).

As of version 0.28.0, this requires the [ib_insync](https://github.com/erdewit/ib_insync) library.

Although this document is about Interactive Brokers, you should read it carefully if you plan to use other brokers as it explains how to modify the various classes to achieve that, or perhaps if you want to use an alternative python layer to talk to the IB API


- Get spot FX price data

Related documents:

- [Storing futures and spot FX data](/docs/futures.md)
- [Using pysystemtrade as a production trading environment](/docs/production.md)
- [Main user guide](/docs/userguide.md)

*IMPORTANT: Make sure you know what you are doing. All financial trading offers the possibility of loss. Leveraged trading, such as futures trading, may result in you losing all your money, and still owing more. Backtested results are no guarantee of future performance. No warranty is offered or implied for this software. I can take no responsibility for any losses caused by live trading using pysystemtrade. Use at your own risk.*

Table of Contents
=================

   * [Quick start](#quick-start)
      * [Getting started with interactive brokers](#getting-started-with-interactive-brokers)
         * [Gateway / TWS](#gateway--tws)
         * [Python library](#python-library)
      * [Launching and configuring the Gateway](#launching-and-configuring-the-gateway)
      * [Making a connection](#making-a-connection)
      * [Get some data](#get-some-data)
   * [How to...](#how-to)
      * [Connections](#connections)
         * [Creating and closing connection objects](#creating-and-closing-connection-objects)
         * [Make multiple connections](#make-multiple-connections)
      * [Deal with errors](#deal-with-errors)
      * [Get spot FX prices](#get-spot-fx-prices)
   * [Reference](#reference)
      * [Classes and object references](#classes-and-object-references)
         * [Client objects](#client-objects)
            * [Generic client object](#generic-client-object)
            * [IB client object](#ib-client-object)
         * [Server objects](#server-objects)
            * [Generic server object](#generic-server-object)
            * [IB server object](#ib-server-object)
         * [Connection objects](#connection-objects)
         * [Data source objects](#data-source-objects)
            * [Spot FX](#spot-fx)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)

# Quick start

## Getting started with interactive brokers

You may want to read [my blog posts](https://qoppac.blogspot.com/2017/03/interactive-brokers-native-python-api.html) to understand more about what is going on if it's your first experience of IB's python API. For any issues with IB go to [this group](https://groups.io/g/twsapi). IB also have a [webinar](https://register.gotowebinar.com/register/5481173598715649281) for the API. The official manual for the IB API is [here](http://interactivebrokers.github.io/tws-api/introduction.html) and for IB insync is [here](https://ib-insync.readthedocs.io/api.html).

### Gateway / TWS

You need to download either the gateway or TWS software from the IB website. I recommend using the Gateway as it is much more stable and lightweight, and does not regularly reboot itself.

These links may break or become outdated - use google to find the appropriate page on IB's website.

[For Windows](https://www.interactivebrokers.co.uk/en/index.php?f=1341)

[For Linux](https://www.interactivebrokers.co.uk/en/index.php?f=16454)


### Python library

You also need the python library for IB. This can be downloaded from [here](https://interactivebrokers.github.io/#). Once you have the source code you will need to install it. Here's the Linux way:

```
cd ~/IBJts/source/pythonclient
python3 setup.py install
```

The directory required may vary, and you might need to prefix the second command with `sudo`. Windows users should do whatever they normally do to install python packages.

## Launching and configuring the Gateway

Before you run any python code you'll need to launch the Gateway software. Current versions of the Gateway do this via a desktop icon. You will need to use either:

- A demo account, such as username: `fdemo`, password: `demouser`. IB seem to be phasing out their demo accounts.
- A paper trading account
- A live trading account (*Make sure you know what you are doing. I can take no responsibility for any losses caused by live trading using pysystemtrade. Use at your own risk!!!*)

You will also need to configure the Gateway:

- Socket port: Should be 4001. If you use a different port you'll need to change your connection calls [here](#making-a-connection) and [here](#creating-and-closing-connection-objects)
- White list for trusted IP addresses: Should include 127.0.0.1. If you are going to be running the Gateway on one machine, and accessing it via another, then you need to add the IP address of your other machines here.
- If you are going to be trading, then 'Read only API' should be turned off
- You may also need to change precautions and preset options

## Making a connection

```
from sysbrokers.IB.ibConnection import  connectionIB
conn = connectionIB(ipaddress = "127.0.0.1", port=4001) # these are the default values and can be omitted
conn

Out[13]: IB broker connection{'ipaddress': '127.0.0.1', 'port': 4001, 'client': 1} # client id may be different

```

See [here](#creating-and-closing-connection-objects) for more details.


# How to...

## Deal with connections

### Creating and closing connection objects

```
from sysbrokers.IB.ibConnection import connectionIB
conn = connectionIB(ipaddress = "127.0.0.1", port=4001) # these are the default values and can be ommitted
```

Portid should match that in the Gateway configuration. Client ids must not be duplicated by an already connected python process (even if it's hung...). The IP address shown means 'this machine'; only change this if you are planning to run the Gateway on a different network machine.

If values for ipaddress and port are not passed here, they will default to:

1- values supplied in file 'private_config.yaml' (see below)
2- default hardcoded values

You should first create a file 'private_config.yaml' in the private directory of [pysystemtrade](#/private). Then add one or both of these line:

```
ib_ipaddress: 192.168.0.10
ib_port: 4001
```

```
conn = connectionIB(config)
```

Connection objects immediately try and connect to IB. So don't create them until you are ready to do this. Once you have a connection object that exists in a particular Python process, do not try and create a new one. I've also had problems closing connections and then trying to create a new connection object. Generally it is safer to stick to the pattern of creating a single connection object in each process, attempting to close it out of politeness with `conn.disconnnect()`, and then terminating the process.

### Make multiple connections

It's possible to have multiple connections to the IB Gateway, each from it's own process, but each connection must have a unique clientid. Used clientid's are stored in a the active database (usually mongoDB) to ensure we don't re-use active clientids.

## Deal with errors

The IB and broker objects don't raise exceptions caused by IB reported errors, or any issues, but they do log them. Generally the pattern is for a call to a client method to return an empty object, which the calling function can decide how to deal with.


## Data

We treat IB as another data source, which means it has to conform to the data object API (see [storing futures and spot FX data](/docs/futures.md)). However we can't delete or write to IB.

### FX Data

```
from sysbrokers.IB.ibSpotFXData import ibFxPricesData
ibfxpricedata = ibFxPricesData(conn)

ibfxpricedata.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFX.csv
ibfxpricedata.get_fx_prices("GBPUSD") # returns fxPrices object
```



## Futures data


```
from sysbrokers.IB.ibFuturesContractPriceData import ibFuturesContractPriceData
ibfuturesdata = ibFuturesContractPriceData(conn)

ibfuturesdata.get_instruments_with_price_data() # returns list of instruments defined in [futures config file](/sysbrokers/IB/ibConfigFutures.csv)
ibfuturesdata.contract_dates_with_price_data_for_instrument_code("EDOLLAR") # returns list of contract dates
ibfuturesdata.get_prices_for_instrument_code_and_contract_date("EDOLLAR", "201203") # returns futuresContractPrices
ibfuturesdata.get_prices_for_contract_object(futuresContract("EDOLLAR", "201203")) # equivalent, allows us to pass richer contract objects eg if we know expiry date
```


<a name="futures_data_workflow"></a>
# Reference

## Classes and object references

There are four types of objects in the [sysbrokers](/sysbrokers/) area of pysystemtrade:

- Client objects,
- Server objects
- Connection objects
- Data source objects

### Client objects

Client objects make calls and requests to the broker.

#### Generic client object

The generic client object, [`brokerClient`](/sysbrokers/baseClient.py), contains a series of methods which need to be overriden to do anything useful.

These methods include:

- `broker_get_daily_fx_data`: Returns a pd.Series of fx data
- `broker_get_historical_futures_data_for_contract`: Returns a pd.Series of futures data, given a contract definition. The contract definition can be "YYYMM" or "YYYYMMDD" if the exact expiry date is known.
- `broker_get_futures_contract_list`: For a given instrument, returns a list of "YYYMMDD" contract ID's which are the expiry dates of the given contracts
- `broker_get_contract_expiry_date`: For a given instrument, return "YYYMMDD" which is the expiry dates of the given contract.

All methods are prefixed with `broker_` to eliminate the chances of a conflict with the brokers own methods.


#### IB client object

The IB client object, [`ibClient`](/sysbrokers/IB/ibClient.py), inherits from `brokerClient`. It overrides the methods in `brokerClient`, and also contains any further methods required to interact with the IB Gateway to implement the `brokerClient` methods. All such methods are prefixed with `ib_` to distinguish them from `broker_` methods, and to reduce the chances of a conflict.

The overriden methods are:

- `broker_get_fx_data`: Returns a pd.Series of fx data given a currency pair definition
- `broker_get_historical_futures_data_for_contract`: Returns a pd.Series of futures data, given a contract definition (including broker metadata added by the ibFuturesContractPriceData layer). The contract definition can be "YYYMM" or "YYYYMMDD" if the exact expiry date is known.
- `broker_get_futures_contract_list`: For a given instrument (including metadata), returns a list of "YYYMMDD" contract ID's which are the expiry dates of the given contracts
- `broker_get_contract_expiry_date`: For a given instrument (including metadata), return "YYYMMDD" which is the expiry dates of the given contract.


The extra methods include:

- `__init__`: Does the weird magical stuff required to get an IB client operating, and initialises the log, and request ID factory.
- `ib_init_request_id_factory`, `ib_next_req_id`, `ib_clear_req_id`: make sure request ID's are parcelled out and shared nicely
- `ib_spotfx_contract`, `ib_futures_contract`, `ib_resolve_futures_contract`: Translate pysystemtrade depictions of an instrument into IB objects
- `ib_resolve_contract`, `ib_get_contract_chain`: Called by individual resolve methods, to go to IB and ensure we have the 'full' IB object.
- `ib_get_historical_data`: Called by specific methods to get historical data

If you are going to connect to a new broker, then your main job is to ensure that you provide working methods to override those in `brokerClient`.


### Server objects

Server objects handle data and messages coming back from the broker.

#### Generic server object

The generic server object, [`brokerServer`](/sysbrokers/baseServer.py) is very lightweight, and only contains methods for error capturing. We do not act on any errors, instead they are passed back to the client objects.

These methods include:

- `broker_get_error`: Read the latest error from the queue
- `broker_is_error`: True if any errors waiting to be read
- `broker_error`: Log, and add an error to the queue of errors. Future versions may handle specific errors.
- `broker_msg`: Log a broker message

All methods are prefixed with `broker_` to reduce the chances of a conflict with the brokers own code.

#### IB server object

The IB server object, [`ibServer`](/sysbrokers/IB/ibServer.py), inherits from `brokerServer` and from the IB `EWrapper`. It overrides the following `EWrapper` methods:

- `error`: Error report. Calls `broker_error` in `brokerServer` to handle the error
- `contractDetails`, `contractDetailsEnd`: Receive contract details
- `historicalData`, `historicalDataEnd`: Receive historical data

It also includes functions to help manage the queues which store data coming from IB to be passed to the client:

- `__init__`: Adds a log, and initialises dictionaries required for error handling
- `error_handler`: Error handler. Needs to be added to the underlying ib_insync object (this is done by the connection object)

### Connection objects

A connection object inherits from both a client and a server (NOTE: in the future we would need to add a database connection object to receive streamed prices, fills etc).

No generic connection object is provided, since they are likely to be highly bespoke to a particular broker. See [connectionIB](/sysbrokers/IB/ibConnection.py) for an example. At a minimum, connection objects must do the following:

- Logging: `def __init__(self, ..., log=logtoscreen())`. This also helpful: `log.label(broker="IB")`
- Init the client and server objects, passing the log through
- Connect to the broker
- Allow a disconnection to the broker

Importantly the connection object will include methods that are inherited from [`brokerClient`](/sysbrokers/baseClient.py) and overriden in [`ibClient`](/sysbrokers/IB/ibClient.py). These are the main 'externally facing' methods.

### Data source objects

We treat IB as another data source, which means it has to conform to the data object API (see [storing futures and spot FX data](/docs/futures.md)). Since connection objects abstract what the broker is doing, it should be possible to use these object for other brokers with minimal changes.

#### Spot FX

For spot FX we have a class `ibFxPricesData` which inherits from the generic `fxPricesData`. This needs to be initialised with an IB connection:


```python
from sysbrokers.IB.ibSpotFXData import ibFxPricesData
ibfxpricedata = ibFxPricesData(conn)
ibfxpricedata.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFX.csv
ibfxpricedata.get_fx_prices("GBPUSD") # returns fxPrices object
```

This is a 'read only' object; there are no methods implemented for writing or deleting FX data.

#### Futures contract prices data

For spot FX we have a class `ibFuturesContractPricesData` which inherits from the generic `futuresContractPriceData`. This needs to be initialised with an IB connection:


```python
from sysbrokers.IB.ibFuturesContractPricesData import ibFuturesContractPricesData
ibfutpricedata = ibFuturesContractPricesData(conn)
ibfutpricedata.get_instruments_with_price_data()  # codes must be in .csv file /sysbrokers/IB/ibConfigFutures.csv
ibfutpricedata.get_prices_for_instrument_code_and_contract_date("SP500", "202006")
```

This is a 'read only' object; there are no methods implemented for writing or deleting data.
