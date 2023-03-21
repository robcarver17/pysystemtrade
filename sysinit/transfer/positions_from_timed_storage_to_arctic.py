from sysdata.data_blob import dataBlob
from sysdata.mongodb.mongo_positions_by_strategy_TO_DEPRECATE import (
    mongoStrategyPositionData,
)
from sysdata.arctic.arctic_historic_strategy_positions import arcticStrategyPositionData

data = dataBlob(keep_original_prefix=True)
data.add_class_list([mongoStrategyPositionData, arcticStrategyPositionData])

list_of_instrument_strategies = (
    data.mongo_strategy_position.get_list_of_instrument_strategies()
)

for instrument_strategy in list_of_instrument_strategies:
    old_data = (
        data.mongo_strategy_position.get_position_as_df_for_instrument_strategy_object(
            instrument_strategy
        )
    )
