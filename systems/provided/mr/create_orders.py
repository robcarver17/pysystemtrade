from typing import Union
from dataclasses import dataclass
from syscore.genutils import same_sign
from syscore.constants import named_object, arg_not_supplied
from sysobjects.orders import SimpleOrder

CLOSE_MR_POSITIONS = named_object("close mr positions")
REACHED_FORECAST_LIMIT = named_object("reached forecast limit")


@dataclass
class DataForMROrder:
    current_position: int
    current_equilibrium_price: float
    current_price: float
    current_vol: float
    current_conditioner_for_forecast: float
    average_position: float
    avg_abs_forecast: float = 10.0
    mr_forecast_scalar: float = 20.0
    lower_forecast_floor: float = -20.0
    upper_forecast_cap: float = 20.0

    def limit_price_given_higher_position(
        self, position_to_derive_for
    ) -> Union[float, named_object]:
        return self._derive_limit_price_at_position_for_mean_reversion_overlay(
            position_to_derive_for, upper_position=True
        )

    def limit_price_given_lower_position(
        self, position_to_derive_for
    ) -> Union[float, named_object]:
        return self._derive_limit_price_at_position_for_mean_reversion_overlay(
            position_to_derive_for, upper_position=False
        )

    def _derive_limit_price_at_position_for_mean_reversion_overlay(
        self, position_to_derive_for: int, upper_position: bool = True
    ) -> Union[float, named_object]:
        """

        If forecast = cap, then don't return a price if too high
        If forecast turned off by conditioning, then fail

        """

        scaled_forecast = self.scaled_forecast

        if not same_sign(scaled_forecast, self.current_conditioner_for_forecast):
            ## Market order
            return CLOSE_MR_POSITIONS

        limit_price = self._derive_limit_price_at_position_for_mean_reversion_overlay_when_conditioning_on(
            position_to_derive_for=position_to_derive_for, upper_position=upper_position
        )

        return limit_price

    def _derive_limit_price_at_position_for_mean_reversion_overlay_when_conditioning_on(
        self, position_to_derive_for: int, upper_position: bool = True
    ) -> Union[float, named_object]:

        if self._is_forecast_beyond_limits(upper_position):
            return REACHED_FORECAST_LIMIT

        limit_price = self.derive_limit_price_without_checks(position_to_derive_for)

        return limit_price

    def _is_forecast_beyond_limits(self, upper_position: bool) -> bool:

        lower_position = not upper_position
        if self.scaled_forecast > self.upper_forecast_cap and upper_position:
            return True
        elif self.scaled_forecast < self.lower_forecast_floor and lower_position:
            return True
        else:
            return False

    def derive_limit_price_without_checks(self, position_to_derive_for: int) -> float:
        """
        FORECAST = FORECAST_SCALAR * (equilibrium - current_price)/ daily_vol_hourly
        POSITION = (average position *  forecast ) / (AVG_ABS_FORECAST)
                 = (average position * FORECAST_SCALAR * (equilibrium - current_price) / (AVG_ABS_FORECAST * daily_vol_hourly)

        POSITION * (AVG_ABS_FORECAST * daily_vol_hourly) = average position * FORECAST_SCALAR * (equilibrium - current_price)
        (equilibrium - current_price) =  POSITION * AVG_ABS_FORECAST * daily_vol_hourly / (average position * FORECAST SCALAR)
        current price = equilibrium - [POSITION * AVG_ABS_FORECAST * daily_vol_hourly / (average position * FORECAST SCALAR)]
        """

        limit_price = self.current_equilibrium_price - (
            position_to_derive_for * self.avg_abs_forecast * self.current_vol
        ) / (self.average_position * self.mr_forecast_scalar)

        return limit_price

    @property
    def capped_scaled_forecast(self) -> float:
        capped_scaled_forecast = min(
            [
                max([self.scaled_forecast, self.lower_forecast_floor]),
                self.upper_forecast_cap,
            ]
        )

        return capped_scaled_forecast

    @property
    def scaled_forecast(self) -> float:
        raw_forecast = (
            self.current_equilibrium_price - self.current_price
        ) / self.current_vol

        scaled_forecast = raw_forecast * self.mr_forecast_scalar

        return scaled_forecast


def create_orders_from_mr_data(data_for_mr_order: DataForMROrder) -> list:

    optimal_position = derive_unrounded_position(data_for_mr_order)
    if optimal_position is CLOSE_MR_POSITIONS:
        ## market order to close positions
        return [SimpleOrder(-data_for_mr_order.current_position)]
    list_of_orders = _create_orders_for_mr_data_if_not_closing(
        optimal_position=optimal_position, data_for_mr_order=data_for_mr_order
    )

    return list_of_orders


def derive_unrounded_position(
    data_for_mr_order: DataForMROrder,
) -> Union[float, named_object]:

    capped_scaled_forecast = data_for_mr_order.capped_scaled_forecast
    if not same_sign(
        capped_scaled_forecast, data_for_mr_order.current_conditioner_for_forecast
    ):
        ## Market order
        return CLOSE_MR_POSITIONS

    position = (
        data_for_mr_order.average_position
        * capped_scaled_forecast
        / data_for_mr_order.avg_abs_forecast
    )

    return position


def _create_orders_for_mr_data_if_not_closing(
    optimal_position: float, data_for_mr_order: DataForMROrder
) -> list:
    rounded_optimal = round(optimal_position)
    diff_to_current = abs(rounded_optimal - data_for_mr_order.current_position)

    if diff_to_current > 1:
        ## close everything no limit order
        return [SimpleOrder(rounded_optimal - data_for_mr_order.current_position)]

    list_of_orders = _create_limit_orders_for_mr_data(data_for_mr_order)

    return list_of_orders


def _create_limit_orders_for_mr_data(data_for_mr_order: DataForMROrder) -> list:
    lower_order_list = _create_lower_limit_order(data_for_mr_order)
    upper_order_list = _create_upper_limit_order(data_for_mr_order)
    list_of_orders = lower_order_list + upper_order_list

    return list_of_orders


def _create_upper_limit_order(data_for_mr_order: DataForMROrder) -> list:
    trade_to_upper = +1
    position_upper = data_for_mr_order.current_position + trade_to_upper
    upper_limit_price = data_for_mr_order.limit_price_given_higher_position(
        position_upper
    )
    if upper_limit_price is REACHED_FORECAST_LIMIT:
        upper_order_list = []
    else:
        upper_order_list = [SimpleOrder(trade_to_upper, upper_limit_price)]

    return upper_order_list


def _create_lower_limit_order(data_for_mr_order: DataForMROrder) -> list:
    trade_to_lower = -1
    position_lower = data_for_mr_order.current_position + trade_to_lower
    lower_limit_price = data_for_mr_order.limit_price_given_lower_position(
        position_lower
    )

    if lower_limit_price is REACHED_FORECAST_LIMIT:
        lower_order_list = []
    else:
        lower_order_list = [SimpleOrder(trade_to_lower, lower_limit_price)]

    return lower_order_list
