import pytest

from sysbrokers.IB.client.ib_fx_client import ibFxClient
from sysbrokers.IB.client.ib_orders_client import ibOrdersClient
from sysexecution.orders.broker_orders import market_order_type, limit_order_type
from sysexecution.trade_qty import tradeQuantity


def _orders_client_without_connection() -> ibOrdersClient:
    return object.__new__(ibOrdersClient)


@pytest.mark.parametrize(
    "order_type, limit_price", [(market_order_type, None), (limit_order_type, 100.0)]
)
def test_futures_order_has_explicit_day_tif(order_type, limit_price):
    ib_order = _orders_client_without_connection()._build_ib_order(
        trade_list=tradeQuantity([1]),
        account_id="DU123",
        order_type=order_type,
        limit_price=limit_price,
    )

    assert ib_order.tif == "DAY"
    assert ib_order.account == "DU123"


def test_fx_order_has_explicit_day_tif():
    ib_order = object.__new__(ibFxClient)._create_fx_market_order_for_submission(
        trade=1000.0
    )

    assert ib_order.tif == "DAY"
