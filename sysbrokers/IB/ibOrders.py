from syslogdiag.log import logtoscreen
from syscore.objects import missing_order, no_order_id
from sysdata.futures.contracts import futuresContract
from sysdata.fx.spotfx import currencyValue
from sysexecution.broker_orders import brokerOrderStackData, brokerOrder
from sysbrokers.IB.ibFuturesContracts import ibFuturesContractData

class ibOrdersData(brokerOrderStackData):
    def __init__(self, ibconnection, log=logtoscreen("ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB orders %s" % str(self.ibconnection)

    @property
    def futures_contract_data(self):
        return  ibFuturesContractData(self.ibconnection)

    def get_list_of_broker_orders(self):
        """
        Get list of broker orders from IB, and return as my broker_order objects

        :return: list of brokerOrder objects
        """

        list_of_raw_orders = self.ibconnection.broker_get_orders()
        order_list = [self.create_broker_order_object(raw_order) for raw_order in list_of_raw_orders]
        order_list = [order for order in order_list if order is not missing_order]

        return order_list

    def get_order_with_id_from_stack(self, order_id):
        pass

    def get_list_of_order_ids(self):
        return self.get_list_of_temp_ids()

    def get_list_of_temp_ids(self):

        all_active_orders = self.get_list_of_broker_orders()
        ib_broker_ids = [broker_order.broker_tempid for broker_order in all_active_orders]

        return ib_broker_ids

    def cancel_order(self, temp_order_id):
        pass

    def modify_order_on_stack(self, temp_order_id, new_trade):
        pass

    def put_order_on_stack(self, broker_order):
        """

        :param broker_order: key properties are instrument_code, contract_id, quantity
        :return: int with order ID or missing_order
        """
        if len(broker_order.trade)>1:
            # only single legs!
            return missing_order

        order_id = self.put_single_leg_order_on_stack(broker_order)

        return order_id

    def put_single_leg_order_on_stack(self, broker_order):
        """

        :param broker_order: key properties are instrument_code, contract_id, quantity
        :return: int with order ID or missing_order

        """
        instrument_code = broker_order.instrument_code

        ## Next two are because we are a single leg order, but both are lists
        contract_id = broker_order.contract_id[0]
        trade = broker_order.trade[0]

        order_type = broker_order.order_type
        limit_price = broker_order.limit_price
        account = broker_order.broker_account

        contract_object = futuresContract(instrument_code, contract_id)
        contract_object_with_ib_data = self.futures_contract_data.get_contract_object_with_IB_metadata(contract_object)

        trade_object = self.ibconnection.broker_submit_single_leg_order(contract_object_with_ib_data, trade, account,
                                                  order_type = order_type,
                                                  limit_price = limit_price)


        return trade_object

    def broker_id_from_trade_object(self, trade_object):
        permid = trade_object.order.permId
        orderid = trade_object.order.orderId
        clientid = trade_object.order.clientId

        return orderid, permid, clientid


    def create_broker_order_object(self, raw_order):
        """
        Map from the data IB gives us to my broker order object

        :param raw_order: named tuple with fields defined in ibClient
        :return: brokerOrder
        """

        sec_type = raw_order.contract.ib_sectype
        if sec_type!="FUT":
            ## Doesn't handle non futures trades, just ignores them
            return missing_order

        strategy_name="NOT_MATCHED"


        instrument_code=self.futures_contract_data.get_instrument_code_from_broker_code(raw_order.contract.ib_instrument_code)
        contract_id=raw_order.contract.ib_contract_id

        # NOT A SPREAD ORDER

        order_sign = raw_order.order.order_sign
        remain_qty = raw_order.order.remain_qty * order_sign
        fill=raw_order.total_filled*order_sign
        trade_size = fill + remain_qty


        algo_comment = raw_order.algo_msg
        order_type=raw_order.order.type
        limit_price = raw_order.order.limit_price
        broker_account=raw_order.order.account
        broker_permid=raw_order.order.perm_id


        broker_clientid, broker_tempid, filled_price, fill_datetime, commission = self.extract_totals_from_fill_data(raw_order.fills)

        broker_order = brokerOrder(strategy_name, instrument_code, [contract_id], [trade_size],  fill=[fill],
                         order_type=order_type, limit_price=limit_price, filled_price=filled_price,
                        algo_comment=algo_comment,
                         fill_datetime=fill_datetime,
                         broker_account=broker_account,
                         commission=commission,
                         broker_permid=broker_permid, broker_tempid=broker_tempid,
                                   broker_clientid=broker_clientid)

        return broker_order

    def extract_totals_from_fill_data(self, list_of_fills):
        """
        Sum up info over fills

        :param list_of_fills: list of named tuples
        :return: average_filled_price, commission (as list of tuples), total quantity filled
        """
        if len(list_of_fills)==0:
            return no_order_id, no_order_id, None, None, 0.0

        qty_and_price_and_datetime_and_id = [(fill.cum_qty, fill.avg_price, fill.time,
                                              fill.temp_id, fill.client_id) for fill in list_of_fills]

        ## sort by total quantity
        qty_and_price_and_datetime_and_id.sort(key = lambda x:x[0])

        final_fill = qty_and_price_and_datetime_and_id[-1]
        _, filled_price, fill_datetime, broker_tempid, broker_clientid = final_fill

        commission = [currencyValue(fill.commission_ccy, fill.commission) for fill in list_of_fills]

        return broker_clientid, broker_tempid, filled_price, fill_datetime, commission