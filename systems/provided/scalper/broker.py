import datetime
from dataclasses import dataclass
from typing import Tuple, List

from build.lib.sysexecution.algos.common_functions import cancel_order
from private.projects.MR_2025.components import Order, Fill, FillAndOrder
from private.projects.MR_2025.configuration import STRATEGY_NAME
from sysdata.data_blob import dataBlob
from sysexecution.algos.algo import Algo
from sysexecution.order_stacks.broker_order_stack import orderWithControls
from sysexecution.orders.broker_orders import create_new_broker_order_from_contract_order, stop_loss_order_type, \
    limit_order_type
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.orders.named_order_objects import missing_order
from sysobjects.contracts import futuresContract
from sysobjects.production.positions import listOfContractPositions, contractPosition
from sysproduction.data.broker import dataBroker

@dataclass
class OrderAndOrderWithControls:
    order: Order
    order_with_controls: orderWithControls

class BrokerController():
    def __init__(self, data: dataBlob, futures_contract: futuresContract):
        self.data =data
        self.futures_contract = futures_contract

    def create_limit_order(self, order: Order):
        ## We don't bother databasing orders until executed

        contract_order = get_contract_order_from_simple_order(order=order, futures_contract=self.futures_contract)
        algo_instance = StrippedDownAlgo(data=self.data, contract_order=contract_order)
        broker, broker_account, broker_clientid = self.get_broker_details()
        placed_broker_order_with_controls = algo_instance.submit_mr_trade(
            broker_account=broker_account,
            broker=broker,
            broker_clientid=broker_clientid
        )

        if placed_broker_order_with_controls is missing_order:
            ## pass
            return missing_order

        ## store the placed broker order for future reference
        self.add_order_to_storage(OrderAndOrderWithControls(
            order=order,
            order_with_controls=placed_broker_order_with_controls
        ))

        return order

    def cancel_all_orders(self):
        while len(self.order_storage)>0:
            order_and_placed_broker_order_with_controls = self.order_storage.pop()
            cancel_order(self.data, order_and_placed_broker_order_with_controls.order_with_controls)


    def check_for_position_match(self, position: int, futures_contract: futuresContract) -> bool:
        broker_contract_positions = self.data_broker.get_all_current_contract_positions()
        broker_position = broker_contract_positions.position_in_contract(futures_contract=futures_contract)

        return int(broker_position)==int(position)

    def check_for_position_match_msg(self, position: int, futures_contract: futuresContract) -> str:
        broker_contract_positions = self.data_broker.get_all_current_contract_positions()
        broker_position = broker_contract_positions.position_in_contract(futures_contract=futures_contract)

        return "Break: Broker position %d, our position from state %d" % (broker_position, position)

    def get_fills_from_broker(self) -> List[FillAndOrder]:
        list_of_fills_and_orders = []
        order_storage = self.order_storage
        for order_and_order_with_controls in order_storage:
            order_with_controls = order_and_order_with_controls.order_with_controls
            order_with_controls.update_order()
            if order_with_controls.completed():
                filled_price = order_with_controls.order.filled_price
                filled_qty = order_with_controls.order.fill.as_single_trade_qty_or_error()
                fill = Fill(price=filled_price, size=filled_qty)

                order_storage.remove(order_and_order_with_controls)
                print("%s filled at %f" % (str(order_and_order_with_controls.order), filled_price))
                list_of_fills_and_orders.append(
                        FillAndOrder(
                            fill=fill,
                        order=order_and_order_with_controls.order)
                )


        return list_of_fills_and_orders

    def add_order_to_storage(self, order_and_controls: OrderAndOrderWithControls):
        storage = self.order_storage
        storage.append(order_and_controls)
        self._order_storage = storage

    @property
    def order_storage(self) -> List[OrderAndOrderWithControls]:
        storage = getattr(self, "_order_storage", [])
        return storage

    @property
    def broker_details(self):
        details = getattr(self, "_broker_details", None)
        if details is None:
            self._broker_details = details = self.get_broker_details()

        return details

    def get_broker_details(self) -> Tuple[str,str,str]:
        broker = self.data_broker.get_broker_name()
        broker_account = self.data_broker.get_broker_account()
        broker_clientid = str(self.data_broker.get_broker_clientid())

        return broker, broker_account, broker_clientid


    @property
    def data_broker(self):
        return dataBroker(self.data)

def get_contract_order_from_simple_order(order: Order, futures_contract: futuresContract):
    if order.stop_loss:
        order_type = stop_loss_order_type
    else:
        order_type = limit_order_type

    contract_order = contractOrder(STRATEGY_NAME, futures_contract.instrument.instrument_code,
                                   futures_contract.contract_date.date_str,
                                   order.size, limit_price=order.level,
                                   order_type=order_type,
                                   order_id=1,  ## pseduo get replaced later
                                   parent=1,
                                   reference_price=None,
                                   generated_datetime=datetime.datetime.now(),
                                   algo_to_use="MR_stripped_down_algo",
                                   reference_of_controlling_algo="MR_stripped_down_algo",

                                   )

    return contract_order

class StrippedDownAlgo(Algo):

    def submit_mr_trade(self,
                        broker:str, broker_account:str, broker_clientid:str) -> orderWithControls:
        """

        :return: broker order with control  or missing_order
        """
        contract_order = self.contract_order
        broker_order = create_new_broker_order_from_contract_order(
            contract_order,
            order_type=contract_order.order_type,
            broker=broker,
            broker_account=broker_account,
            broker_clientid=broker_clientid,
            limit_price=contract_order.limit_price,
        )

        self.data.log.debug(
            "Created a broker order %s (not yet submitted or written to local DB)"
            % str(broker_order),
            **contract_order.log_attributes(),
            method="temp",
        )

        placed_broker_order_with_controls = self.data_broker.submit_broker_order(
            broker_order
        )

        if placed_broker_order_with_controls is missing_order:
            self.data.log.warning(
                "Order could not be submitted",
                **contract_order.log_attributes(),
                method="temp",
            )
            return missing_order

        self.data.log.debug(
            "Submitted order to IB %s" % str(placed_broker_order_with_controls.order),
            **placed_broker_order_with_controls.order.log_attributes(),
            method="temp",
        )

        return placed_broker_order_with_controls

