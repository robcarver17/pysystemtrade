######## DO AS A CACHEING OBJECT
### CREATE A CACHE

import datetime
import pandas as pd
import numpy as np

from syscore.dateutils import get_date_from_period_and_end_date, get_approx_vol_scalar_for_period
from sysdata.data_blob import dataBlob
from sysproduction.data.prices import diagPrices, get_list_of_instruments
from sysproduction.reporting.data.risk import get_current_daily_stdev_for_instrument

def get_market_moves_for_period(data: dataBlob,
                                period: str) -> pd.DataFrame:
    # ['name', 'change', 'vol_adjusted']
    list_of_instruments = get_list_of_instruments(data, source="multiple")
    all_moves = [get_market_move_for_instrument_and_period(data=data,
                                                           instrument_code=instrument_code,
                                                           period=period)
                 for instrument_code in list_of_instruments]

    all_moves_as_df = pd.DataFrame(all_moves)

    return all_moves_as_df

def get_market_move_for_instrument_and_period(data: dataBlob,
                                              instrument_code: str,
                                              period: str) -> dict:

    diag_prices = diagPrices(data)
    price_series = diag_prices.get_adjusted_prices(instrument_code).ffill()
    start_date = get_date_from_period_and_end_date(period)

    change = get_price_change_from_series_for_period(price_series, start_date=start_date)
    vol_for_period = calculate_vol_for_period(data, instrument_code, start_date=start_date)

    return dict(name = instrument_code,
            change = change,
                vol_adjusted = change / vol_for_period)

def get_price_change_from_series_for_period(price_series: pd.Series,
                                            start_date: datetime.date) -> float:
    price_series_for_period = price_series[start_date:]
    if len(price_series_for_period)==0:
        return np.nan
    return price_series_for_period[-1] - price_series_for_period[0]

def calculate_vol_for_period(data: dataBlob,
                                            instrument_code: str,
                                              start_date: datetime) -> float:
    stddev = get_current_daily_stdev_for_instrument(data, instrument_code)
    vol_scalar = get_approx_vol_scalar_for_period(start_date)

    return stddev * vol_scalar


