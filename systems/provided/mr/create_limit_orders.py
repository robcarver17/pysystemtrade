import datetime
from typing import Union

from systems.accounts.order_simulator.simple_orders import (
    ListOfSimpleOrdersWithDate,
    empty_list_of_orders_with_date,
    SimpleOrderWithDate,
)
from systems.provided.mr.forecasting import calculate_scaled_attenuated_forecast
from systems.provided.mr.data_and_constants import (
    Mr_Limit_Types,
    LOWER_LIMIT,
    UPPER_LIMIT,
    Mr_Trading_Flags,
    REACHED_FORECAST_LIMIT,
    MRDataAtIDXPoint,
)


def create_limit_orders_for_mr_data(
    current_position: int,
    current_datetime: datetime.datetime,
    data_for_idx: MRDataAtIDXPoint,
) -> ListOfSimpleOrdersWithDate:

    lower_order_list = create_lower_limit_order(
        data_for_idx=data_for_idx,
        current_datetime=current_datetime,
        current_position=current_position,
    )
    upper_order_list = create_upper_limit_order(
        data_for_idx=data_for_idx,
        current_datetime=current_datetime,
        current_position=current_position,
    )
    combined_list_of_orders = lower_order_list + upper_order_list

    return ListOfSimpleOrdersWithDate(combined_list_of_orders)


def create_upper_limit_order(
    current_position: int,
    current_datetime: datetime.datetime,
    data_for_idx: MRDataAtIDXPoint,
) -> ListOfSimpleOrdersWithDate:

    ## FIXME WONT' WORK WITH VERY LARGE POSITIONS AND LARGE TICK SIZES IN PRODUCTION
    trade_to_upper = +1
    position_upper = current_position + trade_to_upper
    upper_limit_price = limit_price_given_higher_position(
        position_to_derive_for=position_upper, data_for_idx=data_for_idx
    )
    if upper_limit_price is REACHED_FORECAST_LIMIT:
        return empty_list_of_orders_with_date()

    upper_order = SimpleOrderWithDate(
        quantity=trade_to_upper,
        limit_price=upper_limit_price,
        submit_date=current_datetime,
    )

    return ListOfSimpleOrdersWithDate([upper_order])


def create_lower_limit_order(
    current_position: int,
    current_datetime: datetime.datetime,
    data_for_idx: MRDataAtIDXPoint,
) -> ListOfSimpleOrdersWithDate:

    ## FIXME WONT' WORK WITH VERY LARGE POSITIONS AND LARGE TICK SIZES IN PRODUCTION
    trade_to_lower = -1
    position_lower = current_position + trade_to_lower
    lower_limit_price = limit_price_given_lower_position(
        position_to_derive_for=position_lower, data_for_idx=data_for_idx
    )

    if lower_limit_price is REACHED_FORECAST_LIMIT:
        return empty_list_of_orders_with_date()

    lower_order = SimpleOrderWithDate(
        quantity=trade_to_lower,
        limit_price=lower_limit_price,
        submit_date=current_datetime,
    )

    return ListOfSimpleOrdersWithDate([lower_order])


def limit_price_given_higher_position(
    position_to_derive_for: int,
    data_for_idx: MRDataAtIDXPoint,
) -> Union[float, Mr_Trading_Flags]:
    ### FIXME WITH TICK SIZE DO DIFFERENTIAL ROUNDING HERE DEPENDING ON LIMIT TYPE

    return derive_limit_price_at_position_for_mean_reversion_overlay(
        position_to_derive_for=position_to_derive_for,
        data_for_idx=data_for_idx,
        limit_type=UPPER_LIMIT,
    )


def limit_price_given_lower_position(
    position_to_derive_for: int,
    data_for_idx: MRDataAtIDXPoint,
) -> Union[float, Mr_Trading_Flags]:
    ### FIXME WITH TICK SIZE DO DIFFERENTIAL ROUNDING HERE DEPENDING ON LIMIT TYPE

    return derive_limit_price_at_position_for_mean_reversion_overlay(
        position_to_derive_for=position_to_derive_for,
        data_for_idx=data_for_idx,
        limit_type=LOWER_LIMIT,
    )


def derive_limit_price_at_position_for_mean_reversion_overlay(
    position_to_derive_for: int,
    data_for_idx: MRDataAtIDXPoint,
    limit_type: Mr_Limit_Types,
) -> Union[float, Mr_Trading_Flags]:

    if is_current_forecast_beyond_limits(
        data_for_idx=data_for_idx, limit_type=limit_type
    ):
        return REACHED_FORECAST_LIMIT

    limit_price = derive_limit_price_without_checks(
        position_to_derive_for=position_to_derive_for, data_for_idx=data_for_idx
    )

    return limit_price


def is_current_forecast_beyond_limits(
    data_for_idx: MRDataAtIDXPoint, limit_type: Mr_Limit_Types
) -> bool:

    scaled_attenuated_forecast = calculate_scaled_attenuated_forecast(data_for_idx)
    abs_forecast_cap = data_for_idx.abs_forecast_cap
    if limit_type is UPPER_LIMIT:
        return scaled_attenuated_forecast > abs_forecast_cap
    elif limit_type is LOWER_LIMIT:
        return scaled_attenuated_forecast < -abs_forecast_cap
    else:
        raise Exception("Limit type %s not recognised!" % str(limit_type))


def derive_limit_price_without_checks(
    position_to_derive_for: int,
    data_for_idx: MRDataAtIDXPoint,
) -> float:
    """
    RAW_FORECAST = (equilibrium - current_price)/ daily_vol_hourly
    [uncapped] FORECAST = forecast_atten * forecast_scalar * RAW_FORECAST
    position = (average position *  FORECAST ) / (avg_abs_forecast)
             = (average position * forecast_atten * forecast_scalar *
                (equilibrium - current_price)) / (avg_abs_forecast * daily_vol_hourly)
    let FNUM = average position * forecast_atten * forecast_scalar
    let FDIV = (avg_abs_forecast * daily_vol_hourly)
     then
    position = FNUM * (equilibrium - current_price) / FDIV

    ## solve for limit_price = current_price, given position:

    FNUM * (equilibrium - limit_price) = position * FDIV
    (equilibrium - limit_price) = position * FDIV / FNUM
    limit_price = equilibrium - (position * FDIV / FNUM)
    limit_price = equilibrium - [(position * avg_abs_forecast * daily_vol_hourly) /
                                (average position * forecast_atten * forecast_scalar)]
    """
    d = data_for_idx
    limit_price = d.equilibrium_price - [
        (position_to_derive_for * d.avg_abs_forecast * d.hourly_vol)
        / (d.average_position * d.forecast_attenuation * d.forecast_scalar)
    ]

    return limit_price
