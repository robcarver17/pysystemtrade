import datetime
from copy import copy

import pandas as pd

from sysquant.estimators.stdev_estimator import stdevEstimates
from sysquant.estimators.correlations import (
    correlationEstimate,
)
from sysquant.estimators.covariance import (
    covariance_from_stdev_and_correlation,
)
from syscore.interactive.progress_bar import progressBar
from syscore.constants import arg_not_supplied
from syscore.pandas.find_data import get_row_of_series
from syscore.pandas.strategy_functions import calculate_cost_deflator
from systems.provided.dynamic_small_system_optimise.optimisation import (
    objectiveFunctionForGreedy,
    constraintsForDynamicOpt,
)
from systems.provided.dynamic_small_system_optimise.buffering import (
    speedControlForDynamicOpt,
)

from systems.stage import SystemStage
from systems.system_cache import diagnostic

from systems.portfolio import Portfolios

from sysquant.optimisation.weights import portfolioWeights, seriesOfPortfolioWeights
from sysquant.estimators.covariance import covarianceEstimate
from sysquant.estimators.mean_estimator import meanEstimates


class optimisedPositions(SystemStage):
    @property
    def name(self):
        return "optimisedPositions"

    @diagnostic()
    def get_optimised_weights_df(self) -> seriesOfPortfolioWeights:
        position_df = self.get_optimised_position_df()
        per_contract_value_as_proportion_of_df = (
            self.get_per_contract_value_as_proportion_of_capital_df()
        )

        weights_as_df = position_df * per_contract_value_as_proportion_of_df
        weights = seriesOfPortfolioWeights(weights_as_df)

        return weights

    @diagnostic()
    def get_optimised_position_df(self) -> pd.DataFrame:
        self.log.msg("Optimising positions for small capital: may take a while!")
        common_index = list(self.common_index())
        progress = progressBar(
            len(common_index),
            suffix="Optimising positions",
            show_each_time=True,
            show_timings=True,
        )
        previous_optimal_positions = portfolioWeights.allzeros(self.instrument_list())
        position_list = []
        for relevant_date in common_index:
            # self.log.msg(relevant_date)
            optimal_positions = self.get_optimal_positions_with_fixed_contract_values(
                relevant_date, previous_positions=previous_optimal_positions
            )
            position_list.append(optimal_positions)
            previous_optimal_positions = copy(optimal_positions)
            progress.iterate()
        progress.close()
        position_df = pd.DataFrame(position_list, index=common_index)

        return position_df

    def get_optimal_positions_with_fixed_contract_values(
        self,
        relevant_date: datetime.datetime = arg_not_supplied,
        previous_positions: portfolioWeights = arg_not_supplied,
        maximum_positions: portfolioWeights = arg_not_supplied,
    ) -> portfolioWeights:

        obj_instance = self._get_optimal_positions_objective_instance(
            relevant_date=relevant_date,
            previous_positions=previous_positions,
            maximum_positions=maximum_positions,
        )

        try:
            optimal_positions = obj_instance.optimise_positions()
        except Exception as e:
            msg = "Error %s when optimising at %s with previous positions %s" % (
                str(e),
                str(relevant_date),
                str(previous_positions),
            )
            print(msg)
            return previous_positions

        return optimal_positions

    def _get_optimal_positions_objective_instance(
        self,
        relevant_date: datetime.datetime = arg_not_supplied,
        previous_positions: portfolioWeights = arg_not_supplied,
        maximum_positions: portfolioWeights = arg_not_supplied,
    ) -> objectiveFunctionForGreedy:

        covariance_matrix = self.get_covariance_matrix(relevant_date=relevant_date)

        per_contract_value = self.get_per_contract_value(relevant_date)
        contracts_optimal = self.original_position_contracts_for_relevant_date(
            relevant_date
        )

        costs = self.get_costs_per_contract_as_proportion_of_capital_all_instruments(
            relevant_date
        )
        speed_control = self.get_speed_control()
        constraints = self.get_constraints()

        obj_instance = objectiveFunctionForGreedy(
            contracts_optimal=contracts_optimal,
            covariance_matrix=covariance_matrix,
            per_contract_value=per_contract_value,
            previous_positions=previous_positions,
            costs=costs,
            constraints=constraints,
            maximum_positions=maximum_positions,
            speed_control=speed_control,
        )

        return obj_instance

    def get_constraints(self) -> constraintsForDynamicOpt:
        ## 'reduce only' is as good as do not trade in backtesting
        ## but we use this rather than 'don't trade' for consistency with production
        reduce_only_keys = self.get_reduce_only_instruments()

        return constraintsForDynamicOpt(reduce_only_keys=reduce_only_keys)

    @diagnostic()
    def get_reduce_only_instruments(self) -> list:
        reduce_only_keys = self.parent.get_list_of_markets_not_trading_but_with_data()

        return reduce_only_keys

    def get_speed_control(self):
        small_config = self.config.small_system
        trade_shadow_cost = small_config["shadow_cost"]
        tracking_error_buffer = small_config["tracking_error_buffer"]

        speed_control = speedControlForDynamicOpt(
            trade_shadow_cost=trade_shadow_cost,
            tracking_error_buffer=tracking_error_buffer,
        )

        return speed_control

    ## COSTS
    @diagnostic()
    def get_costs_per_contract_as_proportion_of_capital_all_instruments(
        self, relevant_date: arg_not_supplied
    ) -> meanEstimates:
        instrument_list = self.instrument_list()
        costs = dict(
            [
                (
                    instrument_code,
                    self.get_cost_per_contract_as_proportion_of_capital_on_date(
                        instrument_code, relevant_date=relevant_date
                    ),
                )
                for instrument_code in instrument_list
            ]
        )

        costs = meanEstimates(costs)

        return costs

    def get_cost_per_contract_as_proportion_of_capital_on_date(
        self, instrument_code, relevant_date: datetime.datetime = arg_not_supplied
    ) -> float:
        cost_deflator = self.get_cost_deflator_on_date(
            instrument_code, relevant_date=relevant_date
        )
        cost_per_notional_weight_as_proportion_of_capital = (
            self.get_cost_per_notional_weight_as_proportion_of_capital(instrument_code)
        )
        deflated_cost = (
            cost_per_notional_weight_as_proportion_of_capital * cost_deflator
        )

        return deflated_cost

    def get_cost_deflator_on_date(
        self, instrument_code: str, relevant_date: datetime.datetime = arg_not_supplied
    ) -> float:
        deflator = self.get_cost_deflator(instrument_code)

        return get_row_of_series(deflator, relevant_date)

    @diagnostic()
    def get_cost_deflator(self, instrument_code: str):
        price = self.get_raw_price(instrument_code)
        deflator = calculate_cost_deflator(price)
        deflator = deflator.reindex(self.common_index()).ffill()
        deflator[deflator.isna()] = 10000.0

        return deflator

    @diagnostic()
    def get_cost_per_notional_weight_as_proportion_of_capital(
        self, instrument_code
    ) -> float:
        cost_per_contract = self.get_cost_per_contract_in_base_ccy(instrument_code)
        cost_multiplier = self.cost_multiplier()
        notional_value_per_contract_as_proportion_of_capital = (
            self.get_current_contract_value_as_proportion_of_capital_for_instrument(
                instrument_code
            )
        )
        capital = self.get_trading_capital()
        cost_per_notional_weight_as_proportion_of_capital = calculate_cost_per_notional_weight_as_proportion_of_capital(
            cost_per_contract=cost_per_contract,
            cost_multiplier=cost_multiplier,
            notional_value_per_contract_as_proportion_of_capital=notional_value_per_contract_as_proportion_of_capital,
            capital=capital,
        )

        return cost_per_notional_weight_as_proportion_of_capital

    def cost_multiplier(self) -> float:
        cost_multiplier = float(self.config.small_system["cost_multiplier"])
        return cost_multiplier

    def get_cost_per_contract_in_base_ccy(self, instrument_code: str) -> float:
        raw_cost_data = self.get_raw_cost_data(instrument_code)
        multiplier = self.get_contract_multiplier(instrument_code)
        last_price = self.get_final_price(instrument_code)
        fx_rate = self.get_last_fx_rate(instrument_code)

        cost_in_instr_ccy = raw_cost_data.calculate_cost_instrument_currency(
            1.0, multiplier, last_price
        )
        cost_in_base_ccy = fx_rate * cost_in_instr_ccy

        return cost_in_base_ccy

    def get_final_price(self, instrument_code: str) -> float:
        return self.get_raw_price(instrument_code).ffill().iloc[-1]

    def get_last_fx_rate(self, instrument_code: str) -> float:
        return self.get_fx_rate(instrument_code).ffill().iloc[-1]

    ## INPUTS FROM OTHER STAGES

    def get_covariance_matrix(
        self, relevant_date: datetime.datetime = arg_not_supplied
    ) -> covarianceEstimate:

        correlation_estimate = self.get_correlation_matrix(relevant_date=relevant_date)

        stdev_estimate = self.get_stdev_estimate(relevant_date=relevant_date)

        covariance = covariance_from_stdev_and_correlation(
            correlation_estimate, stdev_estimate
        )

        return covariance

    def get_correlation_matrix(
        self, relevant_date: datetime.datetime = arg_not_supplied
    ) -> correlationEstimate:

        corr_matrix = self.portfolio_stage.get_correlation_matrix(
            relevant_date=relevant_date
        )
        corr_matrix = copy(
            corr_matrix.shrink_to_offdiag(
                shrinkage_corr=self.correlation_shrinkage, offdiag=0.0
            )
        )

        return corr_matrix

    @property
    def correlation_shrinkage(self) -> float:
        correlation_shrinkage = float(
            self.config.small_system["shrink_instrument_returns_correlation"]
        )
        return correlation_shrinkage

    def get_stdev_estimate(
        self, relevant_date: datetime.datetime = arg_not_supplied
    ) -> stdevEstimates:

        return self.portfolio_stage.get_stdev_estimate(relevant_date=relevant_date)

    def get_per_contract_value(
        self, relevant_date: datetime.datetime = arg_not_supplied
    ):
        return self.portfolio_stage.get_per_contract_value(relevant_date)

    def get_current_contract_value_as_proportion_of_capital_for_instrument(
        self, instrument_code: str
    ) -> float:

        value_as_ts = (
            self.get_contract_ts_value_as_proportion_of_capital_for_instrument(
                instrument_code
            )
        )
        return value_as_ts.ffill().iloc[-1]

    def get_contract_ts_value_as_proportion_of_capital_for_instrument(
        self, instrument_code: str
    ) -> pd.Series:

        return self.portfolio_stage.get_per_contract_value_as_proportion_of_capital(
            instrument_code
        )

    def get_per_contract_value_as_proportion_of_capital_df(self) -> pd.DataFrame:
        return self.portfolio_stage.get_per_contract_value_as_proportion_of_capital_df()

    def instrument_list(self) -> list:
        return self.parent.get_instrument_list()

    def get_instrument_weights(self) -> pd.DataFrame:
        return self.portfolio_stage.get_instrument_weights()

    def common_index(self):
        return self.portfolio_stage.common_index()

    def original_position_contracts_for_relevant_date(
        self, relevant_date: datetime.datetime = arg_not_supplied
    ):
        return self.portfolio_stage.get_position_contracts_for_relevant_date(
            relevant_date
        )

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
    def position_size_stage(self):
        return self.parent.positionSize

    @property
    def portfolio_stage(self) -> Portfolios:
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


def calculate_cost_per_notional_weight_as_proportion_of_capital(
    notional_value_per_contract_as_proportion_of_capital: float,
    cost_per_contract: float,
    capital: float,
    cost_multiplier: float = 1.0,
) -> float:

    dollar_cost = (
        cost_multiplier
        * cost_per_contract
        / notional_value_per_contract_as_proportion_of_capital
    )

    return dollar_cost / capital
