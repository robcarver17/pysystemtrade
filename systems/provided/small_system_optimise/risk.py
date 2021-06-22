import datetime
import numpy as np
import pandas as pd
from syscore.genutils import progressBar

from systems.stage import SystemStage
from systems.system_cache import diagnostic

from syscore.objects import arg_not_supplied
from syscore.pdutils import listOfDataFrames, get_row_of_df_aligned_to_weights_as_dict

from systems.provided.small_system_optimise.expected_returns import expectedReturnsStage

from sysquant.optimisation.shared import variance
from sysquant.optimisation.weights import portfolioWeights
from sysquant.estimators.covariance import covarianceEstimate

class Risk(SystemStage):
    @property
    def name(self):
        return "risk"

    @diagnostic()
    def get_portfolio_risk_for_optimised_positions(self) -> pd.Series:
        weights = self.get_optimised_weights_df()
        return self._get_portfolio_risk_given_weights(weights)

    @diagnostic()
    def get_portfolio_risk_for_original_positions(self) -> pd.Series:
        weights = self.get_original_portfolio_weight_df()
        return self._get_portfolio_risk_given_weights(weights)

    def  get_original_portfolio_weight_df(self) -> pd.DataFrame:
        return self.expected_returns_stage.get_original_portfolio_weight_df()

    @diagnostic()
    def get_portfolio_risk_for_original_positions_rounded_buffered(self) -> pd.Series:
        positions = self.get_original_buffered_rounded_positions_df()
        positions = positions.round()
        return self._get_portfolio_risk_given_positions(positions)

    @diagnostic()
    def get_original_buffered_rounded_positions_df(self) -> pd.DataFrame:
        instrument_list = self.instrument_list()
        positions_dict = dict([
            (instrument_code,
             self.get_original_buffered_rounded_position_for_instrument(instrument_code))
            for instrument_code in instrument_list
        ])

        positions = pd.DataFrame(positions_dict)
        positions = positions.ffill()

        return positions

    @diagnostic()
    def get_original_buffered_rounded_position_for_instrument(self, instrument_code: str):
        return self.accounts_stage.get_buffered_position(instrument_code, roundpositions=True)

    def _get_portfolio_risk_given_positions(self, positions: pd.DataFrame) -> pd.Series:
        weight_per_position = self.expected_returns_stage.get_per_contract_value_as_proportion_of_capital_df()
        portfolio_weights = listOfDataFrames([weight_per_position, positions]).fill_and_multipy()

        return self._get_portfolio_risk_given_weights(portfolio_weights)

    def _get_portfolio_risk_given_weights(self, portfolio_weights: pd.DataFrame) -> pd.Series:
        risk_series = []
        common_index = self.common_index()
        p = progressBar(len(common_index), show_timings=True, show_each_time=False)

        for relevant_date in common_index:
            p.iterate()
            weights_on_date = portfolioWeights(
                get_row_of_df_aligned_to_weights_as_dict(portfolio_weights, relevant_date))
            covariance = self.get_covariance_matrix(relevant_date)
            risk_on_date = calculate_risk(weights = weights_on_date,
                                          covariance = covariance)
            risk_series.append(risk_on_date)

        p.finished()
        risk_series = pd.Series(risk_series, common_index)

        return risk_series

    def get_covariance_matrix(self,
                              relevant_date: datetime.datetime = arg_not_supplied) -> covarianceEstimate:

            return self.expected_returns_stage.get_covariance_matrix(relevant_date=relevant_date)

    def common_index(self):
        return self.expected_returns_stage.common_index()

    def get_optimised_weights_df(self):
        return self.optimised_stage.get_optimised_weights_df()

    @property
    def optimised_stage(self):
        return self.parent.optimisedPositions

    @property
    def accounts_stage(self):
        return self.parent.accounts

    @property
    def expected_returns_stage(self) -> expectedReturnsStage:
        return self.parent.expectedReturns

    def instrument_list(self) -> list:
        return self.parent.get_instrument_list()


def calculate_risk(weights: portfolioWeights, covariance: covarianceEstimate):
    covariance_with_valid_data = covariance.without_missing_data()
    list_of_instruments = covariance_with_valid_data.columns
    if len(list_of_instruments)==0:
        return np.nan
    list_of_weights = weights.as_list_given_keys(list_of_instruments)
    variance_estimate = variance(weights=np.array(list_of_weights),
                                 sigma = covariance_with_valid_data.values)

    return variance_estimate**.5