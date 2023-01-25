import pandas as pd

from systems.stage import SystemStage
from systems.portfolio import Portfolios
from systems.provided.dynamic_small_system_optimise.optimised_positions_stage import (
    optimisedPositions,
)
from systems.system_cache import diagnostic

from syscore.pandas.list_of_df import listOfDataFrames

from sysquant.optimisation.weights import seriesOfPortfolioWeights


class Risk(SystemStage):
    @property
    def name(self):
        return "risk"

    @diagnostic()
    def get_portfolio_risk_for_optimised_positions(self) -> pd.Series:
        weights = self.get_optimised_weights_df()
        return self._get_portfolio_risk_given_weights(weights)

    @diagnostic()
    def get_portfolio_risk_for_original_positions_rounded_buffered(self) -> pd.Series:
        positions = self.get_original_buffered_rounded_positions_df()
        positions = positions.round()
        return self._get_portfolio_risk_given_positions(positions)

    @diagnostic()
    def get_portfolio_risk_for_original_positions(self) -> pd.Series:
        return self.portfolio_stage.get_portfolio_risk_for_original_positions()

    @diagnostic()
    def get_original_buffered_rounded_positions_df(self) -> pd.DataFrame:
        instrument_list = self.instrument_list()
        positions_dict = dict(
            [
                (
                    instrument_code,
                    self.get_original_buffered_rounded_position_for_instrument(
                        instrument_code
                    ),
                )
                for instrument_code in instrument_list
            ]
        )

        positions = pd.DataFrame(positions_dict)
        positions = positions.ffill()

        return positions

    @diagnostic()
    def get_original_buffered_rounded_position_for_instrument(
        self, instrument_code: str
    ) -> pd.Series:
        return self.accounts_stage.get_buffered_position(
            instrument_code, roundpositions=True
        )

    def _get_portfolio_risk_given_positions(self, positions: pd.DataFrame) -> pd.Series:
        weight_per_position = (
            self.portfolio_stage.get_per_contract_value_as_proportion_of_capital_df()
        )
        portfolio_weights = listOfDataFrames(
            [weight_per_position, positions]
        ).fill_and_multipy()

        portfolio_weights = seriesOfPortfolioWeights(portfolio_weights)

        return self._get_portfolio_risk_given_weights(portfolio_weights)

    def _get_portfolio_risk_given_weights(
        self, portfolio_weights: seriesOfPortfolioWeights
    ) -> pd.Series:
        return self.portfolio_stage.get_portfolio_risk_given_weights(portfolio_weights)

    def get_optimised_weights_df(self) -> seriesOfPortfolioWeights:
        return self.optimised_stage.get_optimised_weights_df()

    @property
    def optimised_stage(self) -> optimisedPositions:
        try:
            op_stage = self.parent.optimisedPositions
        except:
            raise Exception(
                "No optimisedPosition stage - not using dynamic optimisation - risk measure not appropriate"
            )

        return op_stage

    @property
    def accounts_stage(self):
        return self.parent.accounts

    @property
    def portfolio_stage(self) -> Portfolios:
        return self.parent.portfolio

    def instrument_list(self) -> list:
        return self.parent.get_instrument_list()
