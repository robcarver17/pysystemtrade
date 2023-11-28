from syscore.constants import arg_not_supplied

from sysdata.sim.db_futures_sim_data import dbFuturesSimData
from sysdata.data_blob import dataBlob

from sysproduction.data.production_data_objects import (
    get_class_for_data_type,
    FUTURES_ADJUSTED_PRICE_DATA,
    FUTURES_MULTIPLE_PRICE_DATA,
    FX_DATA,
    STORED_SPREAD_DATA,
    FUTURES_INSTRUMENT_DATA,
    ROLL_PARAMETERS_DATA,
)


def get_sim_data_object_for_production(data=arg_not_supplied) -> dbFuturesSimData:
    # Check data has the right elements to do this
    if data is arg_not_supplied:
        data = dataBlob()

    data.add_class_list(
        [
            get_class_for_data_type(FUTURES_ADJUSTED_PRICE_DATA),
            get_class_for_data_type(FUTURES_MULTIPLE_PRICE_DATA),
            get_class_for_data_type(FX_DATA),
            get_class_for_data_type(STORED_SPREAD_DATA),
            get_class_for_data_type(FUTURES_INSTRUMENT_DATA),
            get_class_for_data_type(ROLL_PARAMETERS_DATA),
        ]
    )

    return dbFuturesSimData(data)
