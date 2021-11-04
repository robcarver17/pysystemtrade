import datetime
from copy import copy

import pandas as pd

from syscore.genutils import progressBar
from syscore.objects import arg_not_supplied
from systems.provided.dynamic_small_system_optimise.optimisation import objectiveFunctionForGreedy, constraintsForDynamicOpt
from systems.provided.dynamic_small_system_optimise.buffering import speedControlForDynamicOpt

from systems.stage import SystemStage
from systems.system_cache import diagnostic

from systems.provided.dynamic_small_system_optimise.portfolio_weights_stage import portfolioWeightsStage

from sysquant.optimisation.weights import portfolioWeights
from sysquant.estimators.covariance import covarianceEstimate
from sysquant.estimators.mean_estimator import meanEstimates


class optimisedPositions(SystemStage):
    @property
    def name(self):
        return "optimisedPositions"

    @diagnostic()
    def get_optimised_weights_df(self) -> pd.DataFrame:
        position_df = self.get_optimised_position_df()
        per_contract_value_as_proportion_of_df = self.get_per_contract_value_as_proportion_of_capital_df()

        weights = position_df * per_contract_value_as_proportion_of_df

        return weights

    @diagnostic()
    def get_optimised_position_df(self) -> pd.DataFrame:
        self.log.msg("Optimising positions for small capital: may take a while!")
        common_index = list(self.common_index())
        p = progressBar(len(common_index), show_timings=True, show_each_time=True)
        previous_optimal_positions = portfolioWeights.allzeros(self.instrument_list())
        position_list = []
        for relevant_date in common_index:
            #self.log.msg(relevant_date)
            optimal_positions = self.get_optimal_positions_with_fixed_contract_values(relevant_date,
                                                                                  previous_positions=previous_optimal_positions)
            position_list.append(optimal_positions)
            previous_optimal_positions = copy(optimal_positions)
            p.iterate()
        p.finished()
        position_df = pd.DataFrame(position_list, index=common_index)

        return position_df

    def get_optimal_positions_with_fixed_contract_values(self, relevant_date: datetime.datetime = arg_not_supplied,
                                                       previous_positions: portfolioWeights = arg_not_supplied,
                                                        constraints: constraintsForDynamicOpt = arg_not_supplied,
                                                       maximum_positions: portfolioWeights = arg_not_supplied) -> portfolioWeights:

        obj_instance = self.\
            _get_optimal_positions_objective_instance(
                relevant_date=relevant_date,
                previous_positions=previous_positions,
                constraints=constraints,
                maximum_positions = maximum_positions
        )

        optimal_positions = obj_instance.optimise_positions()

        return optimal_positions


    def _get_optimal_positions_objective_instance(self,
                                                relevant_date: datetime.datetime = arg_not_supplied,
                                                       previous_positions: portfolioWeights = arg_not_supplied,
                                                        constraints: constraintsForDynamicOpt = arg_not_supplied,
                                                       maximum_positions: portfolioWeights = arg_not_supplied) -> objectiveFunctionForGreedy:

        covariance_matrix = self.get_covariance_matrix(relevant_date=relevant_date)

        per_contract_value = self.get_per_contract_value(relevant_date)
        contracts_optimal = self.original_position_contracts_for_relevant_date(relevant_date)

        costs = self.get_costs_per_contract_as_proportion_of_capital_all_instruments()
        speed_control = self.get_speed_control()

        obj_instance = objectiveFunctionForGreedy(
                                                contracts_optimal=contracts_optimal,
                                                covariance_matrix=covariance_matrix,
                                                per_contract_value = per_contract_value,
                                                previous_positions = previous_positions,
                                                costs = costs,
                                                constraints=constraints,
                                                maximum_positions = maximum_positions,
                                                speed_control=speed_control)

        return obj_instance

    def get_speed_control(self):
        small_config = self.config.small_system
        trade_shadow_cost = small_config['shadow_cost']
        tracking_error_buffer = small_config['tracking_error_buffer']

        speed_control = speedControlForDynamicOpt(
            trade_shadow_cost=trade_shadow_cost,
            tracking_error_buffer=tracking_error_buffer
        )

        return speed_control

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

    def original_position_contracts_for_relevant_date(self,
                                                     relevant_date: datetime.datetime = arg_not_supplied):
        return self.portfolio_weights_stage.get_position_contracts_for_relevant_date(relevant_date)


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




