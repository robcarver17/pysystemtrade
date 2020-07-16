import datetime

import numpy as np

from syscore.objects import missing_data, arg_not_supplied, missing_order

from sysdata.production.current_positions import contractPosition

from sysexecution.broker_orders import create_new_broker_order_from_contract_order
from sysexecution.tick_data import analyse_tick_data_frame,empty_tick

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

    def broker_fx_balances(self):
        return self.data.broker_misc.broker_fx_balances()

    def get_fx_prices(self, fx_code):
        return self.data.broker_fx_prices.get_fx_prices(fx_code)

    def get_list_of_fxcodes(self):
        return self.data.broker_fx_prices.get_list_of_fxcodes()


    def broker_fx_market_order(self, trade, ccy1, account = arg_not_supplied, ccy2="USD"):
        account = self.get_broker_account()
        result = self.data.broker_misc.broker_fx_market_order(trade, ccy1, ccy2="USD", account = account)
        if result is missing_order:
            self.log.warn("%s %s is not recognised by broker - try inverting" % (ccy1, ccy2))

        return result

    def get_prices_at_frequency_for_contract_object(self, contract_object, frequency):
        return self.data.broker_futures_contract_price.get_prices_at_frequency_for_contract_object(contract_object, frequency)

    def get_recent_bid_ask_tick_data_for_order(self, order):
        return self.data.broker_futures_contract_price.\
            get_recent_bid_ask_tick_data_for_order( order)

    def get_recent_bid_ask_tick_data_for_instrument_code_and_contract_date(self, instrument_code, contract_date):
        return self.data.broker_futures_contract_price.\
            get_recent_bid_ask_tick_data_for_instrument_code_and_contract_date(instrument_code, contract_date)

    def get_actual_expiry_date_for_instrument_code_and_contract_date(self, instrument_code, contract_date):
        return self.data.broker_futures_contract. \
            get_actual_expiry_date_for_instrument_code_and_contract_date(instrument_code, contract_date)

    def get_actual_expiry_date_for_contract(self, contract_object):
        return self.data.broker_futures_contract.get_actual_expiry_date_for_contract(contract_object)

    def get_brokers_instrument_code(self, instrument_code):
        return self.data.broker_futures_contract.get_brokers_instrument_code(instrument_code)

    def is_instrument_code_and_contract_date_okay_to_trade(self, instrument_code, contract_id):
        check_open = self.data.broker_futures_contract.is_instrument_code_and_contract_date_okay_to_trade(instrument_code, contract_id)
        return check_open

    def get_trading_hours_for_instrument_code_and_contract_date(self, instrument_code, contract_id):
        result = self.data.broker_futures_contract.get_trading_hours_for_instrument_code_and_contract_date(instrument_code, contract_id)
        return result


    def get_all_current_contract_positions(self):
        account_id = self.get_broker_account()
        return self.data.broker_contract_position.get_all_current_positions_as_list_with_contract_objects(account_id=account_id)

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

    def get_ticker_object_for_order(self, order):
        ticker_object = self.data.broker_futures_contract_price.get_ticker_object_for_order(order)
        return ticker_object

    def cancel_market_data_for_order(self, order):
        self.data.broker_futures_contract_price.cancel_market_data_for_order(order)


    def get_and_submit_broker_order_for_contract_order_with_quantity(self, contract_order, qty,
                                                                                     limit_price = None,
                                                                     order_type = "market"):

        log = contract_order.log_with_attributes(self.data.log)
        broker = self.get_broker_name()
        broker_account = self.get_broker_account()
        broker_clientid = self.get_broker_clientid()

        side_prices, mid_prices = self.get_benchmark_prices_for_contract_order_by_leg(contract_order)

        broker_order = create_new_broker_order_from_contract_order(contract_order, qty, order_type=order_type,
                                                   side_price=side_prices, mid_price=mid_prices,
                                                                   broker=broker, broker_account=broker_account,
                                                                   broker_clientid=broker_clientid,
                                                                   limit_price=limit_price)

        log.msg("Created a broker order %s (not yet submitted or written to local DB)" % str(broker_order))
        placed_broker_order_with_controls = self.\
            submit_broker_order(broker_order)

        if placed_broker_order_with_controls is missing_order:
            log.warn("Order could not be submitted")
            return missing_order

        log = placed_broker_order_with_controls.order.log_with_attributes(log)
        log.msg("Submitted order to IB %s" % str(placed_broker_order_with_controls.order))

        return placed_broker_order_with_controls

    def get_broker_account(self):
        return self.data.broker_misc.get_broker_account()

    def get_broker_clientid(self):
        return self.data.broker_misc.get_broker_clientid()

    def get_broker_name(self):
        return self.data.broker_misc.get_broker_name()

    def get_net_mid_price_for_contract_order_by_leg(self, contract_order):
        market_conditions = self.get_market_conditions_for_contract_order_by_leg(contract_order)
        if market_conditions is missing_data:
            return np.nan

        mid_prices = [x.mid_price for x in market_conditions]
        net_mid_price = contract_order.trade.get_spread_price(mid_prices)

        return net_mid_price

    def get_benchmark_prices_for_contract_order_by_leg(self, contract_order):
        market_conditions = self.get_market_conditions_for_contract_order_by_leg(contract_order)
        if market_conditions is missing_data:
            return np.nan
        side_prices = [x.side_price for x in market_conditions]
        mid_prices = [x.mid_price for x in market_conditions]

        return side_prices, mid_prices

    def get_largest_offside_liquid_size_for_contract_order_by_leg(self, contract_order):
        ## Get the smallest size available on each side - most conservative for spread orders
        _side_qty_not_used, offside_qty = self.get_current_size_for_contract_order_by_leg(contract_order)

        new_qty = contract_order.trade.apply_minima(offside_qty)

        return new_qty

    def get_current_size_for_contract_order_by_leg(self, contract_order):
        market_conditions = self.get_market_conditions_for_contract_order_by_leg(contract_order)
        if market_conditions is missing_data:
            side_qty = offside_qty = contract_order.trade.zero_version()
            return side_qty, offside_qty

        side_qty = [x.side_qty for x in market_conditions]
        offside_qty = [x.offside_qty for x in market_conditions]

        return side_qty, offside_qty


    def get_market_conditions_for_contract_order_by_leg(self, contract_order):
        market_conditions = []
        instrument_code = contract_order.instrument_code
        for contract_date, qty in zip(contract_order.contract_id, contract_order.trade.qty):
            market_conditions_this_contract = \
                self.check_market_conditions_for_single_contract_trade(instrument_code, contract_date, qty)
            if market_conditions_this_contract is missing_data:
                return missing_data

            market_conditions.append(market_conditions_this_contract)

        return market_conditions


    def check_market_conditions_for_single_contract_trade(self,instrument_code, contract_date, qty):
        """
        Get current prices

        :param contract_order:
        :return: tuple: side_price, mid_price OR missing_data
        """

        tick_data = self.get_recent_bid_ask_tick_data_for_instrument_code_and_contract_date(instrument_code, contract_date)
        analysis_of_tick_data = analyse_tick_data_frame(tick_data, qty)

        return analysis_of_tick_data


    def submit_broker_order(self, broker_order):
        """

        :param broker_order: a broker_order
        :return: broker order id with information added, or missing_order if couldn't submit
        """
        placed_broker_order_with_controls = self.data.broker_orders.put_order_on_stack(broker_order)
        if placed_broker_order_with_controls is missing_order:
            return missing_order

        return placed_broker_order_with_controls


    def get_list_of_orders(self):
        list_of_orders = self.data.broker_orders.get_list_of_broker_orders()

        list_of_orders_with_commission = [self.calculate_total_commission_for_broker_order(broker_order) \
                            for broker_order in list_of_orders]

        return list_of_orders_with_commission

    def get_list_of_orders_for_matching(self):
        account_id = self.get_broker_account()
        list_of_orders = self.data.broker_orders.get_list_of_broker_orders_using_external_tempid(account_id=account_id)
        list_of_orders_with_commission = [self.calculate_total_commission_for_broker_order(broker_order) \
                            for broker_order in list_of_orders]

        return list_of_orders_with_commission


    def get_list_of_placed_orders(self):
        dict_of_orders = self.data.broker_orders.get_dict_of_orders_from_storage()

        list_of_orders_with_commission = [self.calculate_total_commission_for_broker_order(broker_order) \
                            for broker_order in dict_of_orders.values()]

        return list_of_orders_with_commission


    def calculate_total_commission_for_broker_order(self, broker_order):
        """
        This turns a broker_order with non-standard commission field (list of tuples) into a single figure
        in base currency

        :return: broker_order
        """
        if broker_order is missing_order:
            return broker_order

        if broker_order.commission is None:
            return broker_order

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
        matched_order = self.data.broker_orders.match_db_broker_order_to_order_from_brokers(broker_order_to_match)

        matched_order = self.calculate_total_commission_for_broker_order(matched_order)

        return matched_order

    def cancel_order_given_control_object(self, broker_orders_with_controls):
        self.data.broker_orders.cancel_order_given_control_object(broker_orders_with_controls)

    def cancel_order_on_stack(self, broker_order):
        account_id = self.get_broker_account()
        result = self.data.broker_orders.cancel_order_on_stack(broker_order)

        return result

    def check_order_is_cancelled(self, broker_order):
        result = self.data.broker_orders.check_order_is_cancelled(broker_order)

        return result

    def check_order_is_cancelled_given_control_object(self, broker_order_with_controls):
        result = self.data.broker_orders.check_order_is_cancelled_given_control_object(broker_order_with_controls)

        return result

    def modify_limit_price_given_control_object(self, broker_order_with_controls, new_limit_price):
        new_order_with_controls = self.data.broker_orders.modify_limit_price_given_control_object(broker_order_with_controls, new_limit_price)
        return new_order_with_controls