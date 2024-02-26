import pandas as pd

from systems.accounts.order_simulator.account_curve_order_simulator import (
    AccountWithOrderSimulator,
)
from systems.accounts.order_simulator.pandl_order_simulator import (
    OrderSimulator,
    OrdersSeriesData,
)
from systems.system_cache import diagnostic


class HourlyOrderSimulatorOfMarketOrders(OrderSimulator):
    def _series_data(self) -> OrdersSeriesData:
        series_data = _build_hourly_series_data_for_order_simulator(
            system_accounts_stage=self.system_accounts_stage,  # ignore type hint
            instrument_code=self.instrument_code,
            is_subsystem=self.is_subsystem,
        )
        return series_data


def _build_hourly_series_data_for_order_simulator(
    system_accounts_stage,  ## no explicit type would cause circular import
    instrument_code: str,
    is_subsystem: bool = False,
) -> OrdersSeriesData:
    price_series = system_accounts_stage.get_hourly_prices(instrument_code)
    if is_subsystem:
        unrounded_positions = (
            system_accounts_stage.get_unrounded_subsystem_position_for_order_simulator(
                instrument_code
            )
        )
    else:
        unrounded_positions = (
            system_accounts_stage.get_unrounded_instrument_position_for_order_simulator(
                instrument_code
            )
        )

    price_series = price_series.sort_index()
    unrounded_positions = unrounded_positions.sort_index()

    both_index = pd.concat([price_series, unrounded_positions], axis=1).index

    price_series = price_series.reindex(both_index).ffill()
    unrounded_positions = unrounded_positions.reindex(both_index).ffill()

    series_data = OrdersSeriesData(
        price_series=price_series, unrounded_positions=unrounded_positions
    )
    return series_data


class AccountWithOrderSimulatorForHourlyMarketOrders(AccountWithOrderSimulator):
    @diagnostic(not_pickable=True)
    def get_order_simulator(
        self, instrument_code, is_subsystem: bool
    ) -> HourlyOrderSimulatorOfMarketOrders:
        order_simulator = HourlyOrderSimulatorOfMarketOrders(
            system_accounts_stage=self,
            instrument_code=instrument_code,
            is_subsystem=is_subsystem,
        )
        return order_simulator
