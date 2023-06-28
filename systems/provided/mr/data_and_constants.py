from collections import namedtuple
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Mr_Limit_Types(Enum):
    LOWER_LIMIT = 1
    UPPER_LIMIT = 2


LOWER_LIMIT = Mr_Limit_Types.LOWER_LIMIT
UPPER_LIMIT = Mr_Limit_Types.UPPER_LIMIT


class Mr_Trading_Flags(Enum):
    CLOSE_MR_POSITIONS = 1
    REACHED_FORECAST_LIMIT = 2


CLOSE_MR_POSITIONS = Mr_Trading_Flags.CLOSE_MR_POSITIONS
REACHED_FORECAST_LIMIT = Mr_Trading_Flags.REACHED_FORECAST_LIMIT


@dataclass
class MROrderSeriesData:
    equilibrium_hourly_price_series: pd.Series
    price_series: pd.Series
    hourly_vol_series: pd.Series
    conditioning_forecast_series: pd.Series
    average_position_series: pd.Series
    forecast_attenuation_series: pd.Series
    forecast_scalar_series: pd.Series
    avg_abs_forecast: float = 10.0
    abs_forecast_cap: float = 20.0


MRDataAtIDXPoint = namedtuple(
    "MRDataAtIDXPoint",
    [
        "equilibrium_price",
        "average_position",
        "hourly_vol",
        "conditioning_forecast",
        "avg_abs_forecast",
        "abs_forecast_cap",
        "forecast_attenuation",
        "current_hourly_price",
        "next_hourly_price",
        "next_datetime",
        "forecast_scalar",
    ],
)
