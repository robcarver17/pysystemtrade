"""
Strategy specific execution code

For the classic buffered strategy we just compare actual positions with optimal positions, and generate orders
  accordingly

These are 'virtual' orders, because they are per instrument. We translate that to actual contracts downstream

Desired virtual orders have to be labelled with the desired type: limit, market,best-execution
"""

from syscore.objects import missing_order

from sysexecution.instrument_orders import instrumentOrder
from sysexecution.strategies.strategy_order_handling import orderGeneratorForStrategy

from sysproduction.data.positions import dataOptimalPositions


class orderGeneratorForBufferedPositions(orderGeneratorForStrategy):
    def get_required_orders(self):
        strategy_name = self.strategy_name

        optimal_positions = self.get_optimal_positions()
        actual_positions = self.get_actual_positions_for_strategy()

        list_of_trades = list_of_trades_given_optimal_and_actual_positions(
            self.data, strategy_name, optimal_positions, actual_positions
        )

        return list_of_trades

    def get_optimal_positions(self):
        data = self.data
        strategy_name = self.strategy_name

        optimal_position_data = dataOptimalPositions(data)

        list_of_instruments = optimal_position_data.get_list_of_instruments_for_strategy_with_optimal_position(
            strategy_name)
        optimal_positions = dict(
            [
                (instrument_code,
                 optimal_position_data.get_current_optimal_position_for_strategy_and_instrument(
                     strategy_name,
                     instrument_code),
                 ) for instrument_code in list_of_instruments])

        ref_dates = dict(
            [
                (instrument_code, opt_position.date)
                for instrument_code, opt_position in optimal_positions.items()
            ]
        )

        upper_positions = dict(
            [
                (instrument_code, opt_position.upper_position)
                for instrument_code, opt_position in optimal_positions.items()
            ]
        )
        lower_positions = dict(
            [
                (instrument_code, opt_position.lower_position)
                for instrument_code, opt_position in optimal_positions.items()
            ]
        )

        reference_prices = dict(
            [
                (instrument_code, opt_position.reference_price)
                for instrument_code, opt_position in optimal_positions.items()
            ]
        )

        reference_contracts = dict(
            [
                (instrument_code, opt_position.reference_contract)
                for instrument_code, opt_position in optimal_positions.items()
            ]
        )

        return (
            upper_positions,
            lower_positions,
            reference_prices,
            reference_contracts,
            ref_dates,
        )


def list_of_trades_given_optimal_and_actual_positions(
    data, strategy_name, optimal_positions, actual_positions
):
    upper_positions, _, _, _, _ = optimal_positions
    list_of_instruments = upper_positions.keys()
    trade_list = [
        trade_given_optimal_and_actual_positions(
            data, strategy_name, instrument_code, optimal_positions, actual_positions
        )
        for instrument_code in list_of_instruments
    ]

    return trade_list


def trade_given_optimal_and_actual_positions(
    data, strategy_name, instrument_code, optimal_positions, actual_positions
):

    log = data.log.setup(
        strategy_name=strategy_name,
        instrument_code=instrument_code)
    (
        upper_positions,
        lower_positions,
        reference_prices,
        reference_contracts,
        ref_dates,
    ) = optimal_positions

    upper_for_instrument = upper_positions[instrument_code]
    lower_for_instrument = lower_positions[instrument_code]
    actual_for_instrument = actual_positions.get(instrument_code, 0.0)

    if actual_for_instrument < lower_for_instrument:
        required_position = round(lower_for_instrument)
    elif actual_for_instrument > upper_for_instrument:
        required_position = round(upper_for_instrument)
    else:
        required_position = actual_for_instrument

    # Might seem weird to have a zero order, but since orders can be updated
    # it makes sense

    trade_required = required_position - actual_for_instrument

    reference_contract = reference_contracts[instrument_code]
    reference_price = reference_prices[instrument_code]

    log.msg(
        "Upper %.2f Lower %.2f Current %d Required position %d Required trade %d Reference price %f  for contract %s" %
        (upper_for_instrument,
         lower_for_instrument,
         actual_for_instrument,
         required_position,
         trade_required,
         reference_price,
         reference_contract,
         ))

    ref_date = ref_dates[instrument_code]

    # No limit orders, just best execution
    order_required = instrumentOrder(
        strategy_name,
        instrument_code,
        trade_required,
        order_type="best",
        reference_price=reference_price,
        reference_contract=reference_contract,
        reference_datetime=ref_date,
    )

    return order_required
