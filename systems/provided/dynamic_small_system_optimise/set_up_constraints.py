from dataclasses import dataclass

import numpy as np

from syscore.genutils import sign
from syscore.constants import arg_not_supplied
from sysquant.optimisation.weights import portfolioWeights

A_VERY_LARGE_NUMBER = 999999999


class minMaxAndDirectionAndStart(dict):
    @property
    def minima(self) -> portfolioWeights:
        return portfolioWeights(self._get_dict_for_value_across_codes("minimum"))

    @property
    def maxima(self) -> portfolioWeights:
        return portfolioWeights(self._get_dict_for_value_across_codes("maximum"))

    @property
    def direction(self) -> portfolioWeights:
        return portfolioWeights(self._get_dict_for_value_across_codes("direction"))

    @property
    def starting_weights(self) -> portfolioWeights:
        return portfolioWeights(self._get_dict_for_value_across_codes("start_weight"))

    def _get_dict_for_value_across_codes(self, entry_name: str):
        return dict(
            [
                (instrument_code, getattr(dict_value, entry_name))
                for instrument_code, dict_value in self.items()
            ]
        )


@dataclass
class minMaxAndDirectionAndStartForCode:
    minimum: float
    maximum: float
    direction: float
    start_weight: float


def calculate_min_max_and_direction_and_start(
    input_data: "dataForOptimisation",
) -> minMaxAndDirectionAndStart:
    all_codes = list(input_data.keys_with_valid_data)
    all_results = dict(
        [
            (
                instrument_code,
                get_data_and_calculate_for_code(instrument_code, input_data=input_data),
            )
            for instrument_code in all_codes
        ]
    )

    return minMaxAndDirectionAndStart(all_results)


def get_data_and_calculate_for_code(
    instrument_code: str, input_data: "dataForOptimisation"
) -> minMaxAndDirectionAndStartForCode:
    if input_data.reduce_only_keys is arg_not_supplied:
        reduce_only = False
    else:
        reduce_only = instrument_code in input_data.reduce_only_keys

    if input_data.no_trade_keys is arg_not_supplied:
        no_trade = False
    else:
        no_trade = instrument_code in input_data.no_trade_keys

    max_position = input_data.maximum_position_weight_for_code(instrument_code)
    weight_prior = input_data.prior_weight_for_code(instrument_code)
    optimium_weight = input_data.optimal_weights_for_code(instrument_code)

    min_max_and_direction_and_start_for_code = calculations_for_code(
        reduce_only=reduce_only,
        no_trade=no_trade,
        max_position=max_position,
        weight_prior=weight_prior,
        optimium_weight=optimium_weight,
    )

    return min_max_and_direction_and_start_for_code


def calculations_for_code(
    reduce_only: bool = False,
    no_trade: bool = False,
    max_position: float = arg_not_supplied,
    weight_prior: float = arg_not_supplied,
    optimium_weight: float = np.nan,
):

    minimum, maximum = calculate_minima_and_maxima(
        reduce_only=reduce_only,
        no_trade=no_trade,
        max_position=max_position,
        weight_prior=weight_prior,
    )

    assert maximum >= minimum

    direction = calculate_direction(
        optimum_weight=optimium_weight, minimum=minimum, maximum=maximum
    )

    start_weight = calculate_starting_weight(minimum=minimum, maximum=maximum)

    return minMaxAndDirectionAndStartForCode(
        minimum=minimum, maximum=maximum, direction=direction, start_weight=start_weight
    )


def calculate_minima_and_maxima(
    reduce_only: bool = False,
    no_trade: bool = False,
    max_position: float = arg_not_supplied,
    weight_prior: float = arg_not_supplied,
) -> tuple:

    minimum = -A_VERY_LARGE_NUMBER
    maximum = A_VERY_LARGE_NUMBER

    if no_trade:
        if weight_prior is not arg_not_supplied:
            return weight_prior, weight_prior

    if reduce_only:
        if weight_prior is not arg_not_supplied:
            if weight_prior > 0:
                minimum = 0.0
                maximum = weight_prior
            elif weight_prior < 0:
                minimum = weight_prior
                maximum = 0.0

            else:
                ## prior weight equals zero, so no trade
                return (0.0, 0.0)

    if max_position is not arg_not_supplied:
        max_position = abs(max_position)

        # Most conservative of existing minima/maximum if any
        minimum = max(-max_position, minimum)
        maximum = min(max_position, maximum)

    return minimum, maximum


def calculate_direction(
    optimum_weight: float,
    minimum: float = -A_VERY_LARGE_NUMBER,
    maximum: float = A_VERY_LARGE_NUMBER,
) -> float:
    if minimum >= 0:
        return 1

    if maximum <= 0:
        return -1

    if np.isnan(optimum_weight):
        return 1

    return sign(optimum_weight)


def calculate_starting_weight(minimum, maximum) -> float:
    if maximum == minimum:
        ## no trade possible
        return maximum

    if minimum > 0:
        return minimum

    if maximum < 0:
        return maximum

    return 0.0
