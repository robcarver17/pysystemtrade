"""
Update spot FX prices using interactive brokers data, dump into mongodb

Allow manual checking resolution of spikes

"""

from syscore.objects import success

from sysbrokers.IB.ibConnection import connectionIB
from sysdata.mongodb.mongo_connection import mongoDb
from sysdata.futures.manual_price_checker import manual_price_checker
from sysdata.fx.spotfx import fxPrices

from syslogdiag.log import logToMongod as logger

from sysproduction.data.get_data import dataBlob


def update_manual_check_fx_prices(fx_code):
    """
    Update FX prices stored in Arctic (Mongo) with interactive brokers prices (usually going back about a year)

    :return: Nothing
    """

    with mongoDb() as mongo_db,\
        logger("Update-FX-prices", mongo_db=mongo_db) as log,\
        connectionIB(log=log.setup(component="IB-connection")) as ib_conn:

        data = dataBlob("ibFxPricesData arcticFxPricesData", ib_conn=ib_conn, mongo_db=mongo_db)

        list_of_codes_all = data.ib_fx_prices.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFx.csv

        if fx_code not in list_of_codes_all:
            print("\n\n\ %s is not an FX code (valid codes: %s) \n\n" % (fx_code, list_of_codes_all))
            raise Exception()

        log.label(currency_code=fx_code)
        update_manual_check_fx_prices_for_code(fx_code, data)

    return success

def update_manual_check_fx_prices_for_code(fx_code, data):
    new_fx_prices = data.ib_fx_prices.get_fx_prices(fx_code) # returns fxPrices object
    if len(new_fx_prices)==0:
        data.log.warn("No FX prices found for %s" % fx_code)

    old_fx_prices = data.arctic_fx_prices.get_fx_prices(fx_code)

    ## May break manual price checking code if not equal
    old_fx_prices.name = new_fx_prices.name = ''

    print("\n\n Manually checking prices for %s \n\n" % fx_code)
    new_prices_checked = manual_price_checker(old_fx_prices, new_fx_prices,
                         type_new_data = fxPrices.from_data_frame
                         )

    rows_added = data.arctic_fx_prices.update_fx_prices(fx_code, new_prices_checked, check_for_spike=False)

    return success

