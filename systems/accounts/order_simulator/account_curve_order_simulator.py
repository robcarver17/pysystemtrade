import pandas as pd

from systems.system_cache import diagnostic

from systems.accounts.pandl_calculators.pandl_cash_costs import (
    pandlCalculationWithCashCostsAndFills,
)

from systems.accounts.curves.account_curve import accountCurve
from systems.accounts.accounts_stage import Account
from systems.accounts.order_simulator.pandl_order_simulator import OrderSimulator


class AccountWithOrderSimulator(Account):
    @diagnostic(not_pickable=True)
    def pandl_for_subsystem(
        self, instrument_code, delayfill=True, roundpositions=True
    ) -> accountCurve:

        self.log.msg(
            "Calculating pandl for subsystem for instrument %s" % instrument_code,
            instrument_code=instrument_code,
        )

        use_SR_costs = self.use_SR_costs
        _raise_exceptions(
            roundpositions=roundpositions,
            delayfill=delayfill,
            use_SR_costs=use_SR_costs,
        )

        order_simulator = self.get_order_simulator(instrument_code, is_subsystem=False)
        price = order_simulator.prices()
        fills = order_simulator.list_of_fills()

        raw_costs = self.get_raw_cost_data(instrument_code)
        fx = self.get_fx_rate(instrument_code)
        value_of_price_point = self.get_value_of_block_price_move(instrument_code)
        capital = self.get_notional_capital()
        vol_normalise_currency_costs = self.config.vol_normalise_currency_costs
        rolls_per_year = self.get_rolls_per_year(instrument_code)

        pandl_calculator = pandlCalculationWithCashCostsAndFills(
            price,
            raw_costs=raw_costs,
            fills=fills,
            capital=capital,
            value_per_point=value_of_price_point,
            delayfill=delayfill,
            fx=fx,
            roundpositions=roundpositions,
            vol_normalise_currency_costs=vol_normalise_currency_costs,
            rolls_per_year=rolls_per_year,
        )

        account_curve = accountCurve(pandl_calculator)

        return account_curve

    @diagnostic(not_pickable=True)
    def pandl_for_instrument(
        self, instrument_code: str, delayfill: bool = True, roundpositions: bool = True
    ) -> accountCurve:
        self.log.msg(
            "Calculating pandl for instrument for %s" % instrument_code,
            instrument_code=instrument_code,
        )
        use_SR_costs = self.use_SR_costs
        _raise_exceptions(
            roundpositions=roundpositions,
            delayfill=delayfill,
            use_SR_costs=use_SR_costs,
        )

        order_simulator = self.get_order_simulator(instrument_code, is_subsystem=False)
        fills = order_simulator.list_of_fills()
        price = order_simulator.prices()

        raw_costs = self.get_raw_cost_data(instrument_code)

        fx = self.get_fx_rate(instrument_code)
        value_of_price_point = self.get_value_of_block_price_move(instrument_code)

        capital = self.get_notional_capital()

        vol_normalise_currency_costs = self.config.vol_normalise_currency_costs
        rolls_per_year = self.get_rolls_per_year(instrument_code)
        multiply_roll_costs_by = self.config.multiply_roll_costs_by

        pandl_calculator = pandlCalculationWithCashCostsAndFills(
            price,
            raw_costs=raw_costs,
            fills=fills,
            capital=capital,
            value_per_point=value_of_price_point,
            delayfill=delayfill,
            fx=fx,
            roundpositions=roundpositions,
            vol_normalise_currency_costs=vol_normalise_currency_costs,
            rolls_per_year=rolls_per_year,
            multiply_roll_costs_by=multiply_roll_costs_by,
        )

        account_curve = accountCurve(pandl_calculator, weighted=True)

        return account_curve

    @diagnostic()
    def get_buffered_position(
        self, instrument_code: str, roundpositions: bool = True
    ) -> pd.Series:
        _raise_exceptions(roundpositions=roundpositions)
        order_simulator = self.get_order_simulator(instrument_code, is_subsystem=False)

        return order_simulator.positions()

    @diagnostic()
    def get_buffered_subsystem_position(
        self, instrument_code: str, roundpositions: bool = True
    ) -> pd.Series:
        _raise_exceptions(roundpositions=roundpositions)
        order_simulator = self.get_order_simulator(instrument_code, is_subsystem=True)

        return order_simulator.positions()

    @diagnostic(not_pickable=True)
    def get_order_simulator(
        self, instrument_code, is_subsystem: bool
    ) -> OrderSimulator:
        raise NotImplemented("Need to inherit to get an order simulator")


def _raise_exceptions(
    roundpositions: bool = True, use_SR_costs: bool = False, delayfill: bool = True
):
    if not roundpositions:
        raise Exception("Have to round positions when using order simulator!")
    if not delayfill:
        raise Exception("Have to delay fills when using order simulator!")
    if use_SR_costs:
        raise Exception(
            "Have to use cash costs not SR costs when using order simulator!"
        )
