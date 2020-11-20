import datetime

from syscore.objects import (
    arg_not_supplied,
    missing_data,
    success,
    failure,
    missing_order,
)

from sysdata.mongodb.mongo_roll_state_storage import mongoRollStateData
from sysdata.mongodb.mongo_position_by_contract import mongoContractPositionData
from sysdata.mongodb.mongo_positions_by_strategy import mongoStrategyPositionData
from sysdata.mongodb.mongo_optimal_position import mongoOptimalPositionData

from sysproduction.data.contracts import missing_contract
from sysproduction.data.get_data import dataBlob


class diagPositions(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list([
            mongoRollStateData, mongoContractPositionData, mongoStrategyPositionData]
        )
        self.data = data
        self.log = data.log

    def get_roll_state(self, instrument_code):
        return self.data.db_roll_state.get_roll_state(instrument_code)

    def get_position_df_for_instrument_and_contract_id(
        self, instrument_code, contract_id
    ):
        return self.data.db_contract_position.get_position_as_df_for_instrument_and_contract_date(
            instrument_code, contract_id)

    def get_position_df_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        return self.data.db_strategy_position.get_position_as_df_for_strategy_and_instrument(
            strategy_name, instrument_code)

    def get_positions_for_instrument_and_contract_list(
        self, instrument_code, contract_list
    ):
        list_of_positions = [
            self.get_position_for_instrument_and_contract_date(
                instrument_code, contract_date
            )
            for contract_date in contract_list
        ]

        return list_of_positions

    def get_position_for_instrument_and_contract_date(
        self, instrument_code, contract_date
    ):
        if contract_date is missing_contract:
            return 0.0
        position = self.data.db_contract_position.get_current_position_for_instrument_and_contract_date(
            instrument_code, contract_date)
        if position is missing_data:
            return 0.0

        return position.position

    def get_position_for_strategy_and_instrument(
            self, strategy_name, instrument_code):
        position = self.data.db_strategy_position.get_current_position_for_strategy_and_instrument(
            strategy_name, instrument_code)
        if position is missing_data:
            return 0.0
        return position.position

    def get_list_of_instruments_for_strategy_with_position(
            self, strategy_name):
        instrument_list = self.data.db_strategy_position.get_list_of_instruments_for_strategy_with_position(
            strategy_name)
        return instrument_list

    def get_list_of_instruments_with_any_position(self):
        return (
            self.data.db_contract_position.get_list_of_instruments_with_any_position())

    def get_list_of_instruments_with_current_positions(self):
        return (
            self.data.db_contract_position.get_list_of_instruments_with_current_positions())


    def get_list_of_strategies_with_positions(self):
        list_of_strat_instrument_tuples = self.data.db_strategy_position.get_list_of_strategies_and_instruments_with_positions(
            ignore_zero_positions=True)
        strats = list(set([x[0] for x in list_of_strat_instrument_tuples]))

        return strats

    def get_all_current_positions_as_list_with_instrument_objects(self):
        return (
            self.data.db_strategy_position.get_all_current_positions_as_list_with_instrument_objects()
        )


    def get_all_current_contract_positions(self):
        return (
            self.data.db_contract_position.get_all_current_positions_as_list_with_contract_objects()
        )

    def get_all_current_strategy_instrument_positions(self):
        return (
            self.data.db_strategy_position.get_all_current_positions_as_list_with_instrument_objects()
        )

    def get_current_instrument_position_across_strategies(self, instrument_code):
        all_positions = self.get_all_current_strategy_instrument_positions()
        all_positions_sum_over_instruments = all_positions.sum_for_instrument()
        position = all_positions_sum_over_instruments.position_for_instrument(instrument_code)

        return position

    def get_list_of_breaks_between_contract_and_strategy_positions(self):
        contract_positions = self.get_all_current_contract_positions()
        instrument_positions_from_contract = contract_positions.sum_for_instrument()
        strategy_instrument_positions = (
            self.get_all_current_strategy_instrument_positions()
        )
        instrument_positions_from_strategies = (
            strategy_instrument_positions.sum_for_instrument()
        )

        return instrument_positions_from_contract.return_list_of_breaks(
            instrument_positions_from_strategies
        )

    def get_list_of_contracts_with_any_contract_position_for_instrument(
        self, instrument_code
    ):
        return self.data.db_contract_position.get_list_of_contracts_with_any_position_for_instrument(
            instrument_code)

    def get_list_of_contracts_with_any_contract_position_for_instrument_in_date_range(
            self, instrument_code, start_date, end_date=arg_not_supplied):
        if end_date is arg_not_supplied:
            end_date = datetime.datetime.now()

        return self.data.db_contract_position.get_list_of_contracts_with_any_position_for_instrument_in_date_range(
            instrument_code, start_date, end_date)


class dataOptimalPositions(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoOptimalPositionData)
        self.data = data

    def get_list_of_instruments_for_strategy_with_optimal_position(
            self, strategy_name):
        return self.data.db_optimal_position.get_list_of_instruments_for_strategy_with_optimal_position(
            strategy_name)

    def get_current_optimal_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        return self.data.db_optimal_position.get_current_optimal_position_for_strategy_and_instrument(
            strategy_name, instrument_code)

    def get_optimal_position_as_df_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        return self.data.db_optimal_position.get_optimal_position_as_df_for_strategy_and_instrument(
            strategy_name, instrument_code)

    def update_optimal_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code, position_entry
    ):
        self.data.db_optimal_position.update_optimal_position_for_strategy_and_instrument(
            strategy_name, instrument_code, position_entry)

    def get_list_of_optimal_positions(self):
        return self.data.db_optimal_position.get_list_of_optimal_positions()

    def get_pd_of_position_breaks(self):
        optimal_and_current = self.get_list_of_optimal_and_current_positions()

        return optimal_and_current.as_pd_with_breaks()

    def get_list_of_optimal_position_breaks(self):
        opt_positions = self.get_pd_of_position_breaks()
        with_breaks = opt_positions[opt_positions.breaks]

        return list(with_breaks.index)

    def get_list_of_optimal_and_current_positions(self):
        optimal_positions = self.get_list_of_optimal_positions()
        position_data = diagPositions(self.data)
        current_positions = (
            position_data.get_all_current_positions_as_list_with_instrument_objects())
        optimal_and_current = optimal_positions.add_positions(
            current_positions)

        return optimal_and_current


class updatePositions(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list(
            [mongoRollStateData, mongoContractPositionData, mongoStrategyPositionData, mongoOptimalPositionData]
        )
        self.data = data
        self.log = data.log

    def set_roll_state(self, instrument_code, roll_state_required):
        return self.data.db_roll_state.set_roll_state(
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

        strategy_name = instrument_order.strategy_name
        instrument_code = instrument_order.instrument_code
        current_position_object = self.data.db_strategy_position.get_current_position_for_strategy_and_instrument(
            strategy_name, instrument_code)
        trade_done = new_fill.as_int()
        if trade_done is missing_order:
            self.log.critical("Instrument orders can't be spread orders!")
            return failure

        if current_position_object is missing_data:
            current_position = 0
        else:
            current_position = current_position_object.position

        new_position = current_position + trade_done

        self.data.db_strategy_position.update_position_for_strategy_and_instrument(
            strategy_name, instrument_code, new_position)

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
        self, contract_order, fill_list
    ):
        """
        Alter the strategy position table according to contract order fill value

        :param contract_order:
        :return:
        """

        instrument_code = contract_order.instrument_code
        contract_id_list = contract_order.contract_id

        # WE DON'T USE THE CONTRACT FILL DUE TO DATETIME MIX UPS
        # time_date = contract_order.fill_datetime
        time_date = datetime.datetime.now()

        for contract_id, trade_done in zip(contract_id_list, fill_list):
            self.update_positions_for_individual_contract_leg(
                instrument_code, contract_id, trade_done, time_date=time_date
            )
            self.log.msg(
                "Updated position of %s/%s because of trade %s ID:%d with fills %s" %
                (instrument_code,
                 contract_id,
                 str(contract_order),
                    contract_order.order_id,
                    str(fill_list),
                 ))

    def update_positions_for_individual_contract_leg(
        self, instrument_code, contract_id, trade_done, time_date=None
    ):
        if time_date is None:
            time_date = datetime.datetime.now()

        current_position_object = self.data.db_contract_position.get_current_position_for_instrument_and_contract_date(
            instrument_code, contract_id)
        if current_position_object is missing_data:
            current_position = 0
        else:
            current_position = current_position_object.position

        new_position = current_position + trade_done

        self.data.db_contract_position.update_position_for_instrument_and_contract_date(
            instrument_code, contract_id, new_position, date=time_date)
        # check
        updated_position_object = self.data.db_contract_position.get_current_position_for_instrument_and_contract_date(
            instrument_code, contract_id)
        new_position_db = updated_position_object.position

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
