from dataclasses import dataclass

import numpy as np


@dataclass
class speedControlForDynamicOpt:
    trade_shadow_cost: float = (10,)
    tracking_error_buffer: float = (0.02,)


VERY_SMALL_NUMBER = 0.00001


def calculate_adjustment_factor(
    speed_control: speedControlForDynamicOpt, tracking_error_of_prior: float
) -> np.array:

    ## returns 1.0 if we do an entire trade (ok never happens)
    ## returns 0.0 if we do none of it
    if tracking_error_of_prior <= 0:
        return 0.0

    tracking_error_buffer = speed_control.tracking_error_buffer

    excess_tracking_error = tracking_error_of_prior - tracking_error_buffer

    adj_factor = excess_tracking_error / tracking_error_of_prior
    adj_factor = max(adj_factor, 0.0)

    return adj_factor


def adjust_weights_with_factor(
    optimised_weights_as_np: np.array,
    prior_weights_as_np: np.array,
    per_contract_value_as_np: np.array,
    adj_factor: float,
):

    desired_trades_weight_space = optimised_weights_as_np - prior_weights_as_np
    adjusted_trades_weight_space = adj_factor * desired_trades_weight_space

    rounded_adjusted_trades_as_weights = (
        calculate_adjusting_trades_rounding_in_contract_space(
            adjusted_trades_weight_space=adjusted_trades_weight_space,
            per_contract_value_as_np=per_contract_value_as_np,
        )
    )

    new_optimal_weights = prior_weights_as_np + rounded_adjusted_trades_as_weights

    return new_optimal_weights


def calculate_adjusting_trades_rounding_in_contract_space(
    adjusted_trades_weight_space: np.array, per_contract_value_as_np: np.array
) -> np.array:

    adjusted_trades_in_contracts = (
        adjusted_trades_weight_space / per_contract_value_as_np
    )
    rounded_adjusted_trades_in_contracts = np.round(adjusted_trades_in_contracts)
    rounded_adjusted_trades_as_weights = (
        rounded_adjusted_trades_in_contracts * per_contract_value_as_np
    )

    return rounded_adjusted_trades_as_weights
