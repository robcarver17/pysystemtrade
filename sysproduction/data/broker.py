import datetime

from syscore.objects import missing_data, arg_not_supplied, missing_order

from sysdata.production.current_positions import contractPosition

from sysexecution.broker_orders import create_new_broker_order_from_contract_order, log_attributes_from_broker_order
from sysexecution.contract_orders import log_attributes_from_contract_order

from sysproduction.data.get_data import dataBlob
from sysproduction.data.positions import diagPositions
from sysproduction.data.currency_data import currencyData

class dataBroker(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("ibFxPricesData ibFuturesContractPriceData ibFuturesContractData\
        ibContractPositionData ibOrdersData ibMiscData"
                            )
        self.data = data


    def get_fx_prices(self, fx_code):
        return self.data.broker_fx_prices.get_fx_prices(fx_code)

    def get_list_of_fxcodes(self):
        return self.data.broker_fx_prices.get_list_of_fxcodes()

    def get_fx_prices(self, fx_code):
        return self.data.broker_fx_prices.get_fx_prices(fx_code)

    def get_prices_at_frequency_for_contract_object(self, contract_object, frequency):
        return self.data.broker_futures_contract_price.get_prices_at_frequency_for_contract_object(contract_object, frequency)

    def get_actual_expiry_date_for_instrument_code_and_contract_date(self, instrument_code, contract_date):
        return self.data.broker_futures_contract. \
            get_actual_expiry_date_for_instrument_code_and_contract_date(instrument_code, contract_date)

    def get_actual_expiry_date_for_contract(self, contract_object):
        return self.data.broker_futures_contract.get_actual_expiry_date_for_contract(contract_object)

    def get_brokers_instrument_code(self, instrument_code):
        return self.data.broker_futures_contract.get_brokers_instrument_code(instrument_code)

    def get_all_current_contract_positions(self):
        return self.data.broker_contract_position.get_all_current_positions_as_list_with_contract_objects()

    def update_expiries_for_position_list_with_IB_expiries(self, original_position_list):

        for idx in range(len(original_position_list)):
            position_entry = original_position_list[idx]
            actual_expiry = self.get_actual_expiry_date_for_contract(position_entry.contract_object).as_str()
            new_entry = contractPosition(position_entry.position,
                                         position_entry.instrument_code,
                                         actual_expiry)
            original_position_list[idx] = new_entry

        return original_position_list


    def get_list_of_breaks_between_broker_and_db_contract_positions(self):
        diag_positions = diagPositions(self.data)
        db_contract_positions = diag_positions.get_all_current_contract_positions()
        db_contract_positions = self.update_expiries_for_position_list_with_IB_expiries(db_contract_positions)
        broker_contract_positions = self.get_all_current_contract_positions()

        break_list = db_contract_positions.return_list_of_breaks(broker_contract_positions)

        return break_list

    def get_and_submit_broker_order_for_contract_order_as_market_order_with_quantity(self, contract_order, qty):

        log = log_attributes_from_contract_order(self.data.log, contract_order)
        broker = self.get_broker_name()
        broker_account = self.get_broker_account()
        broker_clientid = self.get_broker_clientid()

        # Check market closed?
        side_price, mid_price = self.check_market_conditions_for_contract_order(contract_order)

        broker_order = create_new_broker_order_from_contract_order(contract_order, qty, order_type="market",
                                                   side_price=side_price, mid_price=mid_price,
                                                                   algo_comment="market order",
                                                                   broker=broker, broker_account=broker_account,
                                                                   broker_clientid=broker_clientid)

        submitted_broker_order = self.\
            submit_broker_order(broker_order)

        if submitted_broker_order is missing_order:
            return missing_order


        return submitted_broker_order

    def get_broker_account(self):
        return self.data.broker_misc.get_broker_account()

    def get_broker_clientid(self):
        return self.data.broker_misc.get_broker_clientid()

    def get_broker_name(self):
        return self.data.broker_misc.get_broker_name()

    def check_market_conditions_for_contract_order(self, contract_order):
        """

        :param contract_order:
        :return: tuple: side_price, mid_price OR missing_data
        """

        return None, None

    def submit_broker_order(self, broker_order):
        """

        :param broker_order: a broker_order
        :return: broker order id with information added, or missing_order if couldn't submit
        """
        trade_object = self.data.broker_orders.put_order_on_stack(broker_order)
        if trade_object is missing_order:
            return missing_order

        orderid, permid, clientid = self.data.broker_orders.broker_id_from_trade_object(trade_object)

        # ADD single method to do this
        broker_order.submit_datetime = datetime.datetime.now()
        broker_order.broker_permid = permid
        broker_order.broker_tempid = orderid
        broker_order.broker_clientid = clientid

        return broker_order

    def get_list_of_orders(self):
        list_of_orders = self.data.broker_orders.get_list_of_broker_orders()

        list_of_orders_with_commission = [self.calculate_total_commission_for_broker_order(broker_order) \
                            for broker_order in list_of_orders]

        return list_of_orders_with_commission

    def calculate_total_commission_for_broker_order(self, broker_order):
        """
        This turns a broker_order with non-standard commission field (list of tuples) into a single figure
        in base currency

        :return: broker_order
        """

        currency_data = currencyData(self.data)
        if isinstance(broker_order.commission, float):
            base_values = [broker_order.commission]
        else:
            base_values = [currency_data.currency_value_in_base(ccy_value) for ccy_value in broker_order.commission]

        commission = sum(base_values)
        broker_order.commission = commission

        return broker_order

    def match_db_broker_order_to_order_from_brokers(self, broker_order_to_match):
        """

        :return: brokerOrder coming from broker
        """

        list_of_broker_orders = self.get_list_of_orders()

        ## Match on permid
        permid_to_match = broker_order_to_match.broker_permid

        if permid_to_match=='' or permid_to_match==0:
            ## match on temp id and clientid
            matched_order = match_order_on_tempid(list_of_broker_orders, broker_order_to_match)
        else:
            ## match on permid
            matched_order = match_order_on_permid(list_of_broker_orders, broker_order_to_match)

        verified = self.verify_match(broker_order_to_match, matched_order)
        if not verified:
            return missing_order

        return matched_order

    def verify_match(self, broker_order_to_match, matched_order):
        if matched_order is missing_order:
            return False

        ## BETTER OFF IN BROKER ORDER CODE?
        try:
            assert broker_order_to_match.instrument_code == matched_order.instrument_code

            ## NO spreads... yet
            assert len(broker_order_to_match.contract_id)==1
            assert len(matched_order.contract_id)==1

            original_expiry = self.\
                get_actual_expiry_date_for_instrument_code_and_contract_date(\
                broker_order_to_match.instrument_code, broker_order_to_match.contract_id[0]).as_str()

            matched_expiry = matched_order.contract_id[0]
            assert original_expiry == matched_expiry

            assert broker_order_to_match.trade[0] == matched_order.trade[0]

            return True
        except:
            return False

    def get_actual_expiry_for_broker_order_IB_expiries(self, original_order_list):
        """
        for idx in range(len(original_position_list)):
            position_entry = original_position_list[idx]
            actual_expiry = self.get_actual_expiry_date_for_contract(position_entry.contract_object).as_str()
            new_entry = contractPosition(position_entry.position,
                                         position_entry.instrument_code,
                                         actual_expiry)
            original_position_list[idx] = new_entry

        return original_position_list
        """
        pass

    def update_broker_order_db_stack_with_broker_fills_and_info(self, broker_order_stack):
        pass


def match_order_on_permid(list_of_broker_orders, broker_order_to_match):
    permid_list = [order.broker_permid for order in list_of_broker_orders]
    try:
        permid_idx = permid_list.index(broker_order_to_match.broker_permid)
    except  ValueError:
        return missing_order

    matched_order = list_of_broker_orders[permid_idx]

    return matched_order


def match_order_on_tempid(list_of_broker_orders, broker_order_to_match):
    matched_order_list = [order for order in list_of_broker_orders
                          if order.broker_tempid == broker_order_to_match.broker_tempid
                          and order.broker_clientid == broker_order_to_match.broker_clientid]
    if len(matched_order_list)>1:
        return missing_order
    if len(matched_order_list)==0:
        return missing_order

    matched_order = matched_order_list[0]

    return matched_order

