import itertools
from concurrent.futures.process import ProcessPoolExecutor

import numpy as np
from scipy.optimize import minimize

from syscore.objects import arg_not_supplied
from sysquant.estimators.covariance import covarianceEstimate
from sysquant.estimators.mean_estimator import meanEstimates
from sysquant.optimisation.shared import variance
from sysquant.optimisation.weights import portfolioWeights
from systems.provided.small_system_optimise.grid import gridParameters, generate_grid
from systems.provided.small_system_optimise.optimisation_kernel import neg_return_with_risk_penalty_and_costs, optimisationParameters


def get_implied_expected_returns(portfolio_weights: portfolioWeights,
                        covariance_matrix: covarianceEstimate,
                        risk_aversion: float = 2.0) -> meanEstimates:

    ## need to make sure things are aligned
    covariance_with_valid_data = covariance_matrix.without_missing_data()
    list_of_instruments = covariance_with_valid_data.columns

    covariance_as_np_array = covariance_with_valid_data.values
    aligned_weights = portfolio_weights.as_list_given_keys(list_of_instruments)
    aligned_weights_as_np = np.array(aligned_weights)

    expected_returns_as_np = calculate_implied_expected_returns_given_np(aligned_weights_as_np=aligned_weights_as_np,
                                                                         covariance_as_np_array = covariance_as_np_array,
                                                                         risk_aversion=risk_aversion)

    expected_returns_as_dict = dict([
        (instrument_code, expected_return)
        for instrument_code, expected_return in zip(list_of_instruments, expected_returns_as_np)
    ])

    return meanEstimates(expected_returns_as_dict)


def calculate_implied_expected_returns_given_np(aligned_weights_as_np: np.array,
                                                covariance_as_np_array: np.array,
                                                risk_aversion: float = 2.0):

    expected_returns_as_np = risk_aversion*aligned_weights_as_np.dot(covariance_as_np_array)

    return expected_returns_as_np


def maximise_without_discrete_weights(expected_returns: meanEstimates,
                                                        covariance_matrix: covarianceEstimate,
                                                            risk_aversion: float):

    missing_instruments = covariance_matrix.assets_with_missing_data()
    covariance_with_valid_data = covariance_matrix.without_missing_data()
    list_of_instruments = covariance_with_valid_data.columns
    if len(list_of_instruments)==0:
        weight_list = []
    else:
        expected_returns_as_list = expected_returns.list_in_key_order(list_of_instruments)
        covariance_as_np = covariance_with_valid_data.values

        weight_list = optimise_from_covariance_and_expected_returns_with_risk_coefficient(
            covariance_as_np = covariance_as_np,
            expected_returns_as_list=expected_returns_as_list,
            risk_aversion=risk_aversion
        )

    weights = portfolioWeights([
        (key, weight) for key,weight in zip(list_of_instruments, weight_list)
    ])

    weights = weights.with_zero_weights_for_missing_keys(missing_instruments)

    return weights


def optimise_from_covariance_and_expected_returns_with_risk_coefficient(
        covariance_as_np: np.array,
             expected_returns_as_list: list,
        risk_aversion: float) -> list:

    mus = np.array(expected_returns_as_list, ndmin=2).transpose()
    number_assets = covariance_as_np.shape[1]
    start_weights = [0.0] * number_assets

    ans = minimize(
        neg_return_with_risk_penalty,
        start_weights,
        (covariance_as_np, mus, risk_aversion),
        method="SLSQP",
        tol=0.000000001,
    )

    # anything that had a nan will now have a zero weight
    weights = ans["x"]

    return weights


def neg_return_with_risk_penalty(weights: np.array,
           covariance_as_np: np.array,
           mus: np.array,
                                 risk_aversion: float):
    estreturn = weights.dot(mus)

    risk_penalty = risk_aversion * variance(weights, covariance_as_np) /2.0

    return -(estreturn - risk_penalty)


NO_RISK_LIMIT = 99999


def optimise_with_fixed_contract_values(per_contract_value: portfolioWeights,
                                                        expected_returns: meanEstimates,
                                                        covariance_matrix: covarianceEstimate,
                                                            risk_aversion: float,
                                                        max_portfolio_weights: portfolioWeights,
                                                    original_portfolio_weights: portfolioWeights,
                                        costs: meanEstimates,
                                        use_process_pool: bool = False,
                                        max_risk_as_variance:float = NO_RISK_LIMIT,
                                        previous_weights: portfolioWeights = arg_not_supplied)\
        -> portfolioWeights:

    missing_instruments = covariance_matrix.assets_with_missing_data()
    list_of_instruments = covariance_matrix.assets_with_data()

    grid_parameters = gridParameters(list_of_instruments=list_of_instruments,
                                     max_portfolio_weights=max_portfolio_weights,
                                     original_portfolio_weights=original_portfolio_weights,
                                     per_contract_value=per_contract_value)

    optimisation_parameters = build_optimisation_parameters(list_of_instruments = list_of_instruments,
                                    per_contract_value = per_contract_value,
                                    expected_returns = expected_returns,
                                    covariance_matrix = covariance_matrix,
                                    risk_aversion = risk_aversion,
                                    costs = costs,
                                    max_risk_as_variance = max_risk_as_variance,
                                    previous_weights = previous_weights)

    weight_list = grid_search_optimise_with_fixed_contract_values_and_processed_inputs(
                                                                            grid_parameters=grid_parameters,
                                                                        optimisation_parameters=optimisation_parameters,
                                                                        use_process_pool = use_process_pool)

    weights = portfolioWeights([
        (key, weight) for key,weight in zip(list_of_instruments, weight_list)
    ])

    weights = weights.with_zero_weights_for_missing_keys(missing_instruments)

    return weights


def build_optimisation_parameters(list_of_instruments: list,
                                    per_contract_value: portfolioWeights,
                                    expected_returns: meanEstimates,
                                    covariance_matrix : covarianceEstimate,
                                    risk_aversion: float,
                                    costs: meanEstimates,
                                    max_risk_as_variance:float = NO_RISK_LIMIT,
                                    previous_weights: portfolioWeights = arg_not_supplied)\
        -> optimisationParameters:

    covariance_with_valid_data =covariance_matrix.subset(list_of_instruments)
    covariance_as_np = covariance_with_valid_data.values

    expected_returns_as_list = expected_returns.list_in_key_order(list_of_instruments)
    mus = np.array(expected_returns_as_list, ndmin=2).transpose()

    cost_as_np_in_portfolio_weight_terms = calculate_costs_as_np(list_of_instruments=list_of_instruments,
                                                                 per_contract_value=per_contract_value,
                                                                 costs=costs)

    if previous_weights is not arg_not_supplied:
        previous_weights_as_np = np.array(previous_weights.as_list_given_keys(list_of_instruments))
    else:
        previous_weights_as_np = arg_not_supplied

    optimisation_parameters = optimisationParameters(mus=mus,
                                                     risk_aversion=risk_aversion,
                                                     covariance_as_np=covariance_as_np,
                                                     max_risk_as_variance=max_risk_as_variance,
                                                     cost_as_np_in_portfolio_weight_terms=cost_as_np_in_portfolio_weight_terms,
                                                     previous_weights_as_np=previous_weights_as_np)

    return optimisation_parameters

def calculate_costs_as_np(list_of_instruments: list,
                                    per_contract_value: portfolioWeights,
                                    costs: meanEstimates) -> np.array:

    per_contract_value_as_list = per_contract_value.as_list_given_keys(list_of_instruments)

    # these are the costs to trade contract in pw terms
    # so 0.0001 means we pay 0.01% of our capital, eg 0.01% of $100K which is $10
    costs_as_list = costs.list_in_key_order(list_of_instruments)

    # But we want to know the cost of changing our portfolio weights eg cost per 100% of portfolio weight
    # If one contract is worth 10% of our portfolio then to trade 100% will cost $100 or 0.1% of capital

    # Expected returns are annual, costs happen over a single day
    # We should multiply costs by the number of times we expect to trade in a year
    ## cost = (cost as proportion of capital per contract) * contracts traded = (cost pppc) * (portfolio weight traded / value per contract) = (cost ppppc / value per contract) * portfolio weight traded
    cost_as_np_in_portfolio_weight_terms = \
        np.array(costs_as_list) / np.array(per_contract_value_as_list)

    ASSUMED_TRADES_PER_YEAR = 12.0
    cost_as_np_in_portfolio_weight_terms = cost_as_np_in_portfolio_weight_terms * ASSUMED_TRADES_PER_YEAR

    return cost_as_np_in_portfolio_weight_terms

def grid_search_optimise_with_fixed_contract_values_and_processed_inputs(
                                                                         grid_parameters: gridParameters,
                                                                        optimisation_parameters: optimisationParameters,
                                                                    use_process_pool: bool = False
):
    ## FIX ME TO DO
    ## add other constraints:
    ##   reduce only (needs existing position): conflict with sign change so generate first?
    ##   don't trade (needs existing position)

    ## mean reverting vol estimate

    grid_points = generate_grid(grid_parameters)

    optimal_weights_as_list = find_optimal_weights_given_grid_points(grid_points,
                                                                     optimisation_parameters,
                                                                     use_process_pool = use_process_pool)

    return optimal_weights_as_list


def find_optimal_weights_given_grid_points(grid_points: list,
                                           optimisation_parameters: optimisationParameters,
                                           use_process_pool: bool = False,
                                           num_processes: int = 8):

    grid_possibles = itertools.product(*grid_points)

    if use_process_pool:
        with ProcessPoolExecutor(max_workers=num_processes) as pool:
            results = pool.map(
                neg_return_with_risk_penalty_and_costs,
                         grid_possibles,
                        itertools.repeat(optimisation_parameters),

                         )
    else:
        results = map(neg_return_with_risk_penalty_and_costs,
                      grid_possibles,
                      itertools.repeat(optimisation_parameters))

    results = list(results)
    list_of_values = [result.value for result in results]
    optimal_value_index = list_of_values.index(min(list_of_values))

    optimal_weights_as_list = results[optimal_value_index].weights

    return optimal_weights_as_list


