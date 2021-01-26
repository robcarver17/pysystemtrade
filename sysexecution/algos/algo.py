from copy import copy
from dataclasses import dataclass

from syscore.objects import missing_data, arg_not_supplied, missing_order, missing_contract

from sysdata.data_blob import dataBlob

from sysexecution.orders.base_orders import adjust_spread_order_single_benchmark
from sysexecution.orders.broker_orders import create_new_broker_order_from_contract_order, brokerOrderType, market_order_type, limit_order_type, brokerOrder
from sysexecution.tick_data import analyse_tick_data_frame, tickerObject, analysisTick
from sysexecution.price_quotes import quotePrice
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.trade_qty import tradeQuantity
from sysexecution.order_stacks.broker_order_stack import orderWithControls

from sysobjects.contracts import futuresContract

from sysproduction.data.broker import dataBroker

limit_price_from_input = "input"
limit_price_from_side_price = "side_price"
limit_price_from_offside_price = "offside_price"
sources_of_limit_price = [limit_price_from_offside_price, limit_price_from_side_price, limit_price_from_offside_price]


@dataclass
class benchmarkPriceCollection(object):
    side_price: float = None
    offside_price: float= None
    benchmark_side_prices: quotePrice= None
    benchmark_mid_prices: quotePrice= None

class Algo(object):
    def __init__(self, data: dataBlob,
                 contract_order: contractOrder):
        self._data = data
        self._contract_order = contract_order
        self._data_broker = dataBroker(data)

    @property
    def data(self):
        return self._data

    @property
    def data_broker(self):
        return self._data_broker

    @property
    def contract_order(self):
        return self._contract_order

    def submit_trade(self) -> orderWithControls:
        """

        :return: broker order with control  or missing_order
        """
        raise NotImplementedError

    def manage_trade(self, broker_order_with_controls: orderWithControls) -> orderWithControls:
        """

        :return: broker order with control
        """
        raise NotImplementedError


    def get_and_submit_broker_order_for_contract_order(
        self,
        contract_order: contractOrder,
        input_limit_price: float=None,
        order_type: brokerOrderType=market_order_type,
        limit_price_from: str = limit_price_from_input,
        ticker_object: tickerObject=None,
        broker_account: str = arg_not_supplied
    ):

        log = contract_order.log_with_attributes(self.data.log)
        broker = self.data_broker.get_broker_name()

        if broker_account is arg_not_supplied:
            broker_account = self.data_broker.get_broker_account()

        broker_clientid = self.data_broker.get_broker_clientid()

        if ticker_object is None:
            ticker_object = self.data_broker.get_ticker_object_for_order(contract_order)

        collected_prices = self.get_market_data_for_order_modifies_ticker_object(
            ticker_object, contract_order
        )
        if collected_prices is missing_data:
            # no data available, no can do
            return missing_order

        ## We want to preserve these otherwise there is a danger they will dynamically change
        collected_prices = copy(collected_prices)

        if order_type == limit_order_type:
            limit_price = self.set_limit_price(
                contract_order=contract_order,
                collected_prices=collected_prices,
                limit_price_from=limit_price_from,
                input_limit_price=input_limit_price,
            )
        elif order_type == market_order_type:
            limit_price = None
        else:
            error_msg = "Order type %s not valid for broker orders" % str (order_type)
            log.critical(error_msg)

            return missing_order

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

        placed_broker_order_with_controls = self.data_broker.submit_broker_order(
            broker_order)

        if placed_broker_order_with_controls is missing_order:
            log.warn("Order could not be submitted")
            return missing_order

        log = placed_broker_order_with_controls.order.log_with_attributes(log)
        log.msg("Submitted order to IB %s" %
                str(placed_broker_order_with_controls.order))

        placed_broker_order_with_controls.add_or_replace_ticker(ticker_object)

        return placed_broker_order_with_controls


    def get_market_data_for_order_modifies_ticker_object(self, ticker_object: tickerObject,
                                                         contract_order: contractOrder) -> benchmarkPriceCollection:
        # We use prices for a couple of reasons:
        # to provide a benchmark for execution purposes
        # (optionally) to set limit prices
        ##
        log = contract_order.log_with_attributes(self.data.log)

        # Get the first 'reference' tick
        reference_tick = (
            ticker_object.wait_for_valid_bid_and_ask_and_return_current_tick(
                wait_time_seconds=10
            )
        )

        tick_analysis = ticker_object.analyse_for_tick(reference_tick)

        if tick_analysis is missing_data:
            log.warn(
                "Can't get market data for %s so not trading with limit order %s" %
                (contract_order.instrument_code, str(contract_order)))
            return missing_data

        ticker_object.clear_and_add_reference_as_first_tick(reference_tick)

        # These prices will be used for limit price purposes
        # They are scalars
        side_price = tick_analysis.side_price
        offside_price = tick_analysis.offside_price
        mid_price = tick_analysis.mid_price

        """
        FIXME
        CODE THAT I THINK IS DEFUNCT
        if contract_order.calendar_spread_order:
            # For spread orders, we use the tick stream to get the limit price, and the historical ticks for the benchmark
            # This is because we benchmark on each individual contract price,
            # and the tick stream is just for the spread

            benchmarks = self.get_benchmark_prices_for_contract_order_by_leg(
                contract_order
            )
            if benchmarks is missing_data:
                log.warn(
                    "Can't get individual component market data for %s so not trading with order %s" %
                    (contract_order.instrument_code, str(contract_order)))
                return missing_data


            # We need to adjust these so they are consistent with the initial
            # spread (timing issues or something)
            benchmark_side_prices = adjust_spread_order_single_benchmark(
                contract_order, benchmarks.benchmark_side_prices, side_price
            )
            benchmark_mid_prices = adjust_spread_order_single_benchmark(
                contract_order, benchmarks.benchmark_mid_prices, mid_price
            )
        """

        benchmark_side_prices = quotePrice(side_price)
        benchmark_mid_prices = quotePrice(mid_price)

        collected_prices = benchmarkPriceCollection(
            side_price=side_price,
            offside_price=offside_price,
            benchmark_side_prices=benchmark_side_prices,
            benchmark_mid_prices=benchmark_mid_prices)

        return collected_prices

    def set_limit_price(
        self,
        contract_order: contractOrder,
        collected_prices: benchmarkPriceCollection,
        input_limit_price: float=None,
        limit_price_from: str=limit_price_from_input,
    ) -> float:

        assert limit_price_from in sources_of_limit_price

        if limit_price_from == limit_price_from_input:
            assert input_limit_price is not None
            limit_price = input_limit_price

        elif limit_price_from == limit_price_from_side_price:
            limit_price = collected_prices.side_price

        elif limit_price_from == limit_price_from_offside_price:
            limit_price = collected_prices.offside_price

        else:
            raise Exception("Limit price from %s not known" % limit_price_from)

        limit_price_rounded = self.round_limit_price_to_tick_size(contract_order, limit_price)

        return limit_price_rounded

    def round_limit_price_to_tick_size(self, contract_order: contractOrder, limit_price: float) -> float:
        contract = contract_order.futures_contract

        min_tick = self.data_broker.get_min_tick_size_for_contract(contract)
        if min_tick is missing_contract:
            log = contract_order.log_with_attributes(self.data.log)
            log.warn("Couldn't find min tick size for %s, not rounding limit price %f" % (str(contract),
                                                                                             limit_price))

            return limit_price

        rounded_limit_price = min_tick * round(limit_price / min_tick)

        return rounded_limit_price


    def get_benchmark_prices_for_contract_order_by_leg(self, contract_order: contractOrder)-> benchmarkPriceCollection:
        market_conditions = self.get_market_conditions_for_contract_order_by_leg(
            contract_order)
        if market_conditions is missing_data:
            return missing_data

        side_prices = quotePrice([x.side_price for x in market_conditions])
        mid_prices = quotePrice([x.mid_price for x in market_conditions])

        benchmark_price_collection = benchmarkPriceCollection(benchmark_side_prices=side_prices,
                                 benchmark_mid_prices=mid_prices)

        return benchmark_price_collection


    def get_market_conditions_for_contract_order_by_leg(self, contract_order: contractOrder) -> list:
        market_conditions = []
        list_of_individual_contracts = contract_order.futures_contract.as_list_of_individual_contracts()
        list_of_trades = contract_order.trade
        for contract, qty in zip(
            list_of_individual_contracts, list_of_trades
        ):

            market_conditions_this_contract = (
                self.data_broker.check_market_conditions_for_single_legged_contract_and_qty(contract, qty)
            )
            if market_conditions_this_contract is missing_data:
                return missing_data

            market_conditions.append(market_conditions_this_contract)

        return market_conditions



