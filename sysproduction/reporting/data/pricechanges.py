######## DO AS A CACHEING OBJECT
### CREATE A CACHE

import datetime
import pandas as pd
import numpy as np

from syscore.dateutils import get_date_from_period_and_end_date, get_approx_vol_scalar_for_period
from syscore.cache import Cache
from sysdata.data_blob import dataBlob
from sysproduction.data.prices import diagPrices, get_list_of_instruments
from sysproduction.reporting.data.risk import get_current_daily_stdev_for_instrument

class marketMovers(object):
    def __init__(self, data: dataBlob):
        self._data = data
        self._end_date = datetime.datetime.now()
        self._cache = Cache(self)

    def get_market_moves_for_period(self,
                                    period: str) -> pd.DataFrame:
        print("Getting data for %s" % period)
        # ['name', 'change', 'vol_adjusted']
        list_of_instruments = get_list_of_instruments(self.data, source="multiple")
        all_moves = [self.get_market_move_for_instrument_and_period(
                                                               instrument_code=instrument_code,
                                                               period=period)
                     for instrument_code in list_of_instruments]

        all_moves_as_df = pd.DataFrame(all_moves)

        return all_moves_as_df

    def get_market_move_for_instrument_and_period(self,
                                                  instrument_code: str,
                                                  period: str) -> dict:
        print(instrument_code)
        price_change = self.get_price_change_for_period(instrument_code=instrument_code,
                                                  period=period)

        vol_for_period = self.calculate_vol_for_period( instrument_code=instrument_code,
                                                        period=period)

        vol_adjusted = price_change / vol_for_period

        percentage_change = self.get_percentage_change_for_period(instrument_code=instrument_code,
                                                  period=period)


        return dict(name=instrument_code,
                    change=percentage_change,
                    vol_adjusted=vol_adjusted)

    def get_percentage_change_for_period(self, instrument_code:str, period:str) -> float:
        price_series = self.get_prices_for_instrument(instrument_code)
        start_date = self.start_date_for_period(period)
        end_date = self.end_date
        change = get_percentage_change_from_series_for_period(price_series,
                                                         start_date=start_date,
                                                         end_date=end_date)

        return change


    def get_price_change_for_period(self, instrument_code:str, period:str) -> float:
        price_series = self.get_prices_for_instrument(instrument_code)
        start_date = self.start_date_for_period(period)
        end_date = self.end_date
        change = get_price_change_from_series_for_period(price_series,
                                                         start_date=start_date,
                                                         end_date=end_date)

        return change

    def get_prices_for_instrument(self,
                                  instrument_code: str,
                                                  ) -> pd.Series:
        return self.cache.get(self._get_prices_for_instrument,
                              instrument_code)

    def _get_prices_for_instrument(self,
                                  instrument_code: str,
                                ) -> pd.Series:
        diag_prices = diagPrices(self.data)
        price_series = diag_prices.get_adjusted_prices(instrument_code).ffill()

        return price_series

    def calculate_vol_for_period(self,
                                 instrument_code: str,
                                 period: str) -> float:

        start_date = self.start_date_for_period(period)
        end_date = self.end_date
        vol_scalar = get_approx_vol_scalar_for_period(start_date, end_date)

        stddev = self.get_stdev_at_start_date_for_instrument(start_date, instrument_code)

        return stddev * vol_scalar

    def get_stdev_at_start_date_for_instrument(self, start_date: datetime.date,
                                               instrument_code: str):
        
        stdev = get_stdev_at_start_date_for_instrument(start_date=start_date,
                                                       price_series=self.get_prices_for_instrument(instrument_code))

        return stdev

    def start_date_for_period(self, period: str) -> datetime.datetime:
        return get_date_from_period_and_end_date(period, end_date=self.end_date)

    @property
    def data(self) -> dataBlob:
        return self._data

    @property
    def end_date(self) -> datetime.datetime:
        return self._end_date

    @property
    def cache(self) -> Cache:
        return self._cache


def get_price_change_from_series_for_period(price_series: pd.Series,
                                            start_date: datetime.date,
                                            end_date: datetime.date) -> float:
    price_series_for_period = price_series[start_date:end_date]
    if len(price_series_for_period) == 0:
        return np.nan
    return price_series_for_period[-1] - price_series_for_period[0]



def get_percentage_change_from_series_for_period(price_series: pd.Series,
                                            start_date: datetime.date,
                                            end_date: datetime.date) -> float:
    price_series_for_period = price_series[start_date:end_date]
    if len(price_series_for_period) == 0:
        return np.nan
    return 100*(price_series_for_period[-1]/price_series_for_period[0]) -1

def get_stdev_at_start_date_for_instrument(price_series: pd.Series,
                                            start_date: datetime.date):
    price_series_for_period = price_series[:start_date]
    daily_price_series = price_series_for_period.resample("1B").ffill()
    daily_returns = daily_price_series.diff()
    vol_series = daily_returns.ewm(30).std()

    return vol_series[-1]