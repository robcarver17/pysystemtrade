import pandas as pd
import datetime

from syscore.objects import (
    arg_not_supplied,
    success,
    failure,
    missing_order)

from sysdata.mongodb.mongo_roll_state_storage import mongoRollStateData
from sysdata.mongodb.mongo_position_by_contract import mongoContractPositionData
from sysdata.mongodb.mongo_positions_by_strategy import mongoStrategyPositionData
from sysdata.mongodb.mongo_optimal_position import mongoOptimalPositionData

from sysdata.production.roll_state import rollStateData
from sysdata.production.historic_positions import contractPositionData, strategyPositionData, listOfInstrumentStrategyPositions
from sysdata.production.optimal_positions import optimalPositionData

from sysdata.data_blob import dataBlob

from sysexecution.trade_qty import tradeQuantity
from sysexecution.orders.contract_orders import contractOrder

from sysobjects.production.positions import listOfContractPositions
from sysobjects.production.tradeable_object import listOfInstrumentStrategies, instrumentStrategy
from sysobjects.production.optimal_positions import simpleOptimalPosition, listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies, listOfOptimalPositionsAcrossInstrumentStrategies
from sysobjects.production.roll_state import RollState, is_forced_roll_state, is_type_of_active_rolling_roll_state
from sysobjects.contracts import futuresContract

from sysproduction.data.contracts import missing_contract
from sysproduction.data.generic_production_data import productionDataLayerGeneric


class diagPositions(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_list([
            mongoRollStateData, mongoContractPositionData, mongoStrategyPositionData]
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

    def is_type_of_active_rolling_roll_state(self, instrument_code: str) -> bool:
        roll_state = self.get_roll_state(instrument_code)
        return is_type_of_active_rolling_roll_state(roll_state)

    def get_name_of_roll_state(self, instrument_code: str) -> RollState:
        roll_state_name = self.db_roll_state_data.get_name_of_roll_state(instrument_code)

        return roll_state_name

    def get_roll_state(self, instrument_code: str) -> RollState:
        roll_state = self.db_roll_state_data.get_roll_state(instrument_code)

        return roll_state

    def get_dict_of_actual_positions_for_strategy(self, strategy_name: str) -> dict:
        list_of_instruments = (
            self.get_list_of_instruments_for_strategy_with_position(
                strategy_name
            )
        )
        list_of_instrument_strategies = [
            instrumentStrategy(strategy_name=strategy_name, instrument_code=instrument_code)
            for instrument_code in list_of_instruments
        ]

        actual_positions = dict(
            [
                (
                    instrument_strategy.instrument_code,
                    self.get_current_position_for_instrument_strategy(instrument_strategy),
                )
                for instrument_strategy in list_of_instrument_strategies
            ]
        )

        return actual_positions


    def get_position_df_for_contract(
        self, contract: futuresContract
    ) -> pd.DataFrame:

        df_object = self.db_contract_position_data.get_position_as_df_for_contract_object(contract)

        return df_object

    def get_position_df_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> pd.DataFrame:

        df_object = self.db_strategy_position_data.get_position_as_df_for_instrument_strategy_object(
            instrument_strategy)

        return df_object


    def get_positions_for_instrument_and_contract_list(
        self,
            instrument_code: str,
            list_of_contract_date_str: list
        ) -> list:

        list_of_contracts = [futuresContract(instrument_code, contract_date_str)
                             for contract_date_str in list_of_contract_date_str]


        list_of_positions = [
            self.get_position_for_contract(contract)
            for contract in list_of_contracts
        ]

        return list_of_positions

    def get_position_for_contract(
        self, contract: futuresContract
        ) -> float:

        if contract is missing_contract:
            return 0.0
        position = self.db_contract_position_data.get_current_position_for_contract_object(contract)

        return position

    def get_current_position_for_instrument_strategy(
            self,
            instrument_strategy: instrumentStrategy) -> int:

        position = self.db_strategy_position_data.get_current_position_for_instrument_strategy_object(
            instrument_strategy)

        return position


    def get_list_of_instruments_for_strategy_with_position(
            self,
            strategy_name: str,
            ignore_zero_positions=True) -> list:

        instrument_list = self.db_strategy_position_data.get_list_of_instruments_for_strategy_with_position(
            strategy_name, ignore_zero_positions=ignore_zero_positions)
        return instrument_list

    def get_list_of_instruments_with_any_position(self) -> list:
        instrument_list = self.db_contract_position_data.get_list_of_instruments_with_any_position()

        return instrument_list

    def get_list_of_instruments_with_current_positions(self) -> list:
        instrument_list = self.db_contract_position_data.get_list_of_instruments_with_current_positions()

        return instrument_list

    def get_list_of_strategies_with_positions(self) -> list:
        list_of_strategies = self.db_strategy_position_data.get_list_of_strategies_with_positions()

        return list_of_strategies

    def get_list_of_strategies_and_instruments_with_positions(self) -> listOfInstrumentStrategies:
        return self.db_strategy_position_data.get_list_of_strategies_and_instruments_with_positions()

    def get_all_current_contract_positions(self) -> listOfContractPositions:
        list_of_current_positions =\
            self.db_contract_position_data.get_all_current_positions_as_list_with_contract_objects()

        return list_of_current_positions

    def get_all_current_strategy_instrument_positions(self) -> listOfInstrumentStrategyPositions:
        list_of_current_positions =\
            self.db_strategy_position_data.get_all_current_positions_as_list_with_instrument_objects()

        return list_of_current_positions

    def get_current_instrument_position_across_strategies(self, instrument_code: str) -> int:
        all_positions = self.get_all_current_strategy_instrument_positions()
        all_positions_sum_over_instruments = all_positions.sum_for_instrument()
        position = all_positions_sum_over_instruments.position_for_instrument(instrument_code)

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

        list_of_breaks  = instrument_positions_from_contract.return_list_of_breaks(
            instrument_positions_from_strategies
        )
        return list_of_breaks

    def get_list_of_contracts_with_any_contract_position_for_instrument(
        self, instrument_code: str
    ):
        list_of_date_str = self.db_contract_position_data.get_list_of_contract_date_str_with_any_position_for_instrument(
            instrument_code)

        return list_of_date_str

    def get_list_of_contracts_with_any_contract_position_for_instrument_in_date_range(
            self,
            instrument_code: str,
            start_date: datetime.datetime,
            end_date: datetime.datetime=arg_not_supplied) -> list:

        if end_date is arg_not_supplied:
            end_date = datetime.datetime.now()

        list_of_date_str_with_position = \
            self.db_contract_position_data.\
                get_list_of_contract_date_str_with_any_position_for_instrument_in_date_range(
            instrument_code, start_date, end_date)

        return list_of_date_str_with_position

class dataOptimalPositions(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_object(mongoOptimalPositionData)

        return data

    @property
    def db_optimal_position_data(self) -> optimalPositionData:
        return self.data.db_optimal_position

    def get_list_of_instruments_for_strategy_with_optimal_position(
            self, strategy_name: str) -> list:
        list_of_instruments = self.db_optimal_position_data.\
            get_list_of_instruments_for_strategy_with_optimal_position(
            strategy_name)

        return list_of_instruments

    def get_list_of_strategies_with_optimal_position(
            self) -> list:

        list_of_strategies = self.db_optimal_position_data.list_of_strategies_with_optimal_position()

        return list_of_strategies

    def get_current_optimal_position_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> simpleOptimalPosition:

        current_optimal_position_entry = self.db_optimal_position_data.get_current_optimal_position_for_instrument_strategy(
            instrument_strategy)

        return current_optimal_position_entry

    def get_optimal_position_as_df_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> pd.DataFrame:

        df_object= self.db_optimal_position_data.get_optimal_position_as_df_for_instrument_strategy(
            instrument_strategy)

        return df_object


    def update_optimal_position_for_instrument_strategy(
        self,
            instrument_strategy: instrumentStrategy,
            position_entry: simpleOptimalPosition
    ):
        self.db_optimal_position_data.update_optimal_position_for_instrument_strategy(
            instrument_strategy, position_entry)


    def get_list_of_optimal_positions(self) -> listOfOptimalPositionsAcrossInstrumentStrategies:
        list_of_optimal_positions_and_instrument_strategies = \
            self.db_optimal_position_data.get_list_of_optimal_positions()

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

    def get_list_of_optimal_and_current_positions(self) -> listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies:

        optimal_positions = self.get_list_of_optimal_positions()
        position_data = diagPositions(self.data)
        current_positions = (
            position_data.get_all_current_strategy_instrument_positions())
        optimal_and_current = optimal_positions.add_positions(
            current_positions)

        return optimal_and_current


class updatePositions(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_list(
            [mongoRollStateData, mongoContractPositionData, mongoStrategyPositionData, mongoOptimalPositionData]
        )
        return data

    @property
    def db_roll_state_data(self) ->rollStateData:
        return self.data.db_roll_state



    @property
    def diag_positions(self):
        return diagPositions(self.data)

    def set_roll_state(self, instrument_code: str, roll_state_required: RollState):
        return self.db_roll_state_data.set_roll_state(
            instrument_code, roll_state_required
        )

    def update_strategy_position_table_with_instrument_order(
        self, instrument_order, new_fill
    ):
        """
        Alter the strategy position table according to instrument order fill value

        :param instrument_order:
        :return:
        """

        # FIXME WOULD BE NICE IF COULD GET DIRECTLY FROM ORDER NOT REQUIRE TRADE_DONE
        strategy_name = instrument_order.strategy_name
        instrument_code = instrument_order.instrument_code
        instrument_strategy = instrumentStrategy(strategy_name=strategy_name, instrument_code=instrument_code)

        current_position = self.diag_positions.get_current_position_for_instrument_strategy(instrument_strategy)
        trade_done = new_fill.as_single_trade_qty_or_error()
        if trade_done is missing_order:
            self.log.critical("Instrument orders can't be spread orders!")
            return failure

        new_position = current_position + trade_done

        self.data.db_strategy_position.update_position_for_instrument_strategy_object(
            instrument_strategy, new_position)

        self.log.msg(
            "Updated position of %s/%s from %d to %d because of trade %s %d"
            % (
                strategy_name,
                instrument_code,
                current_position,
                new_position,
                str(instrument_order),
                instrument_order.order_id,
            )
        )

        return success

    def update_contract_position_table_with_contract_order(
        self, contract_order_before_fills: contractOrder,
            fill_list: tradeQuantity
    ):
        """
        Alter the strategy position table according to contract order fill value

        :param contract_order_before_fills:
        :return:
        """

        instrument_code = contract_order_before_fills.instrument_code
        contract_id_list = contract_order_before_fills.contract_date

        # WE DON'T USE THE CONTRACT FILL DATE DELIBERATELY
        time_date = datetime.datetime.now()

        for contract_id, trade_done in zip(contract_id_list, fill_list):
            self.update_positions_for_individual_contract_leg(
                instrument_code, contract_id, trade_done, time_date=time_date
            )
            self.log.msg(
                "Updated position of %s/%s because of trade %s ID:%d with fills %s" %
                (instrument_code,
                 contract_id,
                 str(contract_order_before_fills),
                 contract_order_before_fills.order_id,
                 str(fill_list),
                 ))

    def update_positions_for_individual_contract_leg(
        self, instrument_code, contract_id, trade_done, time_date=None
    ):
        #FIXME CHANGE TO CONTRACT
        if time_date is None:
            time_date = datetime.datetime.now()

        contract = futuresContract(instrument_code, contract_id)
        current_position = self.diag_positions.get_position_for_contract(contract)

        new_position = current_position + trade_done

        self.data.db_contract_position.update_position_for_contract_object(
            contract, new_position, date=time_date)
        # check
        new_position_db = self.diag_positions.get_position_for_contract(contract)

        self.log.msg(
            "Updated position of %s/%s from %d to %d; new position in db is %d"
            % (
                instrument_code,
                contract_id,
                current_position,
                new_position,
                new_position_db,
            )
        )
