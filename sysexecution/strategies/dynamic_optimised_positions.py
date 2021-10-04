"""
Strategy specific execution code

For dynamic optimised position we

These are 'virtual' orders, because they are per instrument. We translate that to actual contracts downstream

Desired virtual orders have to be labelled with the desired type: limit, market,best-execution
"""
from dataclasses import dataclass
import numpy as np

from sysdata.data_blob import dataBlob
from sysdata.config.production_config import get_production_config

from sysexecution.orders.instrument_orders import instrumentOrder, best_order_type
from sysexecution.orders.list_of_orders import listOfOrders
from sysexecution.strategies.strategy_order_handling import orderGeneratorForStrategy

from sysobjects.production.tradeable_object import instrumentStrategy
from sysobjects.production.optimal_positions import optimalPositionWithDynamicCalculations
from sysobjects.production.override import Override, CLOSE_OVERRIDE, NO_TRADE_OVERRIDE, REDUCE_ONLY_OVERRIDE

from sysquant.estimators.covariance import covarianceEstimate
from sysquant.estimators.mean_estimator import meanEstimates
from sysquant.optimisation.weights import portfolioWeights

from sysproduction.data.positions import dataOptimalPositions
from sysproduction.data.controls import diagOverrides
from sysproduction.utilities.risk_metrics import get_covariance_matrix, get_perc_of_strategy_capital_for_instrument_per_contract, capital_for_strategy
from sysproduction.utilities.costs import get_cash_cost_in_base_for_instrument
from sysproduction.strategy_code.run_dynamic_optimised_system import strategy_name_with_raw_tag

from systems.provided.dynamic_small_system_optimise.optimisation import objectiveFunctionForGreedy



class orderGeneratorForDynamicPositions(orderGeneratorForStrategy):
    def get_required_orders(self) -> listOfOrders:
        strategy_name = self.strategy_name

        optimised_positions_data = self.calculate_write_and_return_optimised_positions_data()
        current_positions = self.get_actual_positions_for_strategy()

        list_of_trades = list_of_trades_given_optimised_and_actual_positions(
            self.data, strategy_name=strategy_name,
            optimised_positions_data=optimised_positions_data,
            current_positions=current_positions
        )

        return list_of_trades

    def calculate_write_and_return_optimised_positions_data(self) -> dict:
        ## We bring in
        previous_positions = self.get_actual_positions_for_strategy()
        raw_optimal_position_data = self.get_raw_optimal_position_data()

        data = self.data
        strategy_name = self.strategy_name

        optimised_positions_data = calculate_optimised_positions_data(data,
                                                                      strategy_name=strategy_name,
                                                                 previous_positions=previous_positions,
                                                                 raw_optimal_position_data=raw_optimal_position_data)

        self.write_optimised_positions_data(optimised_positions_data)

        return optimised_positions_data

    def get_raw_optimal_position_data(self) -> dict:
        # This is the 'raw' data, positions pre-optimisation
        # dict of optimalPositionWithReference

        data = self.data
        strategy_name = self.strategy_name
        raw_strategy_name = strategy_name_with_raw_tag(strategy_name)

        optimal_position_data = dataOptimalPositions(data)

        list_of_instruments = optimal_position_data.\
            get_list_of_instruments_for_strategy_with_optimal_position(
            raw_strategy_name)

        list_of_instrument_strategies = [instrumentStrategy(strategy_name=raw_strategy_name,
                                                 instrument_code=instrument_code)
            for instrument_code in list_of_instruments]

        raw_optimal_positions = dict(
            [
                (instrument_strategy.instrument_code,
                 optimal_position_data.get_current_optimal_position_for_instrument_strategy(
                    instrument_strategy),
                 ) for instrument_strategy in list_of_instrument_strategies])

        return raw_optimal_positions

    def write_optimised_positions_data(self, optimised_positions_data: dict):
        write_optimised_positions_data(self.data,
                                  strategy_name=self.strategy_name,
                                  optimised_positions_data=optimised_positions_data)

def calculate_optimised_positions_data(data: dataBlob,
                                    previous_positions: dict,
                                    strategy_name: str,
                                    raw_optimal_position_data: dict) -> dict:

    data_for_objective = get_data_for_objective_instance(data,
                                                         strategy_name=strategy_name,
                                                         previous_positions=previous_positions,
                                                         raw_optimal_position_data=raw_optimal_position_data)

    objective_function = get_objective_instance(data_for_objective)

    optimised_positions_data = get_optimised_positions_data_dict_given_optimisation(data_for_objective=data_for_objective,
                                                                               objective_function=objective_function)

    return optimised_positions_data

@dataclass
class dataForObjectiveInstance:
    weights_optimal: portfolioWeights
    positions_optimal: portfolioWeights
    covariance_matrix: covarianceEstimate
    per_contract_value: portfolioWeights
    costs: meanEstimates
    reference_prices: dict
    reference_contracts: dict
    reference_dates: dict
    weights_prior: portfolioWeights
    previous_positions: portfolioWeights
    maximum_position_weights: portfolioWeights
    maximum_position_contracts: portfolioWeights
    reduce_only_keys: list
    no_trade_keys: list
    trade_shadow_cost: float= 10


def get_data_for_objective_instance(data: dataBlob,
                                    strategy_name: str,
                                    previous_positions: dict,
                                    raw_optimal_position_data: dict) -> dataForObjectiveInstance:

    list_of_instruments = list(raw_optimal_position_data.keys())
    data.log.msg("Getting data for optimisation")

    previous_positions_as_weights_object = portfolioWeights(previous_positions)
    previous_positions_as_weights_object = previous_positions_as_weights_object.with_zero_weights_for_missing_keys(list_of_instruments)

    positions_optimal = portfolioWeights([
        (instrument_code, raw_position_entry.optimal_position)
                                        for instrument_code, raw_position_entry in raw_optimal_position_data.items()])

    reference_prices = dict([(instrument_code, raw_position_entry.reference_price)
                             for instrument_code, raw_position_entry in raw_optimal_position_data.items()])

    reference_contracts = dict([(instrument_code, raw_position_entry.reference_contract)
                             for instrument_code, raw_position_entry in raw_optimal_position_data.items()])

    reference_dates = dict([(instrument_code, raw_position_entry.reference_date)
                             for instrument_code, raw_position_entry in raw_optimal_position_data.items()])

    data.log.msg("Getting maximum positions")
    maximum_position_contracts = get_maximum_position_contracts(data,
                                                                strategy_name=strategy_name,
                                                                previous_positions=previous_positions_as_weights_object,
                                                                list_of_instruments=list_of_instruments)

    data.log.msg("Getting covariance matrix")
    covariance_matrix = get_covariance_matrix(data,
                                              list_of_instruments=list_of_instruments)

    data.log.msg("Getting per contract values")
    per_contract_value = \
        get_per_contract_values(data,
                                strategy_name = strategy_name,
                                list_of_instruments=list_of_instruments)

    data.log.msg("Getting costs")
    costs = calculate_costs_per_portfolio_weight(data,
                                                 strategy_name=strategy_name,
                                                 list_of_instruments=list_of_instruments)

    no_trade_keys = get_no_trade_keys(data,
                                      strategy_name=strategy_name,
                                      list_of_instruments=list_of_instruments)


    reduce_only_keys = get_reduce_only_keys(data,
                                            strategy_name=strategy_name,
                                            list_of_instruments=list_of_instruments)

    weights_optimal = \
        get_weights_given_positions(
                                            positions=positions_optimal,
                                            per_contract_value=per_contract_value)

    weights_prior =         get_weights_given_positions(
                                            positions=previous_positions_as_weights_object,
                                            per_contract_value=per_contract_value)


    maximum_position_weights = get_weights_given_positions(
                                            positions=maximum_position_contracts,
                                            per_contract_value=per_contract_value)

    trade_shadow_cost = get_trade_shadow_cost()

    data_for_objective = dataForObjectiveInstance(weights_optimal=weights_optimal,
                                                  positions_optimal = positions_optimal,
                                                  per_contract_value=per_contract_value,
                                                  covariance_matrix=covariance_matrix,
                                                  costs=costs,
                                                  reference_dates=reference_dates,
                                                  reference_prices=reference_prices,
                                                  reference_contracts=reference_contracts,
                                                  weights_prior=weights_prior,
                                                  previous_positions=previous_positions_as_weights_object,
                                                  maximum_position_weights=maximum_position_weights,
                                                  maximum_position_contracts=maximum_position_contracts,
                                                  reduce_only_keys=reduce_only_keys,
                                                  no_trade_keys=no_trade_keys,
                                                  trade_shadow_cost = trade_shadow_cost)


    return data_for_objective

from sysproduction.data.controls import dataPositionLimits

def get_maximum_position_contracts(data, strategy_name: str,
                                   previous_positions: dict,
                                list_of_instruments: list) ->portfolioWeights:

    maximum_position_contracts = dict([
        (instrument_code,
            get_maximum_position_contracts_for_instrument_strategy(data,
                                            instrument_strategy=
                                                instrumentStrategy(strategy_name=strategy_name,
                                                                instrument_code=instrument_code),
                                             previous_position = previous_positions.get(instrument_code, 0)
                                            )

         )
        for instrument_code in list_of_instruments
    ])

    return portfolioWeights(maximum_position_contracts)

def get_maximum_position_contracts_for_instrument_strategy(data: dataBlob,
                                                           instrument_strategy: instrumentStrategy,
                                                           previous_position: int = 0
                                                           ) -> int:

    override = get_override_for_instrument_strategy(data, instrument_strategy)
    if override == CLOSE_OVERRIDE:
        return 0

    position_limit_data = dataPositionLimits(data)
    spare = int(position_limit_data.get_spare_checking_all_position_limits(instrument_strategy))

    maximum = int(spare)+abs(previous_position)

    return maximum


def get_per_contract_values(data: dataBlob,
                        strategy_name: str,
                        list_of_instruments: list) -> portfolioWeights:

    per_contract_values = portfolioWeights(
        [
            (instrument_code,
             get_perc_of_strategy_capital_for_instrument_per_contract(data,
                                                                      strategy_name=strategy_name,
                                                                      instrument_code=instrument_code))
            for instrument_code in list_of_instruments
        ]
    )

    return per_contract_values

def calculate_costs_per_portfolio_weight(data: dataBlob,
                                         strategy_name: str,
                                        list_of_instruments: list) -> meanEstimates:

    capital = capital_for_strategy(data, strategy_name=strategy_name)
    costs = meanEstimates([
        (instrument_code,
         get_cash_cost_in_base_for_instrument(data, instrument_code) / capital)

        for instrument_code in list_of_instruments
    ])

    return costs


def get_no_trade_keys(data: dataBlob,
                      strategy_name: str,
                    list_of_instruments: list) -> list:

    no_trade_keys = [instrument_code for instrument_code in list_of_instruments
                     if get_override_for_instrument_strategy(data,
                                                    instrument_strategy=
                                                        instrumentStrategy(
                                                            instrument_code=instrument_code,
                                                            strategy_name=strategy_name)
                                                             )
                     == NO_TRADE_OVERRIDE]

    return no_trade_keys


def get_reduce_only_keys(data: dataBlob,
                         strategy_name: str,
                        list_of_instruments: list) -> list:
    no_trade_keys = [instrument_code for instrument_code in list_of_instruments
                     if get_override_for_instrument_strategy(data,
                                                    instrument_strategy=
                                                        instrumentStrategy(
                                                            instrument_code=instrument_code,
                                                            strategy_name=strategy_name)
                                                             )
                     == REDUCE_ONLY_OVERRIDE]


    return no_trade_keys


def get_override_for_instrument_strategy(data: dataBlob,
                                         instrument_strategy: instrumentStrategy) -> Override:

    diag_overrides = diagOverrides(data)
    override = diag_overrides.get_cumulative_override_for_instrument_strategy(instrument_strategy)

    return override


def get_weights_given_positions(
                                positions: portfolioWeights,
                                per_contract_value: portfolioWeights) -> portfolioWeights:

    instrument_list = list(positions.keys())
    np_positions = np.array(positions.as_list_given_keys(instrument_list))
    np_values =  np.array(per_contract_value.as_list_given_keys(instrument_list))

    weights = np_positions * np_values

    return portfolioWeights.from_weights_and_keys(list_of_weights=list(weights),
                                                  list_of_keys=instrument_list)

def get_trade_shadow_cost() -> float:
    config = get_production_config()
    shadow_cost = getattr(config, "shadow_cost", 10.0)

    return shadow_cost


def get_objective_instance(data_for_objective: dataForObjectiveInstance)\
        -> objectiveFunctionForGreedy:

    objective_function= objectiveFunctionForGreedy(weights_optimal=data_for_objective.weights_optimal,
                        covariance_matrix=data_for_objective.covariance_matrix,
                        costs=data_for_objective.costs,
                        trade_shadow_cost=data_for_objective.trade_shadow_cost,
                        weights_prior=data_for_objective.weights_prior,
                        reduce_only_keys=data_for_objective.reduce_only_keys,
                        no_trade_keys=data_for_objective.no_trade_keys,
                        maximum_position_weights=data_for_objective.maximum_position_weights,
                        per_contract_value=data_for_objective.per_contract_value
                        )

    return objective_function

def get_optimised_positions_data_dict_given_optimisation(data_for_objective: dataForObjectiveInstance,
                                                         objective_function: objectiveFunctionForGreedy
                                                         ) -> dict:

    optimised_position_weights = objective_function.optimise()
    optimised_positions = get_positions_given_weights(optimised_position_weights,
                                                      per_contract_value=data_for_objective.per_contract_value)
    instrument_list = list(optimised_position_weights.keys())

    minima_weights = portfolioWeights.from_weights_and_keys(list_of_keys=instrument_list,
                                                    list_of_weights=list(objective_function.minima_as_np))
    maxima_weights = portfolioWeights.from_weights_and_keys(list_of_keys=instrument_list,
                                                    list_of_weights=list(objective_function.maxima_as_np))
    starting_weights = portfolioWeights.from_weights_and_keys(list_of_keys=instrument_list,
                                                              list_of_weights=list(objective_function.starting_weights_as_np()))

    data_dict = dict(
        [
            (instrument_code,
             get_optimal_position_entry_with_calcs_for_code(
                 instrument_code=instrument_code,
                 data_for_objective=data_for_objective,
                 optimised_position_weights=optimised_position_weights,
                 optimised_positions = optimised_positions,
                 maxima_weights=maxima_weights,
                 starting_weights=starting_weights,
                minima_weights = minima_weights
                )
             )

            for instrument_code in instrument_list
        ]
    )

    return data_dict

def get_positions_given_weights(
                                weights: portfolioWeights,
                                per_contract_value: portfolioWeights) -> portfolioWeights:

    instrument_list = list(weights.keys())
    np_weights = np.array(weights.as_list_given_keys(instrument_list))
    np_values =  np.array(per_contract_value.as_list_given_keys(instrument_list))

    np_positions = np_weights / np_values
    positions = list(np_positions)
    positions = [int(pos) for pos in positions]

    return portfolioWeights.from_weights_and_keys(list_of_weights=positions,
                                                  list_of_keys=instrument_list)

def get_optimal_position_entry_with_calcs_for_code(
        instrument_code: str,
            data_for_objective: dataForObjectiveInstance,
            optimised_position_weights: portfolioWeights,
        optimised_positions: portfolioWeights,
        minima_weights: portfolioWeights,
        maxima_weights: portfolioWeights,
        starting_weights: portfolioWeights

)-> optimalPositionWithDynamicCalculations:
    return \
        optimalPositionWithDynamicCalculations(

        data_for_objective.reference_prices[instrument_code],
        data_for_objective.reference_contracts[instrument_code],
        data_for_objective.reference_dates[instrument_code],
        data_for_objective.positions_optimal[instrument_code],

        data_for_objective.per_contract_value[instrument_code],
        data_for_objective.previous_positions[instrument_code],
        data_for_objective.weights_prior[instrument_code],
        instrument_code in data_for_objective.reduce_only_keys,

        instrument_code in data_for_objective.no_trade_keys,

        data_for_objective.maximum_position_contracts[instrument_code],
        data_for_objective.maximum_position_weights[instrument_code],
        data_for_objective.weights_optimal[instrument_code],

        minima_weights[instrument_code],
        maxima_weights[instrument_code],
        starting_weights[instrument_code],
        optimised_position_weights[instrument_code],
        optimised_positions[instrument_code]

    )


def write_optimised_positions_data(data: dataBlob,
                              strategy_name: str,
                              optimised_positions_data: dict):

    for instrument_code,optimised_position_entry  in optimised_positions_data.items():
        write_optimised_positions_data_for_code(data,
                                                strategy_name=strategy_name,
                                                instrument_code=instrument_code,
                                                optimised_position_entry=optimised_position_entry)

def write_optimised_positions_data_for_code(data: dataBlob,
                                            strategy_name: str,
                                            instrument_code: str,
                                            optimised_position_entry: optimalPositionWithDynamicCalculations):

    data_optimal_positions = dataOptimalPositions(data)
    instrument_strategy = instrumentStrategy(instrument_code=instrument_code,
                                             strategy_name=strategy_name)

    data.log.msg("Adding optimal position for %s of %s" % (str(instrument_strategy), optimised_position_entry.verbose_repr()))
    data_optimal_positions. \
        update_optimal_position_for_instrument_strategy(
        instrument_strategy=instrument_strategy,
        position_entry=optimised_position_entry)


def list_of_trades_given_optimised_and_actual_positions(
    data: dataBlob,
        strategy_name: str,
        optimised_positions_data: dict,
        current_positions: dict
) -> listOfOrders:

    list_of_instruments = optimised_positions_data.keys()
    trade_list = [
        trade_given_optimal_and_actual_positions(
            data, strategy_name=strategy_name,
            instrument_code=instrument_code,
            optimised_position_entry=optimised_positions_data[instrument_code],
            current_position=current_positions.get(instrument_code,0)
        )
        for instrument_code in list_of_instruments
    ]

    trade_list = listOfOrders(trade_list)

    return trade_list


def trade_given_optimal_and_actual_positions(
    data: dataBlob,
        strategy_name: str,
        instrument_code: str,
        optimised_position_entry: optimalPositionWithDynamicCalculations,
        current_position: int
) -> instrumentOrder:

    optimised_position = optimised_position_entry.optimised_position

    trade_required = optimised_position - current_position

    reference_contract = optimised_position_entry.reference_contract
    reference_price = optimised_position_entry.reference_price
    reference_date = optimised_position_entry.reference_date

    # No limit orders, just best execution
    order_required = instrumentOrder(
        strategy_name,
        instrument_code,
        trade_required,
        order_type=best_order_type,
        reference_price=reference_price,
        reference_contract=reference_contract,
        reference_datetime=reference_date,
    )

    log = order_required.log_with_attributes(data.log)
    log.msg(
        "Current %d Required position %d Required trade %d Reference price %f  for contract %s" %
        (current_position,
         optimised_position,
         trade_required,
         reference_price,
         reference_contract,
         ))

    return order_required
