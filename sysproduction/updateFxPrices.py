"""
Update spot FX prices using interactive brokers data, dump into mongodb
"""

from sysbrokers.IB.ibConnection import connectionIB
from sysdata.mongodb.mongo_connection import mongoDb
from sysbrokers.IB.ibSpotFXData import ibFxPricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from syslogdiag.log import logToMongod as logger



def update_fx_prices():
    """
    Update FX prices stored in Arctic (Mongo) with interactive brokers prices (usually going back about a year)

    :return: Nothing
    """

    mongo_db = mongoDb() # will use default database, host unles specified here

    log=logger("Update-FX-prices", mongo_db=mongo_db)

    ib_conn = connectionIB(log=log.setup(component="IB-connection")) # will use default port, host

    ibfxpricedata = ibFxPricesData(ib_conn, log=log.setup(component="ibFxPricesData"))
    arcticfxdata = arcticFxPricesData(mongo_db=mongo_db, log=log.setup(component="arcticFxPricesData"))

    list_of_codes_all = ibfxpricedata.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFx.csv
    log.msg("FX Codes: %s" % str(list_of_codes_all))
    for fx_code in list_of_codes_all:
        log.label(currency_code = fx_code)
        new_fx_prices = ibfxpricedata.get_fx_prices(fx_code) # returns fxPrices object

        arcticfxdata.update_fx_prices(fx_code, new_fx_prices)

    ib_conn.disconnect()
