This document is specifically about using pysystemtrade to connect with *Interactive Brokers (IB)*

As of version 0.28.0, this requires the [ib_insync](https://github.com/erdewit/ib_insync) library.

Although this document is about Interactive Brokers, you should read it carefully if you plan to use other brokers as it explains how to modify the various classes to achieve that, or perhaps if you want to use an alternative python layer to talk to the IB API


- Get spot FX price data

Related documents:

- [Storing futures and spot FX data](/docs/data.md)
- [Using pysystemtrade as a production trading environment](/docs/production.md)
- [Using pysystemtrade for backtesting](/docs/backtesting.md)

*IMPORTANT: Make sure you know what you are doing. All financial trading offers the possibility of loss. Leveraged trading, such as futures trading, may result in you losing all your money, and still owing more. Backtested results are no guarantee of future performance. No warranty is offered or implied for this software. I can take no responsibility for any losses caused by live trading using pysystemtrade. Use at your own risk.*


Table of Contents
=================

* [Preliminaries](#preliminaries)
   * [Getting started with interactive brokers](#getting-started-with-interactive-brokers)
      * [Gateway / TWS](#gateway--tws)
      * [IB-insync library](#ib-insync-library)
      * [IBC](#ibc)
   * [Launching and configuring the Gateway](#launching-and-configuring-the-gateway)
   * [Making a connection](#making-a-connection)
* [Reference](#reference)
   * [Classes and object references](#classes-and-object-references)
   * [Data source objects](#data-source-objects)
      * [FX Data](#fx-data)
      * [Futures price data](#futures-price-data)
      * [Capital data](#capital-data)
      * [Contracts data](#contracts-data)
      * [Instruments data](#instruments-data)
      * [Orders data](#orders-data)
      * [Position data](#position-data)
   * [Client objects](#client-objects)
   * [Connection objects](#connection-objects)
      * [Creating and closing connection objects](#creating-and-closing-connection-objects)
      * [Using connections](#using-connections)
      * [Make multiple connections](#make-multiple-connections)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)


# Preliminaries

## Getting started with interactive brokers

You may want to read [my blog posts](https://qoppac.blogspot.com/2017/03/interactive-brokers-native-python-api.html) to understand more about what is going on if it's your first experience of IB's python API. For any issues with IB go to [this group](https://groups.io/g/twsapi). IB also have a [webinar](https://register.gotowebinar.com/register/5481173598715649281) for the API. The official manual for the IB API is [here](http://interactivebrokers.github.io/tws-api/introduction.html) and for IB insync is [here](https://ib-insync.readthedocs.io/api.html).

### Gateway / TWS

You need to download either the gateway or TWS software from the IB website. I recommend using the Gateway as it is much more stable and lightweight, and does not regularly reboot itself.


### IB-insync library

I use IB-insync as my API to the python Gateway. You will need the [ib_insync](https://github.com/erdewit/ib_insync) library. This does not require you to download the IB python code.

It is worth running the examples in the [IB-insync cookbook](https://ib-insync.readthedocs.io/api.html) to make sure your IB connection is working, that you have the right gateway settings, and so on. Pysystemtrade obviously won't work if IB insync can't work!!


### IBC

Many people find [ibcAlpha](https://github.com/IbcAlpha/IBC) is very useful. It will maintain an open IB Gateway session to avoid the pain of having to manually restart every day. This is particularly useful if you're running your system fully automated on a headless trading server.


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
from sysbrokers.IB.ib_connection import connectionIB
conn = connectionIB( 999, ib_ipaddress = "127.0.0.1", ib_port=4001, account="U999999") # the first compulsory value is the client_id; the keyword args are the default values and can be omitted
conn
# In production the client id is assigned from a database to avoid conflicts
Out[13]: IB broker connection{'ipaddress': '127.0.0.1', 'port': 4001, 'client': 999} 

```

See [here](#creating-and-closing-connection-objects) for more details.




<a name="futures_data_workflow"></a>
# Reference

## Classes and object references


There are three types of objects in the [sysbrokers/IB](/sysbrokers/IB/) area of pysystemtrade:

- Data source objects: Provide the standard data object API to the rest of the code, eg getting futures contracts prices is done with the same call whether they are coming from a database or IB. They are called by the `/sysproduction/data/broker/` [interface functions](/docs/data.md#production-interface). They are instanced with a *connection object*. They make calls to *client objects*. 
- Client objects: These make calls to the ib_insync in specific domains (getting data, placing orders and so on). They are also instanced with a *connection object*.
- Connection objects. These contain a specific connection to an IB gateway via an ib_insync IB instance.


## Data source objects

We treat IB as another data source, which means it has to conform to the data object API (see [storing futures and spot FX data](/docs/data.md)). However we can't delete or write to IB.  Normally these functions would be called by the `/sysproduction/data/broker/` [interface functions](/docs/data.md#production-interface); it's discouraged to call them directly as the interface abstracts away exactly which broker you are talking to.

The data source objects all inherit from the classes in the `sysbrokers/` directory, eg `broker*data.py`. This serves a few purposes: it means we can add additional non specific IB methods that only make sense when talking to a broker rather than to a database, and it illustrates the interface you'd need to implement to connect to a different broker.
Data source objects are instanced with and contain a *connection object* (and optionally a logger). They contain, and make calls to, *client objects*. They are in this [module](/sysbrokers/IB/)

You can access the client object and connection used by a particular data source, for example:

```
from sysbrokers.IB.ib_orders_data import ibOrdersData
ib_orders_data = ibOrdersData(conn)
ib_orders_data.ib_client
ib_orders_data.ibconnection
```


### FX Data

```
from sysbrokers.IB.ib_Fx_prices_data import ibFxPricesData
from sysdata.data_blob import dataBlob
ibfxpricedata = ibFxPricesData(conn, dataBlob())

ibfxpricedata.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFX.csv
ibfxpricedata.get_fx_prices("GBPUSD") # returns fxPrices object
```



### Futures price data


```
from sysobjects.contracts import futuresContract
from sysbrokers.IB.ib_futures_contract_price_data import ibFuturesContractPriceData
from sysdata.data_blob import dataBlob
ibfuturesdata = ibFuturesContractPriceData(conn, dataBlob())

ibfuturesdata.get_list_of_instrument_codes_with_merged_price_data() # returns list of instruments defined in [futures config file](/sysbrokers/IB/ibConfigFutures.csv)
ibfuturesdata.contract_dates_with_price_data_for_instrument_code("EDOLLAR") # returns list of contract dates
ibfuturesdata.get_prices_for_contract_object(futuresContract("EDOLLAR", "201203")) # returns OHLC price and volume data
```

### Capital data

```
from sysbrokers.IB.ib_capital_data import ibCapitalData
ib_capital_data = ibCapitalData(conn)

ib_capital_data.get_account_value_across_currency()
```


### Contracts data

```
from sysobjects.contracts import futuresContract
contract = futuresContract("EDOLLAR", "202306")

from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
ib_futures_contract_data = ibFuturesContractData(conn)
ib_futures_contract_data.get_contract_object_with_IB_data(contract) # this is used by a lot of other functions as a first step before eg placing an order or getting a price
ib_futures_contract_data.get_actual_expiry_date_for_single_contract(contract)
ib_futures_contract_data.get_min_tick_size_for_contract(contract)
ib_futures_contract_data.get_trading_hours_for_contract(contract)
```


### Instruments data

```
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
ib_futures_instrument_data = ibFuturesInstrumentData(conn)
ib_futures_instrument_data.get_list_of_instruments()
ib_futures_instrument_data.get_futures_instrument_object_with_IB_data("EDOLLAR") # again used by other functions to get the 'metadata' to map into IB instruments
ib_futures_instrument_data.get_brokers_instrument_code("EDOLLAR") # reverse of next function
ib_futures_instrument_data.get_instrument_code_from_broker_contract_object("GE") # reverse of previous function
```


### Orders data

```
from sysbrokers.IB.ib_orders import ibExecutionStackData
ib_orders_data = ibExecutionStackData(conn)

ib_orders_data.get_list_of_broker_orders_with_account_id() # Get the list of orders that the broker has executed in the last 24 hours
ib_orders_data.get_list_of_orders_from_storage() # Get the list of orders that this instance has exected
ib_orders_data.put_order_on_stack(broker_order) # this will actually trade! It returns an orderWithControls: a broker order that contains the dynamic IB order object 
ib_orders_data.match_db_broker_order_to_order_from_brokers(broker_order) # Useful to see if an order has been filled for example
ib_orders_data.match_db_broker_order_to_control_order_from_brokers(broker_order) # Sometimes it's easier to get the control object back after matching
ib_orders_data.cancel_order_on_stack(broker_order)  # sends a cancellation message...
ib_orders_data.check_order_is_cancelled(broker_order)  # ... check if it's worked
ib_orders_data.check_order_is_cancelled_given_control_object(broker_order_with_controls)   # same but for an order with a control object (easier as don't have to match)
ib_orders_data.check_order_can_be_modified_given_control_object(broker_order_with_controls) 
ib_orders_data.modify_limit_price_given_control_object(broker_order_with_controls) 
```


### Position data

```
from sysbrokers.IB.ib_contract_position_data import ibContractPositionData
ib_contract_position_data = ibContractPositionData(conn)
ib_contract_position_data.get_all_current_positions_as_list_with_contract_objects()
```



## Client objects

Client objects make calls and requests to the broker via ib_insync. They are usually initialised by a broker data source object, which passes them a connection (and optionally a log).

They are located in this [module](/sysbrokers/IB/client/). They are tied together with a weird inheritance tree:

- base ibClient
   - ibAccountingClient(ibClient)
   - ibPositionsClient(ibClient)
   - ibContractsClient(ibClient)
      - ibOrdersClient(ibContractsClient)
      - ibPriceClient(ibContractsClient)
         - ibFxClient(ibPriceClient)
 

Client objects also contain a connection and the live ib_inysnc.IB instance which is actually used by the client object code:

```
from sysbrokers.IB.client.ib_price_client import ibPriceClient
ib_price_client = ibPriceClient()
ib_price_client.ib_connection # connection
ib_price_client.ib # live ib_inysnc.IB instance
```


## Connection objects

You wouldn't normally open a separate IB connection in pysystemtrade since they are opened by the [dataBlob](/docs/data.md#data-blobs) objects used in production. But it's useful to know how they work under the hood.

### Creating and closing connection objects

```
from sysbrokers.IB.ib_connection import connectionIB
conn = connectionIB(1, ib_ipaddress = "127.0.0.1", ib_port=4001, account="U123456")
```

Portid should match that in the Gateway configuration. Client ids (eg 1) must not be duplicated by an already connected python process (even if it's hung... normally in production the client id is assigned from a database to avoid conflicts). The IP address shown means 'this machine'; only change this if you are planning to run the Gateway on a different network machine.

If values for account, ib_ipaddress and ib_port are not passed here, they will default to:

1- values supplied in file 'private_config.yaml' (see below)
2- values supplied in the ['defaults.yaml' file](/sysdata/config/defaults.yaml)

You should first create a file 'private_config.yaml' in the private directory of [pysystemtrade](#/private). Then add one or more of these line:

```
ib_ipaddress: 192.168.0.10
ib_port: 4001
broker_account: U123456
```

```
conn = connectionIB(config)
```

Connection objects immediately try and connect to IB. So don't create them until you are ready to do this. 


Again in production the connection would normally be closed by the [dataBlob](/docs/data.md#data-blobs) object that encapsulates the connection, or you can do it manually with  `conn.close_connection()`.

### Using connections

We treat IB as another data source, which means it has to conform to the data object API (see [storing futures and spot FX data](/docs/data.md)). Since connection objects abstract what the broker is doing, it should be possible to use these object for other brokers with minimal changes.

The main service the connection provides is that it encapsulates a live ib_inysnc.IB instance:

```
conn.ib
```

You can use this directly if you are familiar with ib_insync eg `conn.ib.positions()`, but normally this would be used by the IB client objects.


### Make multiple connections

It's possible to have multiple connections to the IB Gateway, each from its own process, but each connection must have a unique clientid. Used clientids are stored in the active database (usually mongoDB) to ensure we don't re-use active clientids. 




