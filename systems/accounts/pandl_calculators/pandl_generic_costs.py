import pandas as pd

from systems.accounts.pandl_calculators.pandl_calculation import (
    pandlCalculation,
    apply_weighting,
)

curve_types = ["gross", "net", "costs"]
GROSS_CURVE = "gross"
NET_CURVE = "net"
COSTS_CURVE = "costs"


class pandlCalculationWithGenericCosts(pandlCalculation):
    def weight(self, weight: pd.Series):

        weighted_capital = apply_weighting(weight, self.capital)
        weighted_positions = apply_weighting(weight, self.positions)

        return pandlCalculationWithGenericCosts(
            self.price,
            positions=weighted_positions,
            fx=self.fx,
            capital=weighted_capital,
            value_per_point=self.value_per_point,
            roundpositions=self.roundpositions,
            delayfill=self.delayfill,
        )

    def as_pd_series(self, percent=False, curve_type=NET_CURVE):
        if curve_type == NET_CURVE:
            if percent:
                return self.net_percentage_pandl()
            else:
                return self.net_pandl_in_base_currency()

        elif curve_type == GROSS_CURVE:
            if percent:
                return self.percentage_pandl()
            else:
                return self.pandl_in_base_currency()
        elif curve_type == COSTS_CURVE:
            if percent:
                return self.costs_percentage_pandl()
            else:
                return self.costs_pandl_in_base_currency()

        else:
            raise Exception(
                "Curve type %s not recognised! Must be one of %s"
                % (curve_type, curve_types)
            )

    def net_percentage_pandl(self) -> pd.Series:
        gross = self.percentage_pandl()
        costs = self.costs_percentage_pandl()
        net = _add_gross_and_costs(gross, costs)

        return net

    def net_pandl_in_base_currency(self) -> pd.Series:
        gross = self.pandl_in_base_currency()
        costs = self.costs_pandl_in_base_currency()
        net = _add_gross_and_costs(gross, costs)

        return net

    def net_pandl_in_instrument_currency(self) -> pd.Series:
        gross = self.pandl_in_instrument_currency()
        costs = self.costs_pandl_in_instrument_currency()
        net = _add_gross_and_costs(gross, costs)

        return net

    def net_pandl_in_points(self) -> pd.Series:
        gross = self.pandl_in_points()
        costs = self.costs_pandl_in_points()
        net = _add_gross_and_costs(gross, costs)

        return net

    def costs_percentage_pandl(self) -> pd.Series:
        costs_in_base = self.costs_pandl_in_base_currency()
        costs = self._percentage_pandl_given_pandl(costs_in_base)

        return costs

    def costs_pandl_in_base_currency(self) -> pd.Series:
        costs_in_instr_ccy = self.costs_pandl_in_instrument_currency()
        costs_in_base = self._base_pandl_given_currency_pandl(costs_in_instr_ccy)

        return costs_in_base

    def costs_pandl_in_instrument_currency(self) -> pd.Series:
        costs_in_points = self.costs_pandl_in_points()
        costs_in_instr_ccy = self._pandl_in_instrument_ccy_given_points_pandl(
            costs_in_points
        )

        return costs_in_instr_ccy

    def costs_pandl_in_points(self) -> pd.Series:
        raise NotImplementedError


def _add_gross_and_costs(gross: pd.Series, costs: pd.Series):
    net = gross.add(costs, fill_value=0)

    return net
