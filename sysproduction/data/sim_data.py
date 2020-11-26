from syscore.objects import arg_not_supplied

from sysdata.sim.db_futures_sim_data import dbFuturesSimData
from sysdata.data_blob import dataBlob
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.mongodb.mongo_futures_instruments import mongoFuturesInstrumentData


def dataSimData(data=arg_not_supplied):
    # Check data has the right elements to do this
    if data is arg_not_supplied:
        data = dataBlob()

    data.add_class_list([arcticFuturesAdjustedPricesData, arcticFuturesMultiplePricesData,
                         arcticFxPricesData, mongoFuturesInstrumentData])


    return dbFuturesSimData(data)
