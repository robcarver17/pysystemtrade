
"""
Strategy specific execution code

For the classic buffered strategy we just compare actual positions with optimal positions, and generate orders
  accordingly

These are 'virtual' orders, because they are per instrument. We translate that to actual contracts downstream

Desired virtual orders have to be labelled with the desired type: limit, market,best-execution
"""

from sysexecution.instrument_orders import instrumentOrder
from sysexecution.strategy_order_handling import orderGeneratorForStrategy


class orderGeneratorForBufferedPositions(orderGeneratorForStrategy):
    def _required_orders_no_checking(self):
        strategy_name = self.strategy_name

        optimal_positions = self.get_optimal_positions()
        actual_positions = self.get_actual_positions_for_strategy()

        list_of_trades = list_of_trades_given_optimal_and_actual_positions(strategy_name, optimal_positions, actual_positions)

        return list_of_trades

    def get_optimal_positions(self):
        data  = self.data
        strategy_name = self.strategy_name

        data.add_class_list("mongoOptimalPositionData")
        optimal_position_data = data.mongo_optimal_position
        list_of_instruments = optimal_position_data.get_list_of_instruments_for_strategy_with_optimal_position(strategy_name)
        optimal_positions = dict([(instrument_code,
                                   optimal_position_data.get_current_optimal_position_for_strategy_and_instrument(strategy_name, instrument_code))
                             for instrument_code in list_of_instruments])
        upper_positions = dict([(instrument_code, opt_position.upper_position)
                                for instrument_code, opt_position in optimal_positions.items()])
        lower_positions = dict([(instrument_code, opt_position.lower_position)
                                for instrument_code, opt_position in optimal_positions.items()])

        return upper_positions, lower_positions


def list_of_trades_given_optimal_and_actual_positions(strategy_name, optimal_positions, actual_positions):
    upper_positions, _ = optimal_positions
    list_of_instruments = upper_positions.keys()
    trade_list = [trade_given_optimal_and_actual_positions(strategy_name, instrument_code, optimal_positions, actual_positions)
                       for instrument_code in list_of_instruments]

    return trade_list

def trade_given_optimal_and_actual_positions(strategy_name, instrument_code, optimal_positions, actual_positions):
    upper_positions, lower_positions = optimal_positions

    upper_for_instrument = upper_positions.get(instrument_code, 0.0)
    lower_for_instrument = lower_positions.get(instrument_code, 0.0)
    actual_for_instrument = actual_positions.get(instrument_code, 0.0)

    if actual_for_instrument<lower_for_instrument:
        required_position = round(lower_for_instrument)
    elif actual_for_instrument>upper_for_instrument:
        required_position = round(upper_for_instrument)
    else:
        required_position = actual_for_instrument

    # Might seem weird to have a zero order, but since orders can be updated it makes sense

    trade_required = required_position - actual_for_instrument

    order_required = instrumentOrder(strategy_name,instrument_code, trade_required,  type="best")

    return order_required
