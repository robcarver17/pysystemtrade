import matplotlib

matplotlib.use("TkAgg")
"""

Work up a minimum example of a trend following system

"""

# Get some data

from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

""""
Let's get some data

We can get data from various places; however for now we're going to use
prepackaged 'legacy' data stored in csv files
"""

data = csvFuturesSimData()

print(data)
"""
We get stuff out of data with methods
"""
print(data.get_instrument_list())
print(data.get_raw_price("EDOLLAR").tail(5))
"""
data can also behave in a dict like manner (though it's not a dict)
"""

print(data["VIX"])
print(data.keys())

"""
Not all the instruments are easily identifiable
"""

print(data.get_instrument_object_with_meta_data("MUMMY"))


"""

... however this will only access prices
(note these prices have already been backadjusted for rolls)

We have extra futures data here

"""

print(data.get_instrument_raw_carry_data("EDOLLAR").tail(6))
"""
Technical note: csvFuturesSimData inherits from FuturesData which itself inherits
from simData
The chain is 'data specific' <- 'asset class specific' <- 'generic'

Let's create a simple trading rule

No capping or scaling
"""

from sysquant.estimators.vol import robust_vol_calc


def calc_ewmac_forecast(price, Lfast, Lslow=None):
    """
    Calculate the ewmac trading rule forecast, given a price and EWMA speeds
    Lfast, Lslow and vol_lookback

    """
    # price: This is the stitched price series
    # We can't use the price of the contract we're trading, or the volatility
    # will be jumpy
    # And we'll miss out on the rolldown. See
    # https://qoppac.blogspot.com/2015/05/systems-building-futures-rolling.html

    price = price.resample("1B").last()

    if Lslow is None:
        Lslow = 4 * Lfast

    # We don't need to calculate the decay parameter, just use the span
    # directly
    fast_ewma = price.ewm(span=Lfast).mean()
    slow_ewma = price.ewm(span=Lslow).mean()
    raw_ewmac = fast_ewma - slow_ewma

    vol = robust_vol_calc(price.diff())
    return raw_ewmac / vol


"""
Try it out

(this isn't properly scaled at this stage of course)
"""
instrument_code = "VIX"
price = data.daily_prices(instrument_code)
ewmac = calc_ewmac_forecast(price, 32, 128)
ewmac2 = calc_ewmac_forecast(price, 16, 64)

ewmac.columns = ["forecast"]
print(ewmac.tail(5))

from matplotlib.pyplot import show

ewmac.plot()
show()
"""
Did we make money?
"""

from systems.accounts.account_forecast import pandl_for_instrument_forecast

account = pandl_for_instrument_forecast(forecast=ewmac, price=price)
account2 = pandl_for_instrument_forecast(forecast=ewmac, price=price)

account.curve()

account.curve().plot()
show()

print(account.percent.stats())
