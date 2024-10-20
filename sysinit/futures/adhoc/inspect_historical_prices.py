import matplotlib
import pandas as pd
from matplotlib import pyplot as plt

from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.mongodb.mongo_connection import mongoDb

mongo_db = mongoDb()
arctic_historical_prices = arcticFuturesContractPriceData(mongo_db=mongo_db)

hist_prices = arctic_historical_prices.get_all_prices_for_instrument("LUMBER")

prices_final = hist_prices.final_prices()
prices_final_as_pd = pd.concat(prices_final, axis=1)

# print(prices_final_as_pd['1998-01-01':'1998-12-31'].to_string())
# exit(0)

# Inspect prices
prices_final_as_pd.plot()
matplotlib.use('TkAgg')
plt.show()

# Inspect % change
perc = prices_final_as_pd.diff()/prices_final_as_pd.shift(1)
perc.plot()
plt.show()
