import datetime
from copy import copy

import pandas as pd

from syscore.genutils import progressBar
from syscore.objects import arg_not_supplied
from systems.provided.dynamic_small_system_optimise.optimisation import objectiveFunctionForGreedy

from systems.stage import SystemStage
from systems.system_cache import diagnostic

from systems.provided.dynamic_small_system_optimise.portfolio_weights import portfolioWeightsStage

from sysquant.optimisation.weights import portfolioWeights
from sysquant.estimators.covariance import covarianceEstimate
from sysquant.estimators.mean_estimator import meanEstimates


class optimisedPositions(SystemStage):
    @property
    def name(self):
        return "optimisedPositions"

    @diagnostic()
    def get_optimised_position_df(self):
        weights_list_df = self.get_optimised_weights_df()
        per_contract_value_as_proportion_of_df = self.get_per_contract_value_as_proportion_of_capital_df()

        positions = weights_list_df / per_contract_value_as_proportion_of_df

        return positions

    @diagnostic()
    def get_optimised_weights_df(self) -> pd.DataFrame:
        self.log.msg("Optimising positions for small capital: may take a while!")
        common_index = list(self.common_index())
        p = progressBar(len(common_index), show_timings=True, show_each_time=True)
        previous_optimal_weights = portfolioWeights.allzeros(self.instrument_list())
        weights_list = []
        for relevant_date in common_index:
            #self.log.msg(relevant_date)
            optimal_weights = self.get_optimal_weights_with_fixed_contract_values(relevant_date,
                                                                                  previous_weights=previous_optimal_weights)
            weights_list.append(optimal_weights)
            previous_optimal_weights = copy(optimal_weights)
            p.iterate()
        p.finished()
        weights_list_df = pd.DataFrame(weights_list, index=common_index)

        return weights_list_df


    def get_optimal_weights_with_fixed_contract_values(self, relevant_date: datetime.datetime = arg_not_supplied,
                                                       previous_weights: portfolioWeights = arg_not_supplied,
                                                       reduce_only_keys: list = arg_not_supplied,
                                                       no_trade_keys: list = arg_not_supplied,
                                                       maximum_position_weights: portfolioWeights = arg_not_supplied) -> portfolioWeights:

        obj_instance = self.\
            _get_optimal_weights_objective_instance(
                relevant_date=relevant_date,
                previous_weights=previous_weights,
                reduce_only_keys=reduce_only_keys,
                no_trade_keys=no_trade_keys,
                maximum_position_weights=maximum_position_weights
        )

        optimal_weights = obj_instance.optimise()

        return optimal_weights


    def _get_optimal_weights_objective_instance(self,
                                                relevant_date: datetime.datetime = arg_not_supplied,
                                                       previous_weights: portfolioWeights = arg_not_supplied,
                                                       reduce_only_keys: list = arg_not_supplied,
                                                       no_trade_keys: list = arg_not_supplied,
                                                       maximum_position_weights: portfolioWeights = arg_not_supplied) -> objectiveFunctionForGreedy:

        covariance_matrix = self.get_covariance_matrix(relevant_date=relevant_date)
        per_contract_value = self.get_per_contract_value(relevant_date)
        original_portfolio_weights = self.original_portfolio_weights_for_relevant_date(relevant_date)

        covariance_matrix = covariance_matrix.clean_correlations()

        costs = self.get_costs_per_contract_as_proportion_of_capital_all_instruments()

        shadow_cost = self.shadow_cost

        obj_instance = objectiveFunctionForGreedy(
                                                weights_optimal=original_portfolio_weights,
                                                covariance_matrix=covariance_matrix,
                                                per_contract_value = per_contract_value,
                                                weights_prior=previous_weights,
                                                costs = costs,
                                                reduce_only_keys = reduce_only_keys,
                                                no_trade_keys = no_trade_keys,
                                                maximum_position_weights = maximum_position_weights,
                                                trade_shadow_cost=shadow_cost)

        return obj_instance

    @property
    def shadow_cost(self)-> float:
        shadow_cost = self.config.small_system['shadow_cost']

        return shadow_cost


    ## COSTS
    @diagnostic()
    def get_costs_per_contract_as_proportion_of_capital_all_instruments(self) -> meanEstimates:
        instrument_list = self.instrument_list()
        costs = dict([
            (instrument_code, self.get_cost_per_contract_as_proportion_of_capital(instrument_code))
            for instrument_code in instrument_list
        ])

        costs = meanEstimates(costs)

        return costs

    def get_cost_per_contract_as_proportion_of_capital(self, instrument_code)-> float:
        cost_per_contract = self.get_cost_per_contract_in_base_ccy(instrument_code)
        trading_capital = self.get_trading_capital()
        cost_multiplier = self.cost_multiplier()

        return cost_multiplier * cost_per_contract / trading_capital

    def cost_multiplier(self) -> float:
        cost_multiplier = float(self.config.small_system['cost_multiplier'])
        return cost_multiplier

    def get_cost_per_contract_in_base_ccy(self, instrument_code: str) -> float:
        raw_cost_data = self.get_raw_cost_data(instrument_code)
        multiplier = self.get_contract_multiplier(instrument_code)
        last_price= self.get_final_price(instrument_code)
        fx_rate = self.get_last_fx_rate(instrument_code)

        cost_in_instr_ccy = raw_cost_data.calculate_cost_instrument_currency(1.0, multiplier, last_price)
        cost_in_base_ccy = fx_rate * cost_in_instr_ccy

        return cost_in_base_ccy

    def get_final_price(self, instrument_code: str) -> float:
        return self.get_raw_price(instrument_code).ffill().iloc[-1]

    def get_last_fx_rate(self, instrument_code: str) -> float:
        return self.get_fx_rate(instrument_code).ffill().iloc[-1]



    ## INPUTS FROM OTHER STAGES

    def get_covariance_matrix(self,
                              relevant_date: datetime.datetime = arg_not_supplied) -> covarianceEstimate:

            return self.portfolio_weights_stage.get_covariance_matrix(relevant_date=relevant_date)

    def get_per_contract_value(self, relevant_date: datetime.datetime = arg_not_supplied):
        return self.portfolio_weights_stage.get_per_contract_value(relevant_date)

    def get_per_contract_value_as_proportion_of_capital_df(self) -> pd.DataFrame:
        return self.portfolio_weights_stage.get_per_contract_value_as_proportion_of_capital_df()

    def instrument_list(self) -> list:
        return self.parent.get_instrument_list()

    def get_instrument_weights(self) -> pd.DataFrame:
        return self.portfolio_stage.get_instrument_weights()

    def common_index(self):
        return self.portfolio_weights_stage.common_index()

    def original_portfolio_weights_for_relevant_date(self,
                                                     relevant_date: datetime.datetime = arg_not_supplied):
        return self.portfolio_weights_stage.get_portfolio_weights_for_relevant_date(relevant_date)


    def get_raw_cost_data(self, instrument_code: str):
        return self.accounts_stage().get_raw_cost_data(instrument_code)

    def get_contract_multiplier(self, instrument_code: str) -> float:
        return float(self.data.get_value_of_block_price_move(instrument_code))

    def get_raw_price(self, instrument_code: str) -> pd.Series:
        return self.data.get_raw_price(instrument_code)

    def get_fx_rate(self, instrument_code: str) -> pd.Series:
        return self.position_size_stage.get_fx_rate(instrument_code)

    def get_trading_capital(self) -> float:
        return self.position_size_stage.get_notional_trading_capital()

    ## STAGE POINTERS
    def accounts_stage(self):
        return self.parent.accounts

    @property
    def portfolio_weights_stage(self) -> portfolioWeightsStage:
        return self.parent.portfolioWeights

    @property
    def position_size_stage(self):
        return self.parent.positionSize

    @property
    def portfolio_stage(self):
        return self.parent.portfolio

    @property
    def forecast_scaling_stage(self):
        return self.parent.forecastScaleCap

    @property
    def data(self):
        return self.parent.data

    @property
    def config(self):
        return self.parent.config




