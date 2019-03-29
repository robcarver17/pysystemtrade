"""
Update spot FX prices using interactive brokers data, dump into mongodb
"""

from sysbrokers.IB.ibConnection import connectionIB
from sysbrokers.IB.ibSpotFXData import ibFxPricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData

import pandas as pd

def update_fx_prices():
    """
    Update FX prices stored in Arctic (Mongo) with interactive brokers prices (usually going back about a year)

    :return: Nothing
    """

    # avoid unique ids
    conn = connectionIB(client=100)

    ibfxpricedata = ibFxPricesData(conn)
    arcticfxdata = arcticFxPricesData()


    list_of_codes_all = ibfxpricedata.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFx.csv
    print(list_of_codes_all)

    for fx_code in list_of_codes_all:
        print(fx_code)
        new_fx_prices = ibfxpricedata.get_fx_prices(fx_code) # returns fxPrices object

        if len(new_fx_prices)==0:
            print("couldn't get any more data")
            continue

        old_fx_prices = arcticfxdata.get_fx_prices(fx_code)

        new_fx_prices = new_fx_prices[new_fx_prices.index>old_fx_prices.index[-1]]

        if len(new_fx_prices)==0:
            print("No new data found")
            continue

        # merge old and new
        print("Old:")
        print(old_fx_prices.tail(2))
        print("New:")
        print(new_fx_prices.head(2))

        fx_prices = pd.concat([old_fx_prices, new_fx_prices], axis=0)
        fx_prices = fx_prices.sort_index()

        # remove duplicates
        fx_prices = fx_prices[~fx_prices.index.duplicated(keep='first')]

        print("Merged")
        print(fx_prices.tail(5))

        # write
        arcticfxdata.add_fx_prices(fx_code, fx_prices, ignore_duplication=True)

        # consider: crontab, logging, backup, reporting, error handling, pacing
        # code to write to csv
