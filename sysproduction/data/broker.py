from copy import copy
from sysbrokers.IB.ib_capital_data import ibCapitalData
from sysbrokers.IB.ib_Fx_prices_data import ibFxPricesData
from sysbrokers.IB.ib_futures_contract_price_data import ibFuturesContractPriceData
from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
from sysbrokers.IB.ib_contract_position_data import ibContractPositionData
from sysbrokers.IB.ib_orders import ibExecutionStackData
from sysbrokers.IB.ib_static_data import ibStaticData
from sysbrokers.IB.ib_fx_handling import ibFxHandlingData

from sysbrokers.broker_fx_handling import brokerFxHandlingData
from sysbrokers.broker_static_data import brokerStaticData
from sysbrokers.broker_execution_stack import brokerExecutionStackData
from sysbrokers.broker_futures_contract_price_data import brokerFuturesContractPriceData
from sysbrokers.broker_futures_contract_data import brokerFuturesContractData
from sysbrokers.broker_capital_data import brokerCapitalData
from sysbrokers.broker_contract_position_data import brokerContractPositionData
from sysbrokers.broker_fx_prices_data import brokerFxPricesData
from sysbrokers.broker_instrument_data import brokerFuturesInstrumentData

from syscore.objects import (
    arg_not_supplied,
    missing_order,
    missing_contract,
    missing_data,
)
from syscore.dateutils import Frequency

from sysdata.data_blob import dataBlob

from sysexecution.orders.broker_orders import brokerOrder
from sysexecution.orders.list_of_orders import listOfOrders
from sysexecution.tick_data import dataFrameOfRecentTicks
from sysexecution.tick_data import analyse_tick_data_frame, tickerObject, analysisTick
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.trade_qty import tradeQuantity
from sysexecution.order_stacks.broker_order_stack import orderWithControls

from sysobjects.contract_dates_and_expiries import expiryDate
from sysobjects.contracts import futuresContract
from sysobjects.production.positions import contractPosition, listOfContractPositions
from sysobjects.spot_fx_prices import fxPrices
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysproduction.data.positions import diagPositions
from sysproduction.data.currency_data import dataCurrency
from sysproduction.data.control_process import diagControlProcess
from sysproduction.data.generic_production_data import productionDataLayerGeneric


class dataBroker(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        ## Modify these to use another broker
        ## These will be aliased as self.data.broker_fx_prices, self.data.broker_futures_contract_price ... and so on
        data.add_class_list(
            [
                ibFxPricesData,
                ibFuturesContractPriceData,
                ibFuturesContractData,
                ibContractPositionData,
                ibExecutionStackData,
                ibStaticData,
                ibCapitalData,
                ibFuturesInstrumentData,
                ibFxHandlingData,
            ]
        )

        return data

    @property
    def broker_fx_price_data(self) -> brokerFxPricesData:
        return self.data.broker_fx_prices

    @property
    def broker_futures_contract_price_data(self) -> brokerFuturesContractPriceData:
        return self.data.broker_futures_contract_price

    @property
    def broker_futures_contract_data(self) -> brokerFuturesContractData:
        return self.data.broker_futures_contract

    @property
    def broker_futures_instrument_data(self) -> brokerFuturesInstrumentData:
        return self.data.broker_futures_instrument

    @property
    def broker_contract_position_data(self) -> brokerContractPositionData:
        return self.data.broker_contract_position

    @property
    def broker_execution_stack_data(self) -> brokerExecutionStackData:
        return self.data.broker_execution_stack

    @property
    def broker_capital_data(self) -> brokerCapitalData:
        return self.data.broker_capital

    @property
    def broker_fx_handling_data(self) -> brokerFxHandlingData:
        return self.data.broker_fx_handling

    @property
    def broker_static_data(self) -> brokerStaticData:
        return self.data.broker_static

    ## Methods

    def broker_fx_balances(self) -> dict:
        account_id = self.get_broker_account()
        return self.broker_fx_handling_data.broker_fx_balances(account_id=account_id)

    def get_fx_prices(self, fx_code: str) -> fxPrices:
        return self.broker_fx_price_data.get_fx_prices(fx_code)

    def get_list_of_fxcodes(self) -> list:
        return self.broker_fx_price_data.get_list_of_fxcodes()

    def broker_fx_market_order(
        self, trade: float, ccy1: str, account_id: str = arg_not_supplied, ccy2="USD"
    ):
        if account_id is arg_not_supplied:
            account_id = self.get_broker_account()

        result = self.broker_fx_handling_data.broker_fx_market_order(
            trade, ccy1, ccy2=ccy2, account_id=account_id
        )
        if result is missing_order:
            self.log.warn(
                "%s %s is not recognised by broker - try inverting" % (ccy1, ccy2)
            )

    def get_prices_at_frequency_for_contract_object(
        self, contract_object: futuresContract, frequency: Frequency
    ) -> futuresContractPrices:

        return self.broker_futures_contract_price_data.get_prices_at_frequency_for_contract_object(
            contract_object, frequency
        )

    def get_recent_bid_ask_tick_data_for_contract_object(
        self, contract: futuresContract
    ) -> dataFrameOfRecentTicks:
        return self.broker_futures_contract_price_data.get_recent_bid_ask_tick_data_for_contract_object(
            contract
        )

    def get_actual_expiry_date_for_single_contract(
        self, contract_object: futuresContract
    ) -> expiryDate:
        return self.broker_futures_contract_data.get_actual_expiry_date_for_single_contract(
            contract_object
        )

    def get_brokers_instrument_code(self, instrument_code: str) -> str:
        return self.broker_futures_instrument_data.get_brokers_instrument_code(
            instrument_code
        )

    def less_than_N_hours_of_trading_left_for_contract(
        self, contract: futuresContract, N_hours: float = 1.0
    ) -> bool:

        diag_controls = diagControlProcess()
        hours_left_before_process_finishes = (
            diag_controls.how_long_in_hours_before_trading_process_finishes()
        )

        if hours_left_before_process_finishes < N_hours:
            ## irespective of instrument traded
            return True

        result = self.broker_futures_contract_data.less_than_N_hours_of_trading_left_for_contract(
            contract, N_hours=N_hours
        )

        return result

    def is_contract_okay_to_trade(self, contract: futuresContract) -> bool:
        check_open = self.broker_futures_contract_data.is_contract_okay_to_trade(
            contract
        )
        return check_open

    def get_min_tick_size_for_contract(self, contract: futuresContract) -> float:
        result = self.broker_futures_contract_data.get_min_tick_size_for_contract(
            contract
        )
        return result

    def get_trading_hours_for_contract(self, contract: futuresContract) -> list:
        result = self.broker_futures_contract_data.get_trading_hours_for_contract(
            contract
        )
        return result

    def get_all_current_contract_positions(self) -> listOfContractPositions:

        list_of_positions = (
            self.broker_contract_position_data.get_all_current_positions_as_list_with_contract_objects()
        )

        return list_of_positions

    def update_expiries_for_position_list_with_IB_expiries(
        self, original_position_list: listOfContractPositions
    ) -> listOfContractPositions:

        new_position_list = listOfContractPositions()
        for position_entry in original_position_list:
            new_position_entry = self.update_expiry_for_single_position(position_entry)
            new_position_list.append(new_position_entry)

        return new_position_list

    def update_expiry_for_single_position(
        self, position_entry: contractPosition
    ) -> contractPosition:
        original_contract = position_entry.contract
        new_contract = self.update_expiry_for_single_contract(original_contract)

        position = position_entry.position
        new_position_entry = contractPosition(position, new_contract)

        return new_position_entry

    def update_expiry_for_single_contract(
        self, original_contract: futuresContract
    ) -> futuresContract:
        actual_expiry = self.get_actual_expiry_date_for_single_contract(
            original_contract
        )
        if actual_expiry is missing_contract:
            log = original_contract.specific_log(self.data.log)
            log.warn(
                "Contract %s is missing from IB probably expired - need to manually close on DB"
                % str(original_contract)
            )
            new_contract = copy(original_contract)
        else:
            expiry_date_as_str = actual_expiry.as_str()
            instrument_code = original_contract.instrument_code
            new_contract = futuresContract(instrument_code, expiry_date_as_str)

        return new_contract

    def get_list_of_breaks_between_broker_and_db_contract_positions(self) -> list:
        db_contract_positions = self.get_db_contract_positions_with_IB_expiries()
        broker_contract_positions = self.get_all_current_contract_positions()

        break_list = db_contract_positions.return_list_of_breaks(
            broker_contract_positions
        )

        return break_list

    def get_db_contract_positions_with_IB_expiries(self) -> listOfContractPositions:
        diag_positions = diagPositions(self.data)
        db_contract_positions = diag_positions.get_all_current_contract_positions()
        db_contract_positions = self.update_expiries_for_position_list_with_IB_expiries(
            db_contract_positions
        )

        return db_contract_positions

    def get_ticker_object_for_order(self, order: contractOrder) -> tickerObject:
        ticker_object = (
            self.broker_futures_contract_price_data.get_ticker_object_for_order(order)
        )
        return ticker_object

    def cancel_market_data_for_order(self, order: brokerOrder):
        self.broker_futures_contract_price_data.cancel_market_data_for_order(order)

    def get_broker_account(self) -> str:
        return self.broker_static_data.get_broker_account()

    def get_broker_clientid(self) -> int:
        return self.broker_static_data.get_broker_clientid()

    def get_broker_name(self) -> str:
        return self.broker_static_data.get_broker_name()

    def get_largest_offside_liquid_size_for_contract_order_by_leg(
        self, contract_order: contractOrder
    ) -> tradeQuantity:
        # Get the smallest size available on each side - most conservative for
        # spread orders
        (
            _side_qty_not_used,
            offside_qty,
        ) = self.get_current_size_for_contract_order_by_leg(contract_order)

        new_qty = (
            contract_order.trade.reduce_trade_size_proportionally_to_abs_limit_per_leg(
                offside_qty
            )
        )

        return new_qty

    def get_current_size_for_contract_order_by_leg(
        self, contract_order: contractOrder
    ) -> (list, list):
        market_conditions = self.get_market_conditions_for_contract_order_by_leg(
            contract_order
        )
        if market_conditions is missing_data:
            side_qty = offside_qty = len(contract_order.trade) * [0]
            return side_qty, offside_qty

        side_qty = [x.side_qty for x in market_conditions]
        offside_qty = [x.offside_qty for x in market_conditions]

        return side_qty, offside_qty

    def get_market_conditions_for_contract_order_by_leg(
        self, contract_order: contractOrder
    ) -> list:
        market_conditions = []
        list_of_trade_qty = contract_order.trade
        list_of_contracts = (
            contract_order.futures_contract.as_list_of_individual_contracts()
        )
        for contract, qty in zip(list_of_contracts, list_of_trade_qty):

            market_conditions_this_contract = (
                self.check_market_conditions_for_single_legged_contract_and_qty(
                    contract, qty
                )
            )
            if market_conditions_this_contract is missing_data:
                return missing_data

            market_conditions.append(market_conditions_this_contract)

        return market_conditions

    def check_market_conditions_for_single_legged_contract_and_qty(
        self, contract: futuresContract, qty: int
    ) -> analysisTick:
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
        analysis_of_tick_data = analyse_tick_data_frame(
            tick_data, qty, forward_fill=True, replace_qty_nans=True
        )

        return analysis_of_tick_data

    def submit_broker_order(self, broker_order: brokerOrder) -> orderWithControls:
        """

        :param broker_order: a broker_order
        :return: broker order id with information added, or missing_order if couldn't submit
        """
        placed_broker_order_with_controls = (
            self.broker_execution_stack_data.put_order_on_stack(broker_order)
        )

        return placed_broker_order_with_controls

    def get_list_of_orders(self) -> listOfOrders:
        account_id = self.get_broker_account()
        list_of_orders = (
            self.broker_execution_stack_data.get_list_of_broker_orders_with_account_id(
                account_id=account_id
            )
        )
        list_of_orders_with_commission = self.add_commissions_to_list_of_orders(
            list_of_orders
        )

        return list_of_orders_with_commission

    def get_list_of_stored_orders(self) -> listOfOrders:
        list_of_orders = (
            self.broker_execution_stack_data.get_list_of_orders_from_storage()
        )
        list_of_orders_with_commission = self.add_commissions_to_list_of_orders(
            list_of_orders
        )

        return list_of_orders_with_commission

    def add_commissions_to_list_of_orders(
        self, list_of_orders: listOfOrders
    ) -> listOfOrders:
        list_of_orders_with_commission = [
            self.calculate_total_commission_for_broker_order(broker_order)
            for broker_order in list_of_orders
        ]
        list_of_orders_with_commission = listOfOrders(list_of_orders_with_commission)

        return list_of_orders_with_commission

    def calculate_total_commission_for_broker_order(
        self, broker_order: brokerOrder
    ) -> brokerOrder:
        """
        This turns a broker_order with non-standard commission field (list of tuples) into a single figure
        in base currency

        :return: broker_order
        """
        if broker_order is missing_order:
            return broker_order

        if broker_order.commission is None:
            return broker_order

        currency_data = dataCurrency(self.data)
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
        self, broker_order_to_match: brokerOrder
    ) -> brokerOrder:
        """

        :return: brokerOrder coming from broker
        """
        matched_order = self.broker_execution_stack_data.match_db_broker_order_to_order_from_brokers(
            broker_order_to_match
        )

        matched_order = self.calculate_total_commission_for_broker_order(matched_order)

        return matched_order

    def cancel_order_given_control_object(
        self, broker_order_with_controls: orderWithControls
    ):
        self.broker_execution_stack_data.cancel_order_given_control_object(
            broker_order_with_controls
        )

    def cancel_order_on_stack(self, broker_order: brokerOrder):
        result = self.broker_execution_stack_data.cancel_order_on_stack(broker_order)

        return result

    def check_order_is_cancelled(self, broker_order: brokerOrder) -> bool:
        result = self.broker_execution_stack_data.check_order_is_cancelled(broker_order)

        return result

    def check_order_is_cancelled_given_control_object(
        self, broker_order_with_controls: orderWithControls
    ) -> bool:
        result = self.broker_execution_stack_data.check_order_is_cancelled_given_control_object(
            broker_order_with_controls
        )

        return result

    def check_order_can_be_modified_given_control_object(
        self, broker_order_with_controls: orderWithControls
    ) -> bool:
        return self.broker_execution_stack_data.check_order_can_be_modified_given_control_object(
            broker_order_with_controls
        )

    def modify_limit_price_given_control_object(
        self, broker_order_with_controls: orderWithControls, new_limit_price: float
    ) -> orderWithControls:
        new_order_with_controls = (
            self.broker_execution_stack_data.modify_limit_price_given_control_object(
                broker_order_with_controls, new_limit_price
            )
        )
        return new_order_with_controls

    def get_total_capital_value_in_base_currency(self) -> float:
        currency_data = dataCurrency(self.data)
        account_id = self.get_broker_account()
        values_across_accounts = (
            self.broker_capital_data.get_account_value_across_currency(account_id)
        )

        # This assumes that each account only reports either in one currency or
        # for each currency, i.e. no double counting
        total_account_value_in_base_currency = (
            currency_data.total_of_list_of_currency_values_in_base(
                values_across_accounts
            )
        )

        return total_account_value_in_base_currency
