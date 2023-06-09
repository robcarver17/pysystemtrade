from dataclasses import dataclass
import pandas as pd
from syscore.cache import Cache

from sysobjects.orders import ListOfSimpleOrdersWithDate
from sysobjects.fills import ListOfFills


@dataclass
class PositionsOrdersFills:
    positions: pd.Series
    list_of_orders: ListOfSimpleOrdersWithDate
    list_of_fills: ListOfFills


@dataclass
class OrderSimulator:
    system_accounts_stage: object  ## no explicit type as would cause circular import
    instrument_code: str
    is_subsystem: bool = False

    def diagnostic_df(self) -> pd.DataFrame:
        return self.cache.get(self._diagnostic_df)

    def _diagnostic_df(self) -> pd.DataFrame:
        raise NotImplemented("Need to inherit from this class to get diagnostics")

    def prices(self) -> pd.Series:
        raise NotImplemented("Need to inherit from this class to get prices")

    def positions(self) -> pd.Series:
        positions_orders_fills = self.positions_orders_and_fills_from_series_data()
        return positions_orders_fills.positions

    def list_of_fills(self) -> ListOfFills:
        positions_orders_fills = self.positions_orders_and_fills_from_series_data()
        return positions_orders_fills.list_of_fills

    def list_of_orders(self) -> ListOfSimpleOrdersWithDate:
        positions_orders_fills = self.positions_orders_and_fills_from_series_data()
        return positions_orders_fills.list_of_orders

    def positions_orders_and_fills_from_series_data(self) -> PositionsOrdersFills:
        ## Because p&l with orders is path dependent, we generate everything together
        return self.cache.get(self._positions_orders_and_fills_from_series_data)

    def _positions_orders_and_fills_from_series_data(self) -> PositionsOrdersFills:
        raise NotImplemented(
            "Need to inherit from this class and implement positions, orders, fills"
        )

    @property
    def cache(self) -> Cache:
        return getattr(self, "_cache", Cache(self))
