from typing import List, Dict
from copy import copy
import pandas as pd
import datetime

from syscore.constants import arg_not_supplied, success, failure
from sysexecution.orders.named_order_objects import missing_order

from sysdata.mongodb.mongo_roll_state_storage import mongoRollStateData
from sysdata.mongodb.mongo_position_by_contract import mongoContractPositionData
from sysdata.mongodb.mongo_positions_by_strategy import mongoStrategyPositionData
from sysdata.mongodb.mongo_optimal_position import mongoOptimalPositionData


from sysdata.production.roll_state import rollStateData
from sysdata.production.historic_positions import (
    contractPositionData,
    strategyPositionData,
    listOfInstrumentStrategyPositions,
)
from sysdata.production.optimal_positions import optimalPositionData


from sysdata.data_blob import dataBlob

from sysexecution.trade_qty import tradeQuantity
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.orders.instrument_orders import instrumentOrder

from sysobjects.production.positions import listOfContractPositions
from sysobjects.production.tradeable_object import (
    listOfInstrumentStrategies,
    instrumentStrategy,
)
from sysobjects.production.optimal_positions import (
    simpleOptimalPosition,
    listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies,
    listOfOptimalPositionsAcrossInstrumentStrategies,
    instrumentStrategyAndOptimalPosition,
)
from sysobjects.production.roll_state import (
    RollState,
    is_forced_roll_state,
    is_type_of_active_rolling_roll_state,
)
from sysobjects.contracts import futuresContract

from sysproduction.data.generic_production_data import productionDataLayerGeneric


class diagPositions(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_list(
            [mongoRollStateData, mongoContractPositionData, mongoStrategyPositionData]
        )
        return data

    @property
    def db_roll_state_data(self) -> rollStateData:
        return self.data.db_roll_state

    @property
    def db_contract_position_data(self) -> contractPositionData:
        return self.data.db_contract_position

    @property
    def db_strategy_position_data(self) -> strategyPositionData:
        return self.data.db_strategy_position

    def is_forced_roll_required(self, instrument_code: str) -> bool:
        roll_state = self.get_roll_state(instrument_code)
        is_forced_roll_required = is_forced_roll_state(roll_state)

        return is_forced_roll_required

    def is_roll_state_passive(self, instrument_code: str) -> bool:
        roll_state = self.get_roll_state(instrument_code)
        is_roll_state_passive = roll_state == RollState.Passive

        return is_roll_state_passive

    def is_roll_state_no_roll(self, instrument_code: str) -> bool:
        roll_state = self.get_roll_state(instrument_code)
        is_roll_state_no_roll = roll_state == RollState.No_Roll

        return is_roll_state_no_roll

    def is_roll_state_force(self, instrument_code: str) -> bool:
        roll_state = self.get_roll_state(instrument_code)
        is_roll_state_force = roll_state == RollState.Force

        return is_roll_state_force

    def is_roll_state_force_outright(self, instrument_code: str) -> bool:
        roll_state = self.get_roll_state(instrument_code)
        is_roll_state_force_outright = roll_state == RollState.Force_Outright

        return is_roll_state_force_outright

    def is_roll_state_close(self, instrument_code: str) -> bool:
        roll_state = self.get_roll_state(instrument_code)

        is_roll_state_close = roll_state == RollState.Close

        return is_roll_state_close

    def is_type_of_active_rolling_roll_state(self, instrument_code: str) -> bool:
        roll_state = self.get_roll_state(instrument_code)
        return is_type_of_active_rolling_roll_state(roll_state)

    def get_name_of_roll_state(self, instrument_code: str) -> RollState:
        roll_state_name = self.db_roll_state_data.get_name_of_roll_state(
            instrument_code
        )

        return roll_state_name

    def get_roll_state(self, instrument_code: str) -> RollState:
        roll_state = self.db_roll_state_data.get_roll_state(instrument_code)

        return roll_state

    def get_dict_of_actual_positions_for_strategy(
        self, strategy_name: str
    ) -> Dict[str, int]:
        list_of_instruments = self.get_list_of_instruments_for_strategy_with_position(
            strategy_name
        )
        list_of_instrument_strategies = [
            instrumentStrategy(
                strategy_name=strategy_name, instrument_code=instrument_code
            )
            for instrument_code in list_of_instruments
        ]

        actual_positions = dict(
            [
                (
                    instrument_strategy.instrument_code,
                    self.get_current_position_for_instrument_strategy(
                        instrument_strategy
                    ),
                )
                for instrument_strategy in list_of_instrument_strategies
            ]
        )

        return actual_positions

    def get_position_df_for_contract(self, contract: futuresContract) -> pd.DataFrame:

        df_object = (
            self.db_contract_position_data.get_position_as_df_for_contract_object(
                contract
            )
        )

        return df_object

    def get_position_df_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> pd.DataFrame:

        df_object = self.db_strategy_position_data.get_position_as_df_for_instrument_strategy_object(
            instrument_strategy
        )

        return df_object

    def get_positions_for_instrument_and_contract_list(
        self, instrument_code: str, list_of_contract_date_str: list
    ) -> list:

        list_of_contracts = [
            futuresContract(instrument_code, contract_date_str)
            for contract_date_str in list_of_contract_date_str
        ]

        list_of_positions = [
            self.get_position_for_contract(contract) for contract in list_of_contracts
        ]

        return list_of_positions

    def get_position_for_contract(self, contract: futuresContract) -> float:

        position = (
            self.db_contract_position_data.get_current_position_for_contract_object(
                contract
            )
        )

        return position

    def get_current_position_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> int:

        position = self.db_strategy_position_data.get_current_position_for_instrument_strategy_object(
            instrument_strategy
        )

        return position

    def get_list_of_instruments_for_strategy_with_position(
        self, strategy_name: str, ignore_zero_positions=True
    ) -> List[str]:

        instrument_list = self.db_strategy_position_data.get_list_of_instruments_for_strategy_with_position(
            strategy_name, ignore_zero_positions=ignore_zero_positions
        )
        return instrument_list

    def get_list_of_instruments_with_any_position(self) -> list:
        instrument_list = (
            self.db_contract_position_data.get_list_of_instruments_with_any_position()
        )

        return instrument_list

    def get_list_of_instruments_with_current_positions(self) -> list:
        instrument_list = (
            self.db_contract_position_data.get_list_of_instruments_with_current_positions()
        )

        return instrument_list

    def get_list_of_strategies_with_positions(self) -> list:
        list_of_strategies = (
            self.db_strategy_position_data.get_list_of_strategies_with_positions()
        )

        return list_of_strategies

    def get_list_of_strategies_and_instruments_with_positions(
        self,
    ) -> listOfInstrumentStrategies:
        return (
            self.db_strategy_position_data.get_list_of_strategies_and_instruments_with_positions()
        )

    def get_all_current_contract_positions(self) -> listOfContractPositions:
        list_of_current_positions = (
            self.db_contract_position_data.get_all_current_positions_as_list_with_contract_objects()
        )

        return list_of_current_positions

    def get_all_current_strategy_instrument_positions(
        self,
    ) -> listOfInstrumentStrategyPositions:
        list_of_current_positions = (
            self.db_strategy_position_data.get_all_current_positions_as_list_with_instrument_objects()
        )

        return list_of_current_positions

    def get_current_instrument_position_across_strategies(
        self, instrument_code: str
    ) -> int:
        all_positions = self.get_all_current_strategy_instrument_positions()
        all_positions_sum_over_instruments = all_positions.sum_for_instrument()
        position = all_positions_sum_over_instruments.position_for_instrument(
            instrument_code
        )

        return position

    def get_list_of_breaks_between_contract_and_strategy_positions(self) -> list:
        contract_positions = self.get_all_current_contract_positions()
        instrument_positions_from_contract = contract_positions.sum_for_instrument()
        strategy_instrument_positions = (
            self.get_all_current_strategy_instrument_positions()
        )
        instrument_positions_from_strategies = (
            strategy_instrument_positions.sum_for_instrument()
        )

        list_of_breaks = instrument_positions_from_contract.return_list_of_breaks(
            instrument_positions_from_strategies
        )
        return list_of_breaks

    def get_list_of_contracts_with_any_contract_position_for_instrument(
        self, instrument_code: str
    ):
        list_of_date_str = self.db_contract_position_data.get_list_of_contract_date_str_with_any_position_for_instrument(
            instrument_code
        )

        return list_of_date_str

    def get_list_of_contracts_with_any_contract_position_for_instrument_in_date_range(
        self,
        instrument_code: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime = arg_not_supplied,
    ) -> list:

        if end_date is arg_not_supplied:
            end_date = datetime.datetime.now()

        list_of_date_str_with_position = self.db_contract_position_data.get_list_of_contract_date_str_with_any_position_for_instrument_in_date_range(
            instrument_code, start_date, end_date
        )

        return list_of_date_str_with_position


class dataOptimalPositions(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_object(mongoOptimalPositionData)

        return data

    @property
    def db_optimal_position_data(self) -> optimalPositionData:
        return self.data.db_optimal_position

    def get_list_of_current_optimal_positions_for_strategy_name(
        self, strategy_name: str
    ) -> listOfOptimalPositionsAcrossInstrumentStrategies:

        all_optimal_positions = self.get_list_of_optimal_positions()
        optimal_positions_for_strategy = all_optimal_positions.filter_by_strategy(
            strategy_name
        )

        return optimal_positions_for_strategy

    def get_list_of_instruments_for_strategy_with_optimal_position(
        self, strategy_name: str, raw_positions=False
    ) -> list:
        if raw_positions:
            use_strategy_name = strategy_name_with_raw_tag(strategy_name)
        else:
            use_strategy_name = strategy_name

        list_of_instruments = self.db_optimal_position_data.get_list_of_instruments_for_strategy_with_optimal_position(
            use_strategy_name
        )

        return list_of_instruments

    def get_list_of_strategies_with_optimal_position(self) -> list:

        list_of_strategies = (
            self.db_optimal_position_data.list_of_strategies_with_optimal_position()
        )
        list_of_strategies = remove_raw_strategies(list_of_strategies)

        return list_of_strategies

    def get_current_optimal_position_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy, raw_positions=False
    ) -> simpleOptimalPosition:

        if raw_positions:
            use_instrument_strategy = instrument_strategy_with_raw_tag(
                instrument_strategy
            )
        else:
            use_instrument_strategy = instrument_strategy

        current_optimal_position_entry = self.db_optimal_position_data.get_current_optimal_position_for_instrument_strategy(
            use_instrument_strategy
        )

        return current_optimal_position_entry

    def get_optimal_position_as_df_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> pd.DataFrame:

        df_object = self.db_optimal_position_data.get_optimal_position_as_df_for_instrument_strategy(
            instrument_strategy
        )

        return df_object

    def update_optimal_position_for_instrument_strategy(
        self,
        instrument_strategy: instrumentStrategy,
        position_entry: simpleOptimalPosition,
        raw_positions=False,
    ):
        if raw_positions:
            use_instrument_strategy = instrument_strategy_with_raw_tag(
                instrument_strategy
            )
        else:
            use_instrument_strategy = instrument_strategy

        self.db_optimal_position_data.update_optimal_position_for_instrument_strategy(
            use_instrument_strategy, position_entry
        )

    def get_list_of_optimal_positions(
        self,
    ) -> listOfOptimalPositionsAcrossInstrumentStrategies:

        list_of_optimal_positions_and_instrument_strategies = (
            self.db_optimal_position_data.get_list_of_optimal_positions()
        )

        list_of_optimal_positions_and_instrument_strategies = (
            remove_raw_from_list_of_optimal_positions_and_instrument_strategies(
                list_of_optimal_positions_and_instrument_strategies
            )
        )

        return list_of_optimal_positions_and_instrument_strategies

    def get_pd_of_position_breaks(self) -> pd.DataFrame:
        optimal_and_current = self.get_list_of_optimal_and_current_positions()
        optimal_and_current_as_pd = optimal_and_current.as_pd_with_breaks()

        return optimal_and_current_as_pd

    def get_list_of_optimal_position_breaks(self) -> list:
        opt_positions = self.get_pd_of_position_breaks()
        with_breaks = opt_positions[opt_positions.breaks]
        items_with_breaks = list(with_breaks.index)

        return items_with_breaks

    def get_list_of_optimal_and_current_positions(
        self,
    ) -> listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies:

        optimal_positions = self.get_list_of_optimal_positions()
        position_data = diagPositions(self.data)
        current_positions = (
            position_data.get_all_current_strategy_instrument_positions()
        )
        optimal_and_current = optimal_positions.add_positions(current_positions)

        return optimal_and_current


class updatePositions(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_list(
            [
                mongoRollStateData,
                mongoContractPositionData,
                mongoStrategyPositionData,
                mongoOptimalPositionData,
            ]
        )
        return data

    @property
    def db_roll_state_data(self) -> rollStateData:
        return self.data.db_roll_state

    @property
    def db_strategy_position_data(self) -> strategyPositionData:
        return self.data.db_strategy_position

    @property
    def db_contract_position_data(self) -> contractPositionData:
        return self.data.db_contract_position

    @property
    def diag_positions(self):
        return diagPositions(self.data)

    def set_roll_state(self, instrument_code: str, roll_state_required: RollState):
        return self.db_roll_state_data.set_roll_state(
            instrument_code, roll_state_required
        )

    def update_strategy_position_table_with_instrument_order(
        self, original_instrument_order: instrumentOrder, new_fill: tradeQuantity
    ):
        """
        Alter the strategy position table according to new_fill value

        :param original_instrument_order:
        :return:
        """

        instrument_strategy = original_instrument_order.instrument_strategy

        current_position_as_int = (
            self.diag_positions.get_current_position_for_instrument_strategy(
                instrument_strategy
            )
        )
        trade_done_as_int = new_fill.as_single_trade_qty_or_error()
        if trade_done_as_int is missing_order:
            self.log.critical("Instrument orders can't be spread orders!")
            return failure

        new_position_as_int = current_position_as_int + trade_done_as_int

        self.db_strategy_position_data.update_position_for_instrument_strategy_object(
            instrument_strategy, new_position_as_int
        )

        log = original_instrument_order.log_with_attributes(self.log)
        log.msg(
            "Updated position of %s from %d to %d because of trade %s %d fill %s"
            % (
                str(instrument_strategy),
                current_position_as_int,
                new_position_as_int,
                str(original_instrument_order),
                original_instrument_order.order_id,
                str(new_fill),
            )
        )

        return success

    def update_contract_position_table_with_contract_order(
        self, contract_order_before_fills: contractOrder, fill_list: tradeQuantity
    ):
        """
        Alter the strategy position table according to contract order fill value

        :param contract_order_before_fills:
        :return:
        """
        futures_contract_entire_order = contract_order_before_fills.futures_contract
        list_of_individual_contracts = (
            futures_contract_entire_order.as_list_of_individual_contracts()
        )

        time_date = datetime.datetime.now()

        log = contract_order_before_fills.log_with_attributes(self.log)

        for contract, trade_done in zip(list_of_individual_contracts, fill_list):
            self._update_positions_for_individual_contract_leg(
                contract=contract, trade_done=trade_done, time_date=time_date
            )
            log.msg(
                "Updated position of %s because of trade %s ID:%d with fills %d"
                % (
                    str(contract),
                    str(contract_order_before_fills),
                    contract_order_before_fills.order_id,
                    trade_done,
                )
            )

    def _update_positions_for_individual_contract_leg(
        self, contract: futuresContract, trade_done: int, time_date: datetime.datetime
    ):

        current_position = self.diag_positions.get_position_for_contract(contract)

        new_position = current_position + trade_done

        self.db_contract_position_data.update_position_for_contract_object(
            contract, new_position, date=time_date
        )
        # check
        new_position_db = self.diag_positions.get_position_for_contract(contract)

        log = contract.specific_log(self.log)
        log.msg(
            "Updated position of %s from %d to %d; new position in db is %d"
            % (
                str(contract),
                current_position,
                new_position,
                new_position_db,
            )
        )


def annonate_df_index_with_positions_held(data: dataBlob, pd_df: pd.DataFrame):
    instrument_code_list = list(pd_df.index)
    held_instruments = get_list_of_instruments_with_current_positions(data)

    def _annotate(instrument_code, held_instruments):
        if instrument_code in held_instruments:
            return "%s*" % instrument_code
        else:
            return instrument_code

    instrument_code_list = [
        _annotate(instrument_code, held_instruments)
        for instrument_code in instrument_code_list
    ]
    pd_df.index = instrument_code_list

    return pd_df


def get_list_of_instruments_with_current_positions(data: dataBlob) -> List[str]:
    diag_positions = diagPositions(data)
    all_contract_positions = diag_positions.get_all_current_contract_positions()

    return all_contract_positions.unique_list_of_instruments()


POST_TAG_FOR_RAW_OPTIMAL_POSITION = "_raw"


def remove_raw_strategies(list_of_strategies: list) -> list:
    list_of_strategies = [
        strategy_name
        for strategy_name in list_of_strategies
        if is_not_raw_strategy(strategy_name)
    ]

    return list_of_strategies


def is_not_raw_strategy(strategy_name: str) -> bool:
    return not is_raw_strategy(strategy_name)


def is_raw_strategy(strategy_name: str) -> bool:
    return strategy_name.endswith(POST_TAG_FOR_RAW_OPTIMAL_POSITION)


def remove_raw_from_list_of_optimal_positions_and_instrument_strategies(
    list_of_optimal_positions_and_instrument_strategies: listOfOptimalPositionsAcrossInstrumentStrategies,
) -> listOfOptimalPositionsAcrossInstrumentStrategies:

    list_of_optimal_positions_and_instrument_strategies = [
        optimal_position_and_instrument_strategy
        for optimal_position_and_instrument_strategy in list_of_optimal_positions_and_instrument_strategies
        if is_not_raw_optimal_position_and_instrument_strategy(
            optimal_position_and_instrument_strategy
        )
    ]

    return listOfOptimalPositionsAcrossInstrumentStrategies(
        list_of_optimal_positions_and_instrument_strategies
    )


def is_not_raw_optimal_position_and_instrument_strategy(
    optimal_position_and_instrument_strategy: instrumentStrategyAndOptimalPosition,
) -> bool:

    return is_not_raw_instrument_strategy(
        optimal_position_and_instrument_strategy.instrument_strategy
    )


def is_not_raw_instrument_strategy(instrument_strategy: instrumentStrategy) -> bool:
    return is_not_raw_strategy(instrument_strategy.strategy_name)


def instrument_strategy_with_raw_tag(
    instrument_strategy: instrumentStrategy,
) -> instrumentStrategy:
    original_strategy_name = copy(instrument_strategy.strategy_name)
    strategy_name = strategy_name_with_raw_tag(original_strategy_name)

    new_instrument_strategy = instrumentStrategy(
        strategy_name=strategy_name, instrument_code=instrument_strategy.instrument_code
    )

    return new_instrument_strategy


def strategy_name_with_raw_tag(strategy_name: str) -> str:
    return strategy_name + POST_TAG_FOR_RAW_OPTIMAL_POSITION
