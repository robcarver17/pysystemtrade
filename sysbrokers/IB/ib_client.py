from dateutil.tz import tz
import datetime
import pandas as pd
from copy import copy

from ib_insync import Forex, util, ComboLeg
from ib_insync.order import MarketOrder, LimitOrder

from sysobjects.spot_fx_prices import currencyValue

from syscore.objects import missing_contract, arg_not_supplied, missing_order
from syscore.genutils import list_of_ints_with_highest_common_factor_positive_first
from syscore.dateutils import adjust_timestamp, strip_tz_info
from syslogdiag.log import logtoscreen

from sysbrokers.IB.ib_trading_hours import get_trading_hours
from sysbrokers.IB.ib_contracts import (
    resolve_multiple_expiries
)
from sysbrokers.IB.ib_instruments import ib_futures_instrument_just_symbol, futuresInstrumentWithIBConfigData, \
    ib_futures_instrument
from sysbrokers.IB.ib_positions import (
    from_ib_positions_to_dict,
    resolveBS,
    resolveBS_for_list,
    extract_fx_balances_from_account_summary,
)

_PACING_PERIOD_SECONDS = 10 * 60
_PACING_PERIOD_LIMIT = 60
PACING_INTERVAL_SECONDS = 1 + (_PACING_PERIOD_SECONDS / _PACING_PERIOD_LIMIT)

STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY = 600


class ibClient(object):
    """
    Client specific to interactive brokers

    Overrides the methods in the base class specifically for IB

    """

    def __init__(self, log=logtoscreen("ibClient")):

        self.log = log
        # means our first call won't be throttled for pacing
        self.last_historic_price_calltime = (
            datetime.datetime.now() -
            datetime.timedelta(
                seconds=_PACING_PERIOD_SECONDS))

    def refresh(self):
        self.ib.sleep(0.00001)

    def broker_fx_balances(self):
        account_summary = self.ib.accountSummary()
        fx_balance_dict = extract_fx_balances_from_account_summary(
            account_summary)

        return fx_balance_dict

    def broker_get_orders(self, account_id=arg_not_supplied):
        """
        Get all trades, orders and return them with the information needed

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

        return trades_in_broker_format_with_legs

    # Methods in parent class overriden here
    # These methods should abstract the broker completely

    def broker_submit_order(
        self,
        contract_object_with_ib_data,
        trade_list,
        account,
        order_type="market",
        limit_price=None,
    ):
        """

        :param ibcontract: contract_object_with_ib_data: contract where instrument has ib metadata
        :param trade: int
        :param account: str
        :param order_type: str, market or limit
        :param limit_price: None or float

        :return: brokers trade object

        """

        placed_broker_trade_object = self.ib_submit_order(
            contract_object_with_ib_data,
            trade_list,
            account=account,
            order_type=order_type,
            limit_price=limit_price,
        )

        return placed_broker_trade_object

    def broker_get_positions(self, account_id=arg_not_supplied):
        # Get all the positions
        # We return these as a dict of pd DataFrame
        # dict entries are asset classes, columns are IB symbol, contract ID,
        # contract expiry

        raw_positions = self.ib.positions()
        dict_of_positions = from_ib_positions_to_dict(
            raw_positions, account_id=account_id
        )

        return dict_of_positions

    def broker_get_futures_contract_list(
            self, futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData):

        specific_log = self.log.setup(
            instrument_code=futures_instrument_with_ib_data.instrument_code
        )

        ibcontract_pattern = ib_futures_instrument(
            futures_instrument_with_ib_data)
        contract_list = self.ib_get_contract_chain(
            ibcontract_pattern, log=specific_log)
        # if no contracts found will be empty

        # Extract expiry date strings from these
        contract_dates = [
            ibcontract.lastTradeDateOrContractMonth for ibcontract in contract_list]

        return contract_dates

    def broker_fx_market_order(
            self,
            trade,
            ccy1,
            account=arg_not_supplied,
            ccy2="USD"):
        """
        Get some spot fx data

        :param ccy1: first currency in pair
        :param ccy2: second currency in pair
        :param qty:
        :return: broker order object
        """

        ccy_code = ccy1 + ccy2
        specific_log = self.log.setup(currency_code=ccy_code)

        ibcontract = self.ib_spotfx_contract(ccy1, ccy2=ccy2, log=specific_log)
        if ibcontract is missing_contract:
            return missing_contract

        ib_BS_str, ib_qty = resolveBS(trade)
        ib_order = MarketOrder(ib_BS_str, ib_qty)
        if account != "":
            ib_order.account = account
        order_object = self.ib.placeOrder(ibcontract, ib_order)

        # for consistency with spread orders
        trade_with_contract = tradeWithContract(
            ibcontractWithLegs(ibcontract), order_object
        )

        return trade_with_contract

    def broker_get_daily_fx_data(self, ccy1, ccy2="USD", bar_freq="D"):
        """
        Get some spot fx data

        :param ccy1: first currency in pair
        :param ccy2: second currency in pair
        :return: pd.Series
        """

        ccy_code = ccy1 + ccy2
        specific_log = self.log.setup(currency_code=ccy_code)

        ibcontract = self.ib_spotfx_contract(ccy1, ccy2=ccy2, log=specific_log)
        # Register the contract to make logging and error handling cleaner
        # Two different ways of labelling
        self.add_contract_to_register(
            ibcontract, log_tags=dict(
                currency_code=ccy_code))

        if ibcontract is missing_contract:
            specific_log.warn("Can't find IB contract for %s%s" % (ccy1, ccy2))

        fx_data = self._get_generic_data_for_contract(
            ibcontract, log=specific_log, bar_freq=bar_freq, whatToShow="MIDPOINT")

        return fx_data

    def broker_get_historical_futures_data_for_contract(
        self, contract_object_with_ib_broker_config, bar_freq="D"
    ):
        """
        Get historical daily data

        :param contract_object_with_ib_broker_config: contract where instrument has ib metadata
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: futuresContractPriceData
        """

        specific_log = self.log.setup(
            instrument_code=contract_object_with_ib_broker_config.instrument_code,
            contract_date=contract_object_with_ib_broker_config.date_str,
        )

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_broker_config)
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't resolve IB contract %s"
                % str(contract_object_with_ib_broker_config)
            )

        price_data = self._get_generic_data_for_contract(
            ibcontract, log=specific_log, bar_freq=bar_freq, whatToShow="TRADES")

        return price_data

    def broker_get_account_value_across_currency_across_accounts(
        self
    ):
        list_of_currencies = self.get_list_of_currencies_for_liquidation_values()
        list_of_values_per_currency = list(
            [
                currencyValue(
                    currency,
                    self.get_liquidation_value_for_currency_across_accounts(currency),
                )
                for currency in list_of_currencies
            ]
        )

        return list_of_values_per_currency

    def get_liquidation_value_for_currency_across_accounts(self, currency):
        liquidiation_values_across_accounts_dict = (
            self.get_net_liquidation_value_across_accounts()
        )
        list_of_account_ids = liquidiation_values_across_accounts_dict.keys()
        values_for_currency = [
            liquidiation_values_across_accounts_dict[account_id].get(currency, 0.0)
            for account_id in list_of_account_ids
        ]

        return sum(values_for_currency)

    def get_list_of_currencies_for_liquidation_values(self):
        liquidiation_values_across_accounts_dict = (
            self.get_net_liquidation_value_across_accounts()
        )
        currencies = [
            list(account_dict.keys())
            for account_dict in liquidiation_values_across_accounts_dict.values()
        ]
        currencies = sum(currencies, [])  # flatten

        return list(set(currencies))

    def get_net_liquidation_value_across_accounts(self):
        # returns a dict, accountid as keys, of dicts, currencies as keys
        account_summary_dict = self.ib_get_account_summary()
        accounts = account_summary_dict.keys()
        liquidiation_values_across_accounts_dict = dict(
            [
                (account_id, self.get_liquidation_values_for_single_account(account_id))
                for account_id in accounts
            ]
        )

        return liquidiation_values_across_accounts_dict

    def get_liquidation_values_for_single_account(self, account_id):
        # returns a dict, with currencies as keys
        account_summary_dict = self.ib_get_account_summary()
        return account_summary_dict[account_id]["NetLiquidation"]

    def broker_get_contract_expiry_date(
            self, contract_object_with_ib_data) -> str:
        """
        Return the exact expiry date for a given contract

        :param contract_object_with_ib_data:  contract where instrument has ib metadata
        :return: YYYYMMDD str
        """
        specific_log = self.log.setup(
            instrument_code=contract_object_with_ib_data.instrument_code,
            contract_date=contract_object_with_ib_data.date_str,
        )

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_data)
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't get contract expiry from IB for %s"
                % str(contract_object_with_ib_data)
            )
            return missing_contract

        expiry_date = ibcontract.lastTradeDateOrContractMonth

        return expiry_date

    # IB specific methods
    # Called by parent class generics

    def add_contract_legs_to_order(self, raw_order_from_ib):
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

    def get_ticker_object(
        self, contract_object_with_ib_data, trade_list_for_multiple_legs=None
    ):

        specific_log = self.log.setup(
            instrument_code=contract_object_with_ib_data.instrument_code,
            contract_date=contract_object_with_ib_data.date_str,
        )

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't find matching IB contract for %s"
                % str(contract_object_with_ib_data)
            )
            return missing_contract

        self.ib.reqMktData(ibcontract, "", False, False)
        ticker = self.ib.ticker(ibcontract)

        ib_BS_str, ib_qty = resolveBS_for_list(trade_list_for_multiple_legs)

        ticker_with_bs = tickerWithBS(ticker, ib_BS_str)

        return ticker_with_bs

    def cancel_market_data_for_contract_object(
        self, contract_object_with_ib_data, trade_list_for_multiple_legs=None
    ):

        specific_log = self.log.setup(
            instrument_code=contract_object_with_ib_data.instrument_code,
            contract_date=contract_object_with_ib_data.date_str,
        )

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't find matching IB contract for %s"
                % str(contract_object_with_ib_data)
            )
            return missing_contract

        self.ib.cancelMktData(ibcontract)

    def ib_get_recent_bid_ask_tick_data(
        self,
        contract_object_with_ib_data,
        trade_list_for_multiple_legs=None,
        tick_count=200,
    ):
        """

        :param contract_object_with_ib_data:
        :return:
        """
        specific_log = self.log.setup(
            instrument_code=contract_object_with_ib_data.instrument_code,
            contract_date=contract_object_with_ib_data.date_str,
        )
        if contract_object_with_ib_data.is_spread_contract():
            raise Exception("Can't get historical data for combo")

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't find matching IB contract for %s"
                % str(contract_object_with_ib_data)
            )
            return missing_contract
        recent_ib_time = self.ib.reqCurrentTime() - datetime.timedelta(seconds=60)

        tick_data = self.ib.reqHistoricalTicks(
            ibcontract, recent_ib_time, "", tick_count, "BID_ASK", useRth=False
        )

        return tick_data

    def ib_get_trading_hours(self, contract_object_with_ib_data):
        ib_contract = self.ib_futures_contract(
            contract_object_with_ib_data, always_return_single_leg=True
        )
        if ib_contract is missing_contract:
            return missing_contract

        ib_contract_details = self.ib.reqContractDetails(ib_contract)[0]

        try:
            trading_hours = get_trading_hours(ib_contract_details)
        except Exception as e:
            self.log.warn("%s when getting trading hours!" % e)
            return missing_contract

        return trading_hours

    def ib_get_min_tick_size(self, contract_object_with_ib_data):
        ib_contract = self.ib_futures_contract(
            contract_object_with_ib_data, always_return_single_leg=True
        )
        if ib_contract is missing_contract:
            return missing_contract

        ib_contract_details = self.ib.reqContractDetails(ib_contract)[0]

        try:
            min_tick = ib_contract_details.minTick
        except Exception as e:
            self.log.warn("%s when getting min tick size from %s!" % (e, ib_contract_details))
            return missing_contract

        return min_tick


    def modify_limit_price_given_original_objects(
            self,
            original_order_object,
            original_contract_object_with_legs,
            new_limit_price):
        original_contract_object = original_contract_object_with_legs.ibcontract
        original_order_object.lmtPrice = new_limit_price

        new_trade_object = self.ib.placeOrder(
            original_contract_object, original_order_object
        )

        new_trade_with_contract = tradeWithContract(
            original_contract_object_with_legs, new_trade_object
        )

        return new_trade_with_contract

    def ib_cancel_order(self, original_order_object):
        new_trade_object = self.ib.cancelOrder(original_order_object)

        return new_trade_object

    def ib_submit_order(
        self,
        contract_object_with_ib_data,
        trade_list,
        account="",
        order_type="market",
        limit_price=None,
    ):

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

    def _get_generic_data_for_contract(
        self, ibcontract, log=None, bar_freq="D", whatToShow="TRADES"
    ):
        """
        Get historical daily data

        :param contract_object_with_ib_data: contract where instrument has ib metadata
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: futuresContractPriceData
        """
        if log is None:
            log = self.log

        if ibcontract is missing_contract:
            log.warn("Can't find price with valid IB contract")
            return pd.Series()

        try:
            barSizeSetting, durationStr = get_barsize_and_duration_from_frequency(
                bar_freq)
        except Exception as exception:
            log.warn(str(exception.args[0]))
            return pd.Series()

        price_data_raw = self.ib_get_historical_data(
            ibcontract,
            durationStr=durationStr,
            barSizeSetting=barSizeSetting,
            whatToShow=whatToShow,
            log=log,
        )

        if price_data_raw is None:
            log.warn("No price data from IB")
            return pd.Series()

        price_data_as_df = price_data_raw[[
            "open", "high", "low", "close", "volume"]]
        price_data_as_df.columns = ["OPEN", "HIGH", "LOW", "FINAL", "VOLUME"]
        date_index = [
            self.ib_timestamp_to_datetime(price_row)
            for price_row in price_data_raw["date"]
        ]
        price_data_as_df.index = date_index

        return price_data_as_df


    def ib_timestamp_to_datetime(self, timestamp_ib):
        """
        Turns IB timestamp into pd.datetime as plays better with arctic, converts IB time (UTC?) to local,
        and adjusts yyyymm to closing vector

        :param timestamp_str: datetime.datetime
        :return: pd.datetime
        """

        local_timestamp_ib = self.adjust_ib_time_to_local(timestamp_ib)
        timestamp = pd.to_datetime(local_timestamp_ib)

        adjusted_ts = adjust_timestamp(timestamp)

        return adjusted_ts

    def adjust_ib_time_to_local(self, timestamp_ib):

        if getattr(timestamp_ib, "tz_localize", None) is None:
            # daily, nothing to do
            return timestamp_ib

        timestamp_ib_with_tz = self.add_tz_to_ib_time(timestamp_ib)
        local_timestamp_ib_with_tz = timestamp_ib_with_tz.astimezone(
            tz.tzlocal())
        local_timestamp_ib = strip_tz_info(local_timestamp_ib_with_tz)

        return local_timestamp_ib

    def add_tz_to_ib_time(self, timestamp_ib):
        ib_tz = self.get_ib_timezone()
        timestamp_ib_with_tz = timestamp_ib.tz_localize(ib_tz)

        return timestamp_ib_with_tz

    def get_ib_timezone(self):
        # cache
        ib_tz = getattr(self, "_ib_time_zone", None)
        if ib_tz is None:
            ib_time = self.ib.reqCurrentTime()
            ib_tz = ib_time.timetz().tzinfo
            self._ib_time_zone = ib_tz

        return ib_tz

    def get_broker_time_local_tz(self):
        ib_time = self.ib.reqCurrentTime()
        local_ib_time_with_tz = ib_time.astimezone(tz.tzlocal())
        local_ib_time = strip_tz_info(local_ib_time_with_tz)

        return local_ib_time

    def ib_spotfx_contract(self, ccy1, ccy2="USD", log=arg_not_supplied):
        ibcontract = Forex(ccy1 + ccy2)

        ibcontract = self.ib_resolve_unique_contract(ibcontract)

        return ibcontract

    def ib_futures_contract(
        self,
        contract_object_with_ib_data,
        always_return_single_leg=False,
        trade_list_for_multiple_legs=None,
        return_leg_data=False,
    ):
        """
        Return a complete and unique IB contract that matches contract_object_with_ib_data
        Doesn't actually get the data from IB, tries to get from cache

        :param contract_object_with_ib_data: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """
        contract_object_to_use = copy(contract_object_with_ib_data)
        if always_return_single_leg and contract_object_to_use.is_spread_contract():
            contract_object_to_use = contract_object_to_use.new_contract_with_replaced_contract_date_object(contract_object_with_ib_data.date_str[0])

        if getattr(self, "_futures_contract_cache", None) is None:
            self._futures_contract_cache = {}

        if not contract_object_to_use.is_spread_contract():
            trade_list_suffix = ""
        else:
            # WANT TO TREAT EG -2,2 AND -4,4 AS THE SAME BUT DIFFERENT FROM
            # -2,1 OR -1,2,-1...
            trade_list_suffix = str(
                list_of_ints_with_highest_common_factor_positive_first(
                    trade_list_for_multiple_legs
                )
            )

        cache = self._futures_contract_cache
        key = contract_object_to_use.key + trade_list_suffix

        ibcontract_with_legs = cache.get(key, missing_contract)
        if ibcontract_with_legs is missing_contract:
            ibcontract_with_legs = self._get_ib_futures_contract(
                contract_object_to_use,
                trade_list_for_multiple_legs=trade_list_for_multiple_legs,
            )
            cache[key] = ibcontract_with_legs

        if return_leg_data:
            return ibcontract_with_legs
        else:
            return ibcontract_with_legs.ibcontract

    def _get_ib_futures_contract(
        self, contract_object_with_ib_data, trade_list_for_multiple_legs=None
    ):
        """
        Return a complete and unique IB contract that matches futures_contract_object
        This is expensive so not called directly, only by ib_futures_contract which does caching

        :param contract_object_with_ib_data: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """
        # Convert to IB world
        instrument_object_with_metadata = contract_object_with_ib_data.instrument

        if contract_object_with_ib_data.is_spread_contract():
            ibcontract, legs = self._get_spread_ib_futures_contract(
                instrument_object_with_metadata,
                contract_object_with_ib_data.contract_date,
                trade_list_for_multiple_legs=trade_list_for_multiple_legs,
            )
        else:
            ibcontract = self._get_vanilla_ib_futures_contract(
                instrument_object_with_metadata,
                contract_object_with_ib_data.contract_date,
            )
            legs = []

        ibcontract_with_legs = ibcontractWithLegs(ibcontract, legs=legs)

        return ibcontract_with_legs

    def _get_vanilla_ib_futures_contract(
        self, futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData, contract_date
    ):
        """
        Return a complete and unique IB contract that matches contract_object_with_ib_data
        This is expensive so not called directly, only by ib_futures_contract which does caching

        :param contract_object_with_ib_data: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """

        # The contract date might be 'yyyymm' or 'yyyymmdd'
        ibcontract = ib_futures_instrument(futures_instrument_with_ib_data)

        contract_day_passed = contract_date.is_day_defined()
        if contract_day_passed:
            # Already have the expiry
            pass
        else:
            # Don't have the expiry so lose the days at the end so it's just
            # 'YYYYMM'
            contract_date = str(contract_date.date_str)[:6]

        ibcontract.lastTradeDateOrContractMonth = contract_date

        # We allow multiple contracts in case we have 'yyyymm' and not
        # specified expiry date for VIX
        ibcontract_list = self.ib_get_contract_chain(ibcontract)

        if len(ibcontract_list) == 0:
            # No contracts found
            return missing_contract

        if len(ibcontract_list) == 1:
            # OK no hassle, only one contract no confusion
            resolved_contract = ibcontract_list[0]
        else:
            # It might be a contract with weekly expiries (probably VIX)
            # We need to find the right one
            try:
                resolved_contract = resolve_multiple_expiries(
                    ibcontract_list, futures_instrument_with_ib_data
                )
            except Exception as exception:
                self.log.warn(
                    "%s could not resolve contracts: %s"
                    % (str(futures_instrument_with_ib_data), exception.args[0])
                )

                return missing_contract

        return resolved_contract

    def _get_spread_ib_futures_contract(
        self,
        futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData,
        contract_date,
        trade_list_for_multiple_legs=[-1, 1],
    ):
        """
        Return a complete and unique IB contract that matches contract_object_with_ib_data
        This is expensive so not called directly, only by ib_futures_contract which does caching

        :param contract_object_with_ib_data: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """
        # Convert to IB world
        ibcontract = ib_futures_instrument(futures_instrument_with_ib_data)
        ibcontract.secType = "BAG"

        list_of_contract_dates = contract_date.list_of_single_contract_dates
        resolved_legs = [
            self._get_vanilla_ib_futures_contract(
                futures_instrument_with_ib_data, contract_date
            )
            for contract_date in list_of_contract_dates
        ]

        ratio_list = list_of_ints_with_highest_common_factor_positive_first(
            trade_list_for_multiple_legs
        )

        def _get_ib_combo_leg(ratio, resolved_leg):

            leg = ComboLeg()
            leg.conId = int(resolved_leg.conId)
            leg.exchange = str(resolved_leg.exchange)

            action, size = resolveBS(ratio)

            leg.ratio = int(size)
            leg.action = str(action)

            return leg

        ibcontract.comboLegs = [
            _get_ib_combo_leg(ratio, resolved_leg)
            for ratio, resolved_leg in zip(ratio_list, resolved_legs)
        ]

        return ibcontract, resolved_legs

    def ib_resolve_unique_contract(self, ibcontract_pattern, log=None):
        """
        Returns the 'resolved' IB contract based on a pattern. We expect a unique contract.

        :param ibcontract_pattern: ibContract
        :param log: log object
        :return: ibContract or missing_contract
        """
        if log is None:
            log = self.log

        contract_chain = self.ib_get_contract_chain(
            ibcontract_pattern, log=log)

        if len(contract_chain) > 1:
            log.warn(
                "Got multiple contracts for %s when only expected a single contract: Check contract date" %
                str(ibcontract_pattern))
            return missing_contract
        if len(contract_chain) == 0:
            log.warn("Failed to resolve contract %s" % str(ibcontract_pattern))
            return missing_contract

        resolved_contract = contract_chain[0]

        return resolved_contract

    def ib_get_contract_with_conId(self, symbol, conId):
        ibcontract_pattern = ib_futures_instrument_just_symbol(symbol)
        contract_chain = self.ib_get_contract_chain(ibcontract_pattern)
        conId_list = [contract.conId for contract in contract_chain]
        try:
            contract_idx = conId_list.index(conId)
        except ValueError:
            return missing_contract
        required_contract = contract_chain[contract_idx]

        return required_contract

    def ib_get_contract_chain(self, ibcontract_pattern, log=None):
        """
        Get all the IB contracts matching a pattern.

        :param ibcontract_pattern: ibContract which may not fully specify the contract
        :param log: log object
        :return: list of ibContracts
        """

        if log is None:
            log = self.log

        new_contract_details_list = self.ib.reqContractDetails(
            ibcontract_pattern)

        ibcontract_list = [
            contract_details.contract for contract_details in new_contract_details_list]

        return ibcontract_list

    # HISTORICAL DATA
    # Works for FX and futures
    def ib_get_historical_data(
        self,
        ibcontract,
        durationStr="1 Y",
        barSizeSetting="1 day",
        whatToShow="TRADES",
        log=None,
    ):
        """
        Returns historical prices for a contract, up to today
        ibcontract is a Contract
        :returns list of prices in 4 tuples: Open high low close volume
        """

        if log is None:
            log = self.log

        last_call = self.last_historic_price_calltime
        avoid_pacing_violation(last_call, log=log)

        bars = self.ib.reqHistoricalData(
            ibcontract,
            endDateTime="",
            durationStr=durationStr,
            barSizeSetting=barSizeSetting,
            whatToShow=whatToShow,
            useRTH=True,
            formatDate=1,
        )
        df = util.df(bars)

        self.last_historic_price_calltime = datetime.datetime.now()

        return df

    def ib_get_account_summary(self):
        data_stale = self._ib_get_account_summary_check_for_stale_cache()
        if data_stale:
            account_summary_data = self._ib_get_account_summary_if_cache_stale()
        else:
            account_summary_data = self._account_summary_data

        return account_summary_data

    def _ib_get_account_summary_check_for_stale_cache(self):
        account_summary_data_update = getattr(
            self, "_account_summary_data_update", None
        )
        account_summary_data = getattr(self, "_account_summary_data", None)

        if account_summary_data_update is None or account_summary_data is None:
            return True
        elapsed_seconds = (
            datetime.datetime.now() - account_summary_data_update
        ).total_seconds()

        if elapsed_seconds > STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY:
            return True
        else:
            return False

    def _ib_get_account_summary_if_cache_stale(self):

        account_summary_rawdata = self.ib.accountSummary()

        # Weird format let's clean it up
        account_summary_dict = clean_up_account_summary(
            account_summary_rawdata)

        self._account_summary_data = account_summary_dict
        self._account_summary_data_update = datetime.datetime.now()

        return account_summary_dict


def clean_up_account_summary(account_summary_rawdata):
    list_of_accounts = _unique_list_from_total(
        account_summary_rawdata, "account")
    list_of_tags = _unique_list_from_total(account_summary_rawdata, "tag")

    account_summary_dict = {}
    for account_id in list_of_accounts:
        account_summary_dict[account_id] = {}
        for tag in list_of_tags:
            account_summary_dict[account_id][tag] = {}

    for account_item in account_summary_rawdata:
        try:
            value = float(account_item.value)
        except ValueError:
            value = account_item.value
        account_summary_dict[account_item.account][account_item.tag][
            account_item.currency
        ] = value

    return account_summary_dict


def _unique_list_from_total(account_summary_data, tag_name):
    list_of_items = [getattr(account_value, tag_name)
                     for account_value in account_summary_data]
    list_of_items = list(set(list_of_items))
    return list_of_items


def get_barsize_and_duration_from_frequency(bar_freq):

    barsize_lookup = dict(
        [
            ("D", "1 day"),
            ("H", "1 hour"),
            ("15M", "15 mins"),
            ("5M", "5 mins"),
            ("M", "1 min"),
            ("10S", "10 secs"),
            ("S", "1 secs"),
        ]
    )
    duration_lookup = dict(
        [
            ("D", "1 Y"),
            ("H", "1 M"),
            ("15M", "1 W"),
            ("5M", "1 W"),
            ("M", "1 D"),
            ("10S", "14400 S"),
            ("S", "1800 S"),
        ]
    )
    try:
        assert bar_freq in barsize_lookup.keys() and bar_freq in duration_lookup.keys()
    except BaseException:
        raise Exception(
            "Barsize %s not recognised should be one of %s"
            % (bar_freq, str(barsize_lookup.keys()))
        )

    ib_barsize = barsize_lookup[bar_freq]
    ib_duration = duration_lookup[bar_freq]

    return ib_barsize, ib_duration


def avoid_pacing_violation(last_call_datetime, log=logtoscreen("")):
    printed_warning_already = False
    while (
        datetime.datetime.now() - last_call_datetime
    ).total_seconds() < PACING_INTERVAL_SECONDS:
        if not printed_warning_already:
            log.msg("Pausing %f seconds to avoid pacing violation" %
                    (datetime.datetime.now() - last_call_datetime).total_seconds())
            printed_warning_already = True
        pass


class ibcontractWithLegs(object):
    def __init__(self, ibcontract, legs=[]):
        self.ibcontract = ibcontract
        self.legs = legs

    def __repr__(self):
        return str(self.ibcontract) + " " + str(self.legs)


class tradeWithContract(object):
    def __init__(self, ibcontract_with_legs, trade_object):
        self.ibcontract_with_legs = ibcontract_with_legs
        self.trade = trade_object
        self.ib_instrument_code = trade_object.contract.symbol

    def __repr__(self):
        return str(self.trade) + " " + str(self.ibcontract_with_legs)


class tickerWithBS(object):
    def __init__(self, ticker, BorS):
        self.ticker = ticker
        self.BorS = BorS
