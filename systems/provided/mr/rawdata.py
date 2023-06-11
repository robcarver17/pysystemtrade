import pandas as pd
from systems.rawdata import RawData


class MrRawData(RawData):
    def daily_equilibrium_price(self, instrument_code: str) -> pd.Series:
        daily_price = self.get_daily_prices(instrument_code)
        mr_span = self.config.mr["mr_span_days"]
        daily_equilibrium = daily_price.ewm(span=mr_span).mean()

        return daily_equilibrium
