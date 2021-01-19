from ib_insync.order import MarketOrder, LimitOrder, Trade
from syscore.objects import arg_not_supplied, missing_order, missing_contract
from sysbrokers.IB.client.ib_client import ibClient
from sysbrokers.IB.client.ib_contracts_client import ibContractsClient
from sysbrokers.IB.ib_translate_broker_order_objects import tradeWithContract, listOfTradesWithContracts
from sysbrokers.IB.ib_positions import (
    from_ib_positions_to_dict,
    resolveBS,
    resolveBS_for_list,
positionsFromIB
)
from sysbrokers.IB.ib_contracts import (
    resolve_multiple_expiries,
    ibcontractWithLegs)
from sysexecution.trade_qty import tradeQuantity
from sysexecution.orders.broker_orders import brokerOrderType, market_order_type

from sysobjects.contracts import futuresContract

# we don't include ibClient since we get that through contracts client

class ibOrdersClient(ibContractsClient):
    def broker_get_orders(self, account_id: str=arg_not_supplied) -> listOfTradesWithContracts:
        """
        Get all active trades, orders and return them with the information needed

        :return: list
        """
        self.refresh()
        trades_in_broker_format = self.ib.trades()
        if account_id is not arg_not_supplied:
            trades_in_broker_format_this_account = [
                trade
                for trade in trades_in_broker_format
                if trade.order.account == account_id
            ]
        else:
            trades_in_broker_format_this_account = trades_in_broker_format

        trades_in_broker_format_with_legs = [
            self.add_contract_legs_to_order(raw_order_from_ib)
            for raw_order_from_ib in trades_in_broker_format_this_account
        ]

        trade_list = listOfTradesWithContracts(trades_in_broker_format_with_legs)

        return trade_list


    def broker_submit_order(
        self,
        contract_object_with_ib_data: futuresContract,
        trade_list: tradeQuantity,
        account: str,
        order_type: brokerOrderType = market_order_type,
        limit_price: float=None,
    ):
        """

        :param ibcontract: contract_object_with_ib_data: contract where instrument has ib metadata
        :param trade: int
        :param account: str
        :param order_type: str, market or limit
        :param limit_price: None or float

        :return: brokers trade object

        """
        # FIXME WHAT THE FUCK IS GOING ON HERE
        if contract_object_with_ib_data.is_spread_contract():
            ibcontract_with_legs = self.ib_futures_contract(
                contract_object_with_ib_data,
                trade_list_for_multiple_legs=trade_list,
                return_leg_data=True,
            )
            ibcontract = ibcontract_with_legs.ibcontract
        else:
            ibcontract = self.ib_futures_contract(contract_object_with_ib_data)
            ibcontract_with_legs = ibcontractWithLegs(ibcontract)

        if ibcontract is missing_contract:
            return missing_order

        ib_BS_str, ib_qty = resolveBS_for_list(trade_list)

        if order_type == "market":
            ib_order = MarketOrder(ib_BS_str, ib_qty)
        elif order_type == "limit":
            if limit_price is None:
                self.log.critical("Need to have limit price with limit order!")
                return missing_order
            else:
                ib_order = LimitOrder(ib_BS_str, ib_qty, limit_price)
        else:
            self.log.critical("Order type %s not recognised!" % order_type)
            return missing_order

        if account != "":
            ib_order.account = account

        order_object = self.ib.placeOrder(ibcontract, ib_order)

        # for consistency with spread orders
        trade_with_contract = tradeWithContract(
            ibcontract_with_legs, order_object)

        return trade_with_contract

    def add_contract_legs_to_order(self, raw_order_from_ib: Trade) -> tradeWithContract:
        combo_legs = getattr(raw_order_from_ib.contract, "comboLegs", [])
        legs_data = []
        for leg in combo_legs:
            contract_for_leg = self.ib_get_contract_with_conId(
                raw_order_from_ib.contract.symbol, leg.conId
            )
            legs_data.append(contract_for_leg)
        ibcontract_with_legs = ibcontractWithLegs(
            raw_order_from_ib.contract, legs=legs_data
        )
        trade_with_contract = tradeWithContract(
            ibcontract_with_legs, raw_order_from_ib)

        return trade_with_contract

