"""
Get some data to test the handcrafting method
"""

from sysdata.csv.csv_sim_futures_data import csvFuturesSimData
from syscore.handcrafting import Portfolio
import pandas as pd

data=csvFuturesSimData()
code_list = ['BOBL', 'BUND', 'US10', 'US20', 'KR3','KR10','EDOLLAR', 'CORN', 'CRUDE_W', 'GAS_US']

def calc_weekly_return(instrument_code, start_date=pd.datetime(2014,1,1)):
    price = data[instrument_code]
    price=price[start_date:]
    weekly_price = price.resample("W").last()
    denom_price = data.get_instrument_raw_carry_data(instrument_code).PRICE
    denom_weekly_price = denom_price.resample("W").last()

    weekly_returns = (weekly_price - weekly_price.shift(1))/denom_weekly_price

    return weekly_returns[start_date:]


returns = dict([(instrument_code, calc_weekly_return(instrument_code)) for instrument_code in code_list])
returns = pd.DataFrame(returns)

p=Portfolio(returns, risk_target=.1)
