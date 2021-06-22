import datetime
from copy import copy

import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.objects import arg_not_supplied, resolve_function
from syscore.pdutils import get_row_of_df_aligned_to_weights_as_dict
from sysquant.estimators.correlations import correlationEstimate, create_boring_corr_matrix, CorrelationList
from sysquant.estimators.covariance import covarianceEstimate, covariance_from_stdev_and_correlation
from sysquant.estimators.mean_estimator import meanEstimates
from sysquant.estimators.stdev_estimator import stdevEstimates
from sysquant.optimisation.weights import portfolioWeights
from systems.provided.small_system_optimise.calculations import get_implied_expected_returns
from systems.stage import SystemStage
from systems.system_cache import diagnostic


class expectedReturnsStage(SystemStage):
    @property
    def name(self):
        return "expectedReturns"

    @diagnostic()
    def get_implied_expected_returns(self,
                                     relevant_date: datetime.datetime = arg_not_supplied) \
            -> meanEstimates:

        portfolio_weights = self.get_portfolio_weights_for_relevant_date(relevant_date)
        covariance_matrix = self.get_covariance_matrix(relevant_date=relevant_date)
        risk_aversion = self.risk_aversion_coefficient()

        expected_returns = get_implied_expected_returns(portfolio_weights=portfolio_weights,
                                                        covariance_matrix=covariance_matrix,
                                                        risk_aversion=risk_aversion)

        return expected_returns



    def get_portfolio_weights_for_relevant_date(self,
                              relevant_date: datetime.datetime = arg_not_supplied) \
            -> portfolioWeights:

        weights_as_df = self.get_original_portfolio_weight_df()
        weights_at_date = get_row_of_df_aligned_to_weights_as_dict(weights_as_df, relevant_date)

        portfolio_weights = portfolioWeights(weights_at_date)

        return portfolio_weights

    def get_covariance_matrix(self,
                              relevant_date: datetime.datetime = arg_not_supplied) \
            -> covarianceEstimate:

        correlation_estimate = \
            self.get_correlation_matrix(relevant_date=relevant_date)
        stdev_estimate = self.get_stdev_estimate(relevant_date = relevant_date)

        covariance = covariance_from_stdev_and_correlation(correlation_estimate,
                                                           stdev_estimate)

        return covariance

    def get_correlation_matrix(self,
                              relevant_date: datetime.datetime = arg_not_supplied) \
            -> correlationEstimate:
        list_of_correlations = self.get_list_of_instrument_returns_correlations()
        try:
            correlation_matrix = list_of_correlations.most_recent_correlation_before_date(relevant_date)
        except:
            instrument_list = self.instrument_list()
            correlation_matrix = create_boring_corr_matrix(len(instrument_list),
                                                           columns=instrument_list,
                                                           offdiag = 0.0)

        return correlation_matrix


    @diagnostic(not_pickable=True)
    def get_list_of_instrument_returns_correlations(self) ->CorrelationList:
        config = self.config

        # Get some useful stuff from the config
        corr_params = copy(config.small_system['instrument_returns_correlation'])

        # which function to use for calculation
        corr_func = resolve_function(corr_params.pop("func"))

        returns_as_pd = self.returns_across_instruments_as_df()

        return corr_func(returns_as_pd, **corr_params)

    @diagnostic()
    def returns_across_instruments_as_df(self) -> pd.DataFrame:
        instrument_list = self.instrument_list()
        returns_as_dict = dict([
            (instrument_code,
                self.percentage_return_for_instrument(instrument_code))
                           for instrument_code in instrument_list])

        returns_as_pd = pd.DataFrame(returns_as_dict)

        return returns_as_pd

    def percentage_return_for_instrument(self, instrument_code) -> pd.Series:
        return self.rawdata.get_daily_percentage_returns(instrument_code)

    def get_per_contract_value(self, relevant_date: datetime.datetime = arg_not_supplied) -> portfolioWeights:
        df_of_values = self.get_per_contract_value_as_proportion_of_capital_df()
        values_at_date = get_row_of_df_aligned_to_weights_as_dict(df_of_values, relevant_date)
        contract_values = portfolioWeights(values_at_date)

        return contract_values


    def get_stdev_estimate(self, relevant_date: datetime.datetime = arg_not_supplied) -> stdevEstimates:
        df_of_vol = self.get_df_of_perc_vol()
        stdev_at_date = get_row_of_df_aligned_to_weights_as_dict(df_of_vol, relevant_date)

        stdev_estimate = stdevEstimates(stdev_at_date)

        return stdev_estimate

    @diagnostic()
    def get_df_of_perc_vol(self) -> pd.DataFrame:
        instrument_list = self.instrument_list()
        vol_as_dict = dict([
            (instrument_code,
                self.annualised_percentage_vol(instrument_code))
                           for instrument_code in instrument_list])

        vol_as_pd = pd.DataFrame(vol_as_dict)

        common_index = self.common_index()
        vol_as_pd = vol_as_pd.reindex(common_index)
        vol_as_pd = vol_as_pd.ffill()

        return vol_as_pd


    def common_index(self):
        portfolio_weights = self.get_original_portfolio_weight_df()
        common_index = portfolio_weights.index

        return common_index


    @diagnostic()
    def get_original_portfolio_weight_df(self) -> pd.DataFrame:
        instrument_list = self.instrument_list()
        weights_as_dict = dict([
            (instrument_code,
                self.get_portfolio_weight_series_from_contract_positions(instrument_code))
                           for instrument_code in instrument_list])

        weights_as_pd = pd.DataFrame(weights_as_dict)
        weights_as_pd = weights_as_pd.ffill()

        return weights_as_pd


    @diagnostic()
    def get_per_contract_value_as_proportion_of_capital_df(self) -> pd.DataFrame:
        instrument_list = self.instrument_list()
        values_as_dict = dict([
            (instrument_code,
                self.get_per_contract_value_as_proportion_of_capital(instrument_code))
                           for instrument_code in instrument_list])

        values_as_pd = pd.DataFrame(values_as_dict)
        common_index = self.common_index()

        values_as_pd = values_as_pd.reindex(common_index)
        values_as_pd = values_as_pd.ffill()

        ## slight cheating
        values_as_pd = values_as_pd.bfill()

        return values_as_pd


    @diagnostic()
    def get_portfolio_weight_series_from_contract_positions(self, instrument_code: str) -> pd.Series:
        contract_positions = self.get_contract_positions(instrument_code)
        per_contract_value_as_proportion_of_capital = self.get_per_contract_value_as_proportion_of_capital(instrument_code)

        weights_as_proportion_of_capital = get_portfolio_weights_from_contract_positions(
                                                      contract_positions=contract_positions,
                                                                                per_contract_value_as_proportion_of_capital=per_contract_value_as_proportion_of_capital)
        return weights_as_proportion_of_capital

    def get_per_contract_value_as_proportion_of_capital(self, instrument_code: str)-> pd.Series:
        trading_capital = self.get_trading_capital()
        contract_values = self.get_baseccy_value_per_contract(instrument_code)

        per_contract_value_as_proportion_of_capital = contract_values / trading_capital

        return per_contract_value_as_proportion_of_capital


    def get_baseccy_value_per_contract(self, instrument_code: str) -> pd.Series:
        contract_prices = self.get_contract_prices(instrument_code)
        contract_multiplier = self.get_contract_multiplier(instrument_code)
        fx_rate = self.get_fx_for_contract(instrument_code)

        fx_rate_aligned = fx_rate.reindex(contract_prices.index, method="ffill")

        return fx_rate_aligned*contract_prices * contract_multiplier

    def annualised_percentage_vol(self, instrument_code: str) -> pd.Series:
        daily_vol = self.daily_percentage_vol_100scale(instrument_code)
        return (ROOT_BDAYS_INYEAR/100.0)*daily_vol

    def daily_percentage_vol_100scale(self, instrument_code: str) -> pd.Series:
        return self.position_size_stage.calculate_daily_percentage_vol(instrument_code)

    def get_trading_capital(self) -> float:
        return self.position_size_stage.get_notional_trading_capital()

    def get_contract_positions(self, instrument_code: str) -> pd.Series:
        return self.portfolio_stage.get_notional_position(instrument_code)

    def get_contract_prices(self, instrument_code: str) -> pd.Series:
        return self.position_size_stage.get_underlying_price(instrument_code)

    def get_contract_multiplier(self, instrument_code: str) -> float:
        return float(self.data.get_value_of_block_price_move(instrument_code))

    def get_fx_for_contract(self, instrument_code: str) -> pd.Series:
        return self.position_size_stage.get_fx_rate(instrument_code)


    @diagnostic()
    def risk_aversion_coefficient(self) -> float:
        return self.config.small_system['risk_aversion_coefficient']

    def instrument_list(self):
        return self.parent.get_instrument_list()

    @property
    def position_size_stage(self):
        return self.parent.positionSize

    @property
    def portfolio_stage(self):
        return self.parent.portfolio

    @property
    def rawdata(self):
        return self.parent.rawdata

    @property
    def data(self):
        return self.parent.data

    @property
    def config(self):
        return self.parent.config


def get_portfolio_weights_from_contract_positions(
                                                  contract_positions: pd.Series,
                                                  per_contract_value_as_proportion_of_capital: pd.Series) -> pd.Series:

    aligned_values = per_contract_value_as_proportion_of_capital.reindex(contract_positions.index, method="ffill")
    weights_as_proportion_of_capital = contract_positions * aligned_values

    return weights_as_proportion_of_capital