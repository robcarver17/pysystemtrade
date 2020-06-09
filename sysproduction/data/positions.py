from syscore.objects import arg_not_supplied, missing_data, success, failure

from sysproduction.data.contracts import missing_contract
from sysproduction.data.get_data import dataBlob


class diagPositions(object):
    def __init__(self, data = arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("mongoRollStateData mongoContractPositionData mongoStrategyPositionData mongoOptimalPositionData")
        self.data = data

    def get_roll_state(self, instrument_code):
        return self.data.db_roll_state.get_roll_state(instrument_code)

    def get_positions_for_instrument_and_contract_list(self, instrument_code, contract_list):
        list_of_positions = [self.get_position_for_instrument_and_contract_date(instrument_code, contract_date)
                             for contract_date in contract_list]

        return list_of_positions

    def get_position_for_instrument_and_contract_date(self, instrument_code, contract_date):
        if contract_date is missing_contract:
            return 0.0
        position = self.data.db_contract_position.\
                get_current_position_for_instrument_and_contract_date(instrument_code, contract_date)
        if position is missing_data:
            return 0.0

        return position.position

    def get_position_for_strategy_and_instrument(self, strategy_name, instrument_code):
        position = self.data.db_strategy_position.get_current_position_for_strategy_and_instrument(strategy_name, instrument_code)
        if position is missing_data:
            return 0.0
        return position.position

    def get_list_of_instruments_for_strategy_with_position(self, strategy_name):
        instrument_list = self.data.db_strategy_position.get_list_of_instruments_for_strategy_with_position(strategy_name)
        return instrument_list

    def get_list_of_instruments_with_any_position(self):
        return self.data.db_contract_position.get_list_of_instruments_with_any_position()

    def get_list_of_strategies_with_positions(self):
        list_of_strat_instrument_tuples = self.data.db_strategy_position.get_list_of_strategies_and_instruments_with_positions(ignore_zero_positions=True)
        strats = list(set([x[0] for x in list_of_strat_instrument_tuples]))

        return strats

    def get_list_of_positions_for_strategy(self, strategy_name):
        return self.data.db_strategy_position.get_list_of_instruments_for_strategy_with_position(strategy_name)

    def get_all_current_contract_positions(self):
        return self.data.db_contract_position.\
            get_all_current_positions_as_list_with_contract_objects()

    def get_all_current_strategy_instrument_positions(self):
        return self.data.db_strategy_position.get_all_current_positions_as_list_with_instrument_objects()

    def get_list_of_breaks_between_contract_and_strategy_positions(self):
        contract_positions = self.get_all_current_contract_positions()
        instrument_positions_from_contract = contract_positions.sum_for_instrument()
        strategy_instrument_positions = self.get_all_current_strategy_instrument_positions()
        instrument_positions_from_strategies = strategy_instrument_positions.sum_for_instrument()

        return instrument_positions_from_contract.return_list_of_breaks(instrument_positions_from_strategies)

    def optimal_position_data(self):
        return self.data.db_optimal_position


class updatePositions(object):
    def __init__(self, data = arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("mongoRollStateData mongoContractPositionData mongoStrategyPositionData mongoOptimalPositionData")
        self.data = data
        self.log = data.log

    def set_roll_state(self, instrument_code, roll_state_required):
        return self.data.db_roll_state.set_roll_state(instrument_code, roll_state_required)

    def update_strategy_position_table_with_instrument_order(self, instrument_order):
        """
        Alter the strategy position table according to instrument order fill value

        :param instrument_order:
        :return:
        """

        strategy_name = instrument_order.strategy_name
        instrument_code = instrument_order.instrument_code
        current_position_object = self.data.db_strategy_position.\
            get_current_position_for_strategy_and_instrument(strategy_name, instrument_code)
        trade_done = instrument_order.fill
        if current_position_object is missing_data:
            current_position = 0
        else:
            current_position = current_position_object.position

        new_position = current_position + trade_done

        self.data.db_strategy_position.\
            update_position_for_strategy_and_instrument(strategy_name, instrument_code, new_position,
                                                        )

        self.log.msg("Updated position of %s/%s from %d to %d because of trade %s %d" %
                     (strategy_name, instrument_code, current_position, new_position, str(instrument_order),
                      instrument_order.order_id))

        return success

    def update_contract_position_table_with_contract_order(self, contract_order):
        """
        Alter the strategy position table according to contract order fill value

        :param contract_order:
        :return:
        """

        instrument_code = contract_order.instrument_code
        contract_id_list = contract_order.contract_id
        fill_list = contract_order.fill

        for trade_done, contract_id in zip(fill_list, contract_id_list):
            current_position_object = self.data.db_contract_position.\
                get_current_position_for_instrument_and_contract_date(instrument_code, contract_id)
            if current_position_object is missing_data:
                current_position = 0
            else:
                current_position = current_position_object.position

            new_position = current_position + trade_done

            self.data.db_contract_position.\
                update_position_for_instrument_and_contract_date(instrument_code, contract_id, new_position)

            self.log.msg("Updated position of %s/%s from %d to %d because of trade %s %d" %
                         (instrument_code, contract_id, current_position, new_position, str(contract_order),
                          contract_order.order_id))

    def update_optimal_position_for_strategy_and_instrument(self, strategy_name, instrument_code, position_entry):
        self.data.db_optimal_position.update_optimal_position_for_strategy_and_instrument(strategy_name, instrument_code, position_entry)

