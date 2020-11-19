import datetime

import numpy as np

from collections import namedtuple

from sysbrokers.IB.ib_capital_data import ibCapitalData
from sysbrokers.IB.ib_spot_FX_data import ibFxPricesData
from sysbrokers.IB.ib_futures_contract_price_data import ibFuturesContractPriceData
from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
from sysbrokers.IB.ib_position_data import ibContractPositionData
from sysbrokers.IB.ib_orders_data import ibOrdersData
from sysbrokers.IB.ib_misc_data import ibMiscData

from syscore.objects import missing_data, arg_not_supplied, missing_order, missing_contract

from sysdata.production.current_positions import contractPosition

from sysexecution.base_orders import adjust_spread_order_single_benchmark
from sysexecution.broker_orders import create_new_broker_order_from_contract_order
from sysexecution.tick_data import analyse_tick_data_frame

from sysobjects.contracts import futuresContract

from sysproduction.data.get_data import dataBlob
from sysproduction.data.positions import diagPositions
from sysproduction.data.currency_data import currencyData
from sysproduction.data.controls import diagProcessConfig

benchmarkPriceCollection = namedtuple(
    "benchmarkPriceCollection",
    ["side_price", "offside_price", "benchmark_side_prices", "benchmark_mid_prices"],
)


class dataBroker(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list([
            ibFxPricesData, ibFuturesContractPriceData, ibFuturesContractData,
        ibContractPositionData, ibOrdersData, ibMiscData, ibCapitalData,
        ibFuturesInstrumentData]
        )
        self.data = data

    def broker_fx_balances(self):
        return self.data.broker_misc.broker_fx_balances()

    def get_fx_prices(self, fx_code):
        return self.data.broker_fx_prices.get_fx_prices(fx_code)

    def get_list_of_fxcodes(self):
        return self.data.broker_fx_prices.get_list_of_fxcodes()

    def broker_fx_market_order(
            self,
            trade,
            ccy1,
            account=arg_not_supplied,
            ccy2="USD"):
        account = self.get_broker_account()
        result = self.data.broker_misc.broker_fx_market_order(
            trade, ccy1, ccy2="USD", account=account
        )
        if result is missing_order:
            self.log.warn(
                "%s %s is not recognised by broker - try inverting" %
                (ccy1, ccy2))

        return result

    def get_prices_at_frequency_for_contract_object(
            self, contract_object, frequency):
        return self.data.broker_futures_contract_price.get_prices_at_frequency_for_contract_object(
            contract_object, frequency)

    def get_recent_bid_ask_tick_data_for_order(self, order):
        return self.data.broker_futures_contract_price.get_recent_bid_ask_tick_data_for_order(
            order)



    def get_recent_bid_ask_tick_data_for_contract_object(
        self, contract
    ):
        return self.data.broker_futures_contract_price.get_recent_bid_ask_tick_data_for_contract_object(contract)


    def get_actual_expiry_date_for_contract(self, contract_object):
        return self.data.broker_futures_contract.get_actual_expiry_date_for_contract(
            contract_object)

    def get_brokers_instrument_code(self, instrument_code):
        return self.data.broker_futures_instrument.get_brokers_instrument_code(
            instrument_code
        )

    def less_than_one_hour_of_trading_leg_for_instrument_code_and_contract_date(
            self, instrument_code, contract_date):
        # FIXME REMOVE
        contract = futuresContract(instrument_code, contract_date)
        result = self.less_than_one_hour_of_trading_leg_for_contract(contract)

        return result

    def less_than_one_hour_of_trading_leg_for_contract(
            self, contract: futuresContract):

        diag_controls = diagProcessConfig()
        hours_left_before_process_finishes = diag_controls.how_long_in_hours_before_trading_process_finishes()

        if hours_left_before_process_finishes<1:
            ## irespective of instrument traded
            return True

        result = self.data.broker_futures_contract.less_than_one_hour_of_trading_leg_for_contract(contract)

        return result

    def is_contract_okay_to_trade(self, contract):
        check_open = self.data.broker_futures_contract.is_contract_okay_to_trade(contract)
        return check_open

    def is_instrument_code_and_contract_date_okay_to_trade(
        self, instrument_code, contract_id
    ):
        #FIXME REMOVE
        futures_contract = futuresContract(instrument_code, contract_id)
        check_open = self.is_contract_okay_to_trade(futures_contract)
        return check_open

    def get_min_tick_size_for_instrument_code_and_contract_date(self, instrument_code, contract_id):
        # FIXME REMOVE
        result = self.get_min_tick_size_for_contract(futuresContract(instrument_code, contract_id))
        return result

    def get_min_tick_size_for_contract(self, contract):
        result = self.data.broker_futures_contract.get_min_tick_size_for_contract(contract)
        return result


    def get_trading_hours_for_instrument_code_and_contract_date(
        self, instrument_code, contract_id
    ):
        # FIXME REMOVE
        result = self.get_trading_hours_for_contract(futuresContract(instrument_code, contract_id))
        return result


    def get_trading_hours_for_contract(
        self, contract
    ):
        result = self.data.broker_futures_contract.get_trading_hours_for_contract(contract)
        return result

    def get_all_current_contract_positions(self):
        account_id = self.get_broker_account()
        return self.data.broker_contract_position.get_all_current_positions_as_list_with_contract_objects(
            account_id=account_id)

    def update_expiries_for_position_list_with_IB_expiries(
        self, original_position_list
    ):

        for idx in range(len(original_position_list)):
            position_entry = original_position_list[idx]
            actual_expiry = self.get_actual_expiry_date_for_contract(
                position_entry.contract_object
            ).as_str()
            new_entry = contractPosition(
                position_entry.position,
                position_entry.instrument_code,
                actual_expiry)
            original_position_list[idx] = new_entry

        return original_position_list

    def get_list_of_breaks_between_broker_and_db_contract_positions(self):
        db_contract_positions = self.get_db_contract_positions_with_IB_expiries()
        broker_contract_positions = self.get_all_current_contract_positions()

        break_list = db_contract_positions.return_list_of_breaks(
            broker_contract_positions
        )

        return break_list

    def get_db_contract_positions_with_IB_expiries(self):
        diag_positions = diagPositions(self.data)
        db_contract_positions = diag_positions.get_all_current_contract_positions()
        db_contract_positions = self.update_expiries_for_position_list_with_IB_expiries(
            db_contract_positions)

        return db_contract_positions

    def get_ticker_object_for_order(self, order):
        ticker_object = (
            self.data.broker_futures_contract_price.get_ticker_object_for_order(order))
        return ticker_object

    def cancel_market_data_for_order(self, order):
        self.data.broker_futures_contract_price.cancel_market_data_for_order(
            order)

    def get_and_submit_broker_order_for_contract_order(
        self,
        contract_order,
        input_limit_price=None,
        order_type="market",
        limit_price_from="input",
        ticker_object=None,
    ):

        log = contract_order.log_with_attributes(self.data.log)
        broker = self.get_broker_name()
        broker_account = self.get_broker_account()
        broker_clientid = self.get_broker_clientid()

        if ticker_object is None:
            ticker_object = self.get_ticker_object_for_order(contract_order)

        ticker_object, collected_prices = self.get_market_data_for_order(
            ticker_object, contract_order
        )
        if collected_prices is missing_order:
            # no data available, no can do
            return missing_order

        if order_type == "limit":
            limit_price = self.set_limit_price(
                contract_order,
                collected_prices.side_price,
                collected_prices.offside_price,
                limit_price_from=limit_price_from,
                input_limit_price=input_limit_price,
            )
        else:
            limit_price = None

        broker_order = create_new_broker_order_from_contract_order(
            contract_order,
            order_type=order_type,
            side_price=collected_prices.benchmark_side_prices,
            mid_price=collected_prices.benchmark_mid_prices,
            broker=broker,
            broker_account=broker_account,
            broker_clientid=broker_clientid,
            limit_price=limit_price,
        )

        log.msg(
            "Created a broker order %s (not yet submitted or written to local DB)" %
            str(broker_order))
        placed_broker_order_with_controls = self.submit_broker_order(
            broker_order)

        if placed_broker_order_with_controls is missing_order:
            log.warn("Order could not be submitted")
            return missing_order

        log = placed_broker_order_with_controls.order.log_with_attributes(log)
        log.msg("Submitted order to IB %s" %
                str(placed_broker_order_with_controls.order))

        placed_broker_order_with_controls.add_or_replace_ticker(ticker_object)

        return placed_broker_order_with_controls

    def get_broker_account(self):
        return self.data.broker_misc.get_broker_account()

    def get_broker_clientid(self):
        return self.data.broker_misc.get_broker_clientid()

    def get_broker_name(self):
        return self.data.broker_misc.get_broker_name()

    def get_market_data_for_order(self, ticker_object, contract_order):
        # We use prices for a couple of reasons:
        # to provide a benchmark for execution purposes
        # (optionally) to set limit prices
        ##
        # We get prices from two sources:
        # A tick stream in ticker object
        # Historical ticks
        ##
        log = contract_order.log_with_attributes(self.data.log)

        # Get the first 'reference' tick
        reference_tick = (
            ticker_object.wait_for_valid_bid_and_ask_and_return_current_tick(
                wait_time_seconds=10
            )
        )

        # Try and get limit price from ticker
        # We ignore the limit price given in the contract order: need to create
        # a different order type for those
        tick_analysis = ticker_object.analyse_for_tick(reference_tick)

        if tick_analysis is missing_data:
            """
            Here's a possible solution for markets with no active spread orders, but it has potential problems
            So probably better to do these as market orders

            ## Get limit price from legs: we use the mid price because the net of offside prices is likely to be somewhat optimistic
            ## limit_price_from_legs = data_broker.get_net_mid_price_for_contract_order_by_leg(remaining_contract_order)

            #limit_price = limit_price_from_legs

            """
            log.warn(
                "Can't get market data for %s so not trading with limit order %s" %
                (contract_order.instrument_code, str(contract_order)))
            return ticker_object, missing_order

        ticker_object.clear_and_add_reference_as_first_tick(reference_tick)

        # These prices will be used for limit price purposes
        # They are scalars
        side_price = tick_analysis.side_price
        offside_price = tick_analysis.offside_price
        mid_price = tick_analysis.mid_price

        if contract_order.calendar_spread_order:
            # For spread orders, we use the tick stream to get the limit price, and the historical ticks for the benchmark
            # This is because we benchmark on each individual contract price,
            # and the tick stream is just for the spread

            benchmarks = self.get_benchmark_prices_for_contract_order_by_leg(
                contract_order
            )
            if benchmarks is missing_data:
                log.warn(
                    "Can't get individual component market data for %s so not trading with limit order %s" %
                    (contract_order.instrument_code, str(contract_order)))
                return ticker_object, missing_order

            benchmark_side_prices, benchmark_mid_prices = benchmarks

            # We need to adjust these so they are consistent with the initial
            # spread
            benchmark_side_prices = adjust_spread_order_single_benchmark(
                contract_order, benchmark_side_prices, side_price
            )
            benchmark_mid_prices = adjust_spread_order_single_benchmark(
                contract_order, benchmark_mid_prices, mid_price
            )

        else:
            # For non spread orders, we use the tick stream to get both the limit prices and the benchmark
            # These need to be converted into lists, as the tick stream
            # provides scalars only
            benchmark_side_price_scalar = side_price
            benchmark_mid_price_scalar = mid_price

            benchmark_side_prices = [benchmark_side_price_scalar]
            benchmark_mid_prices = [benchmark_mid_price_scalar]

        collected_prices = benchmarkPriceCollection(
            side_price, offside_price, benchmark_side_prices, benchmark_mid_prices)

        return ticker_object, collected_prices

    def set_limit_price(
        self,
            contract_order,
        side_price,
        offside_price,
        input_limit_price=None,
        limit_price_from="input",
    ):
        assert limit_price_from in ["input", "side_price", "offside_price"]

        if limit_price_from == "input":
            assert input_limit_price is not None
            limit_price = input_limit_price
        elif limit_price_from == "side_price":
            limit_price = side_price
        elif limit_price_from == "offside_price":
            limit_price = offside_price

        limit_price_rounded = self.round_limit_price_to_tick_size(contract_order, limit_price)

        return limit_price_rounded

    def round_limit_price_to_tick_size(self, contract_order, limit_price):
        instrument_code = contract_order.instrument_code
        contract_id = contract_order.contract_id

        min_tick = self.get_min_tick_size_for_instrument_code_and_contract_date(instrument_code, contract_id)
        if min_tick is missing_contract:
            log = contract_order.log_with_attributes(self.data.log)
            log.warn("Couldn't find min tick size for %s %s, not rounding limit price %f" % (instrument_code,
                                                                                             contract_id,
                                                                                             limit_price))

            return limit_price

        rounded_limit_price = min_tick * round(limit_price / min_tick)

        return rounded_limit_price

    def get_net_mid_price_for_contract_order_by_leg(self, contract_order):
        market_conditions = self.get_market_conditions_for_contract_order_by_leg(
            contract_order)
        if market_conditions is missing_data:
            return np.nan

        mid_prices = [x.mid_price for x in market_conditions]
        net_mid_price = contract_order.trade.get_spread_price(mid_prices)

        return net_mid_price

    def get_benchmark_prices_for_contract_order_by_leg(self, contract_order):
        market_conditions = self.get_market_conditions_for_contract_order_by_leg(
            contract_order)
        if market_conditions is missing_data:
            return missing_data
        side_prices = [x.side_price for x in market_conditions]
        mid_prices = [x.mid_price for x in market_conditions]

        return side_prices, mid_prices

    def get_largest_offside_liquid_size_for_contract_order_by_leg(
            self, contract_order):
        # Get the smallest size available on each side - most conservative for
        # spread orders
        (
            _side_qty_not_used,
            offside_qty,
        ) = self.get_current_size_for_contract_order_by_leg(contract_order)

        new_qty = contract_order.trade.apply_minima(offside_qty)

        return new_qty

    def get_current_size_for_contract_order_by_leg(self, contract_order):
        market_conditions = self.get_market_conditions_for_contract_order_by_leg(
            contract_order)
        if market_conditions is missing_data:
            side_qty = offside_qty = contract_order.trade.zero_version()
            return side_qty, offside_qty

        side_qty = [x.side_qty for x in market_conditions]
        offside_qty = [x.offside_qty for x in market_conditions]

        return side_qty, offside_qty

    def get_market_conditions_for_contract_order_by_leg(self, contract_order):
        # FIXME FEELS TOO EARLY TO SPRING OUT THE ORDER ELEMENTS
        market_conditions = []
        instrument_code = contract_order.instrument_code
        for contract_date, qty in zip(
            contract_order.contract_id, contract_order.trade.qty
        ):
            contract = futuresContract(instrument_code, contract_date)

            market_conditions_this_contract = (
                self.check_market_conditions_for_single_legged_contract_and_qty(contract, qty)
            )
            if market_conditions_this_contract is missing_data:
                return missing_data

            market_conditions.append(market_conditions_this_contract)

        return market_conditions



    def check_market_conditions_for_single_legged_contract_and_qty(
        self, contract, qty
    ):
        """
        Get current prices

        :param contract_order:
        :return: tuple: side_price, mid_price OR missing_data
        """

        """
        Get current prices

        :param contract_order:
        :return: tuple: side_price, mid_price OR missing_data
        """

        tick_data = self.get_recent_bid_ask_tick_data_for_contract_object(contract)
        analysis_of_tick_data = analyse_tick_data_frame(tick_data, qty)

        return analysis_of_tick_data



    def submit_broker_order(self, broker_order):
        """

        :param broker_order: a broker_order
        :return: broker order id with information added, or missing_order if couldn't submit
        """
        placed_broker_order_with_controls = self.data.broker_orders.put_order_on_stack(
            broker_order)
        if placed_broker_order_with_controls is missing_order:
            return missing_order

        return placed_broker_order_with_controls

    def get_list_of_orders(self):
        account_id = self.get_broker_account()
        list_of_orders = self.data.broker_orders.get_list_of_broker_orders(
            account_id=account_id
        )
        list_of_orders_with_commission = self.add_commissions_to_list_of_orders(
            list_of_orders)

        return list_of_orders_with_commission

    def get_list_of_stored_orders(self):
        list_of_orders = self.data.broker_orders.get_list_of_orders_from_storage()
        list_of_orders_with_commission = self.add_commissions_to_list_of_orders(
            list_of_orders)

        return list_of_orders_with_commission

    def add_commissions_to_list_of_orders(self, list_of_orders):
        list_of_orders_with_commission = [
            self.calculate_total_commission_for_broker_order(broker_order)
            for broker_order in list_of_orders
        ]

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
            base_values = [
                currency_data.currency_value_in_base(ccy_value)
                for ccy_value in broker_order.commission
            ]

        commission = sum(base_values)
        broker_order.commission = commission

        return broker_order

    def match_db_broker_order_to_order_from_brokers(
            self, broker_order_to_match):
        """

        :return: brokerOrder coming from broker
        """
        matched_order = (
            self.data.broker_orders.match_db_broker_order_to_order_from_brokers(
                broker_order_to_match
            )
        )

        matched_order = self.calculate_total_commission_for_broker_order(
            matched_order)

        return matched_order

    def cancel_order_given_control_object(self, broker_order_with_controls):
        self.data.broker_orders.cancel_order_given_control_object(
            broker_order_with_controls
        )

    def cancel_order_on_stack(self, broker_order):
        result = self.data.broker_orders.cancel_order_on_stack(broker_order)

        return result

    def check_order_is_cancelled(self, broker_order):
        result = self.data.broker_orders.check_order_is_cancelled(broker_order)

        return result

    def check_order_is_cancelled_given_control_object(
            self, broker_order_with_controls):
        result = self.data.broker_orders.check_order_is_cancelled_given_control_object(
            broker_order_with_controls)

        return result

    def check_order_can_be_modified_given_control_object(
        self, broker_order_with_controls
    ):
        return self.data.broker_orders.check_order_can_be_modified_given_control_object(
            broker_order_with_controls)

    def modify_limit_price_given_control_object(
        self, broker_order_with_controls, new_limit_price
    ):
        new_order_with_controls = (
            self.data.broker_orders.modify_limit_price_given_control_object(
                broker_order_with_controls, new_limit_price
            )
        )
        return new_order_with_controls

    def get_total_capital_value_in_base_currency(self) ->float:
        currency_data = currencyData(self.data)
        values_across_accounts = self.data.broker_capital.get_account_value_across_currency_across_accounts()

        # This assumes that each account only reports either in one currency or
        # for each currency, i.e. no double counting
        total_account_value_in_base_currency = (
            currency_data.total_of_list_of_currency_values_in_base(
                values_across_accounts
            )
        )

        return total_account_value_in_base_currency
