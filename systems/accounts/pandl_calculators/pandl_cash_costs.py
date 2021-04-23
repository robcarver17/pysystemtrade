import pandas as pd

from systems.accounts.pandl_calculators.pandl_generic_costs import pandlCalculationWithGenericCosts
from systems.accounts.pandl_calculators.pandl_using_fills import pandlCalculationWithFills
from sysobjects.instruments import instrumentCosts

class pandlCalculationWithCashCostsAndFills(pandlCalculationWithGenericCosts, pandlCalculationWithFills):
    def __init__(self, *args,
                 raw_costs: instrumentCosts,
                 **kwargs):
        ## Is SR_cost a negative number?
        super().__init__(*args, **kwargs)
        self._raw_costs = raw_costs


    def costs_pandl_in_points(self) -> pd.Series:
        ## We work backwards since the cost calculator returns a currency cost
        costs_pandl_in_instrument_currency = self.costs_pandl_in_instrument_currency()
        block_price_multiplier = self.value_per_point
        costs_pandl_in_points = costs_pandl_in_instrument_currency / block_price_multiplier

        return costs_pandl_in_points

    def costs_pandl_in_instrument_currency(self) -> pd.Series:
        list_of_fills = self.fills

        date_index = [fill.date for fill in list_of_fills]
        instrument_currency_costs = [
            -self.calculate_cost_instrument_currency_for_a_trade(trade=fill.qty,
                                                                 price=fill.price)
                                     for fill in list_of_fills]

        costs_as_pd_series = pd.Series(instrument_currency_costs, date_index)

        return costs_as_pd_series

    def calculate_cost_instrument_currency_for_a_trade(self, trade: float, price: float) -> float:
        block_price_multiplier = self.value_per_point
        cost_for_trade = self.raw_costs.calculate_cost_instrument_currency(blocks_traded=trade,
                                                          price=price,
                                                          block_price_multiplier=block_price_multiplier)

        return cost_for_trade


    @property
    def raw_costs(self) -> instrumentCosts:
        return self._raw_costs
