"""
Update spot FX prices using interactive brokers data, dump into mongodb
"""

from sysbrokers.IB.ibConnection import connectionIB
from sysbrokers.IB.ibSpotFXData import ibFxPricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from syslogdiag.log import logToMongod as logger

import pandas as pd

def update_fx_prices():
    """
    Update FX prices stored in Arctic (Mongo) with interactive brokers prices (usually going back about a year)

    :return: Nothing
    """

    log=logger("Update-FX-prices")

    # avoid unique ids
    conn = connectionIB(client=100, log=log.setup(component="IB-connection"))

    ibfxpricedata = ibFxPricesData(conn, log=log.setup(component="ibFxPricesData"))
    arcticfxdata = arcticFxPricesData(log=log.setup(component="arcticFxPricesData"))

    list_of_codes_all = ibfxpricedata.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFx.csv
    log.msg("FX Codes: %s" % str(list_of_codes_all))
    for fx_code in list_of_codes_all:
        log.label(currency_code = fx_code)
        new_fx_prices = ibfxpricedata.get_fx_prices(fx_code) # returns fxPrices object

        if len(new_fx_prices)==0:
            log.error("Error trying to get data for %s" % fx_code)
            continue

        old_fx_prices = arcticfxdata.get_fx_prices(fx_code)

        new_fx_prices = new_fx_prices[new_fx_prices.index>old_fx_prices.index[-1]]

        if len(new_fx_prices)==0:
            log.msg("No additional data for %s" % fx_code)
            continue

        fx_prices = pd.concat([old_fx_prices, new_fx_prices], axis=0)
        fx_prices = fx_prices.sort_index()

        # remove duplicates
        fx_prices = fx_prices[~fx_prices.index.duplicated(keep='first')]

        # write
        arcticfxdata.add_fx_prices(fx_code, fx_prices, ignore_duplication=True)

        # consider: reporting, pacing, clientids, private directory
        # code to write to csv
        # keep track of client ids
