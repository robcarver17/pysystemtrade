from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from datetime import datetime
import time


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def historicalData(self, reqId, bar):
        print(
            f"Time: {bar.date}, Open: {bar.open}, High: {bar.high}, Low: {bar.low}, Close: {bar.close}, Volume: {bar.volume}")


def run_loop():
    app.run()


app = IBapi()
app.connect('127.0.0.1', 4001, 123)
app.nextOrderId = 0

# Start the socket in a thread
import threading

thread = threading.Thread(target=run_loop, daemon=True)
thread.start()
# Sleep interval to allow time for connection to server
time.sleep(1)

# Create contract object
forex_contract = Contract()
forex_contract.symbol = 'EUR'
forex_contract.secType = 'CASH'
forex_contract.exchange = 'IDEALPRO'
forex_contract.currency = 'USD'

# Request historical candles
app.reqHistoricalData(1, forex_contract, '', '1 D', '1 hour', 'MIDPOINT', 1, 1, False, [])

time.sleep(5)  # sleep to allow enough time for data to be returned
app.disconnect()
