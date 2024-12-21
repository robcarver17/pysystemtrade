from sysbrokers.IB.ib_capital_data import ibCapitalData
from sysdata.data_blob import dataBlob
from sysdata.sim.db_futures_sim_data import dbFuturesSimData

if __name__ == '__main__':

    # Note: 1. IB in_sync
    # # 1. Make connection
    # from ib_insync import *
    # ib = IB()
    # ib.connect('127.0.0.1', 7497, clientId=1)
    #
    # # 2.2 FUTURES
    #
    # # 2. Define the futures contract
    # mxp_future = Future(symbol='MXP', lastTradeDateOrContractMonth='202503', exchange='CME', currency='USD')
    #
    # # 3. Request historical data
    # bars = ib.reqHistoricalData(
    #     mxp_future,
    #     endDateTime='',
    #     durationStr='30 D',  # Adjust duration (e.g., '30 D' for 30 days)
    #     barSizeSetting='1 day',  # Adjust bar size (e.g., '1 hour', '1 day')
    #     whatToShow='TRADES',  # Can be 'TRADES', 'BID', 'ASK', etc.
    #     useRTH=True  # Set to False to include outside regular trading hours
    # )
    #
    # # 4. Convert to DataFrame and print
    # df = util.df(bars)
    # print(df)
    #
    # # 3.1 Ge tick data
    # ticker = ib.reqMktData(mxp_future)
    # # 4. Wait for market data to populate
    # ib.sleep(2)  # Give it a couple of seconds to fetch data
    # # 5. Print current data
    # print(f"Last Price: {ticker.last}")
    # print(f"Bid Price: {ticker.bid}")
    # print(f"Ask Price: {ticker.ask}")
    # print(f"Volume: {ticker.volume}")

    # Note 2: From Sysbrokers
    from sysbrokers.IB.ib_connection import connectionIB
    conn = connectionIB(client_id=1)
    print(conn)
