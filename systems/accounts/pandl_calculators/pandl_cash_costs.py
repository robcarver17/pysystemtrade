import pandas as pd

from syscore.objects import arg_not_supplied
from systems.accounts.pandl_calculators.pandl_calculation import pandlCalculationWithGenericCosts

from sysobjects.instruments import instrumentCosts


class pandlCalculationWithCashCosts(pandlCalculationWithGenericCosts):
    def __init__(self, *args,
                 raw_costs: instrumentCosts,
                 **kwargs):
        ## Is SR_cost a negative number?
        super().__init__(*args, **kwargs)
        self._raw_costs = raw_costs

    def costs_pandl_in_points(self) -> pd.Series:
        SR_cost_as_annualised_figure = self.SR_cost_as_annualised_figure_points()

        position = self.positions
        price = self.price

        SR_cost_per_period = calculate_SR_cost_per_period_of_position_data_match_price_index(position,
                                                                                             price=price,
                                                                           SR_cost_as_annualised_figure=SR_cost_as_annualised_figure)
    @property
    def raw_costs(self) -> instrumentCosts:
        return self._raw_costs


        return SR_cost_per_period
