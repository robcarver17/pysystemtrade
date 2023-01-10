import pandas as pd
from systems.accounts.pandl_calculators.pandl_generic_costs import (
    pandlCalculationWithGenericCosts,
)


class pandlCalculationWithoutPositions(pandlCalculationWithGenericCosts):
    def __init__(
        self,
        pandl_in_base_currency: pd.Series,
        costs_pandl_in_base_currency: pd.Series,
        capital: pd.Series,
    ):

        super().__init__(price=pd.Series(dtype="float64"), capital=capital)

        self._pandl_in_base_currency = pandl_in_base_currency
        self._costs_pandl_in_base_currency = costs_pandl_in_base_currency

    ## used for summing account curves
    def pandl_in_base_currency(self) -> pd.Series:
        return self._pandl_in_base_currency

    def costs_pandl_in_base_currency(self) -> pd.Series:
        return self._costs_pandl_in_base_currency

    def net_pandl_in_instrument_currency(self):
        raise NotImplementedError

    def pandl_in_instrument_currency(self):
        raise NotImplementedError

    def costs_pandl_in_instrument_currency(self):
        raise NotImplementedError

    def net_pandl_in_points(self):
        raise NotImplementedError

    def pandl_in_points(self):
        raise NotImplementedError

    def costs_pandl_in_points(self):
        raise NotImplementedError

    @property
    def price(self):
        raise NotImplementedError

    @property
    def positions(self):
        raise NotImplementedError

    @property
    def value_per_point(self):
        raise NotImplementedError

    @property
    def fx(self):
        raise NotImplementedError

    @property
    def _index_to_align_capital_to(self):
        return self.pandl_in_base_currency().index


class dictOfPandlCalculatorsWithGenericCosts(dict):
    def sum(self, capital) -> pandlCalculationWithoutPositions:

        pandl_in_base_currency = self.sum_of_pandl_in_base_currency()
        costs_pandl_in_base_currency = self.sum_of_costs_pandl_in_base_currency()

        pandl_calculator = pandlCalculationWithoutPositions(
            pandl_in_base_currency=pandl_in_base_currency,
            costs_pandl_in_base_currency=costs_pandl_in_base_currency,
            capital=capital,
        )

        return pandl_calculator

    def sum_of_pandl_in_base_currency(self) -> pd.Series:
        return sum_list_of_pandl_curves(self.list_of_pandl_in_base_currency)

    def sum_of_costs_pandl_in_base_currency(self) -> pd.Series:
        return sum_list_of_pandl_curves(self.list_of_costs_pandl_in_base_currency)

    @property
    def list_of_pandl_in_base_currency(self) -> list:
        return self._list_of_attr("pandl_in_base_currency")

    @property
    def list_of_costs_pandl_in_base_currency(self) -> list:
        return self._list_of_attr("costs_pandl_in_base_currency")

    def _list_of_attr(self, attr_name) -> list:
        list_of_methods = [
            getattr(pandl_item, attr_name) for pandl_item in self.values()
        ]
        list_of_attr = [x() for x in list_of_methods]

        return list_of_attr


def sum_list_of_pandl_curves(list_of_pandl_curves: list):
    df_of_pandl_curves = pd.concat(list_of_pandl_curves, axis=1, sort=True)
    summed_pandl_curve = df_of_pandl_curves.sum(axis=1)

    return summed_pandl_curve
