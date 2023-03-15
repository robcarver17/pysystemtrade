from syscore.constants import arg_not_supplied

from sysdata.sim.db_futures_sim_data import dbFuturesSimData
from sysdata.data_blob import dataBlob
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.csv.csv_instrument_data import csvFuturesInstrumentData
from sysdata.mongodb.mongo_spread_costs import mongoSpreadCostData
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData


def get_sim_data_object_for_production(data=arg_not_supplied) -> dbFuturesSimData:
    # Check data has the right elements to do this
    if data is arg_not_supplied:
        data = dataBlob()

    data.add_class_list(
        [
            arcticFuturesAdjustedPricesData,
            arcticFuturesMultiplePricesData,
            arcticFxPricesData,
            mongoSpreadCostData,
            csvFuturesInstrumentData,
            mongoRollParametersData,
        ]
    )

    return dbFuturesSimData(data)
