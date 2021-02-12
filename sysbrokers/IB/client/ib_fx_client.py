import pandas as pd
from ib_insync import MarketOrder, Forex

from sysbrokers.IB.client.ib_price_client import ibPriceClient
from sysbrokers.IB.ib_contracts import ibcontractWithLegs
from sysbrokers.IB.ib_positions import extract_fx_balances_from_account_summary, resolveBS
from sysbrokers.IB.ib_translate_broker_order_objects import tradeWithContract
from syscore.objects import arg_not_supplied, missing_contract
from sysproduction.data.directories import missing_data


class ibFxClient(ibPriceClient):

    def broker_fx_balances(self) -> dict:
        account_summary = self.ib.accountSummary()
        fx_balance_dict = extract_fx_balances_from_account_summary(
            account_summary)

        return fx_balance_dict

    def broker_fx_market_order(
            self,
            trade: float,
            ccy1: str,
            account: str=arg_not_supplied,
            ccy2: str="USD") -> tradeWithContract:
        """
        Get some spot fx data

        :param ccy1: first currency in pair
        :param ccy2: second currency in pair
        :param qty:
        :return: broker order object
        """

        ibcontract = self.ib_spotfx_contract(ccy1, ccy2=ccy2)
        if ibcontract is missing_contract:
            return missing_contract

        ib_order = self._create_fx_market_order_for_submission(trade=trade, account=account)
        order_object = self.ib.placeOrder(ibcontract, ib_order)

        # for consistency with spread orders use this kind of object
        contract_object_to_return =ibcontractWithLegs(ibcontract)
        trade_with_contract = tradeWithContract(
            contract_object_to_return, order_object
        )

        return trade_with_contract

    def _create_fx_market_order_for_submission(self,
            trade: float,
            account: str=arg_not_supplied,
            ) -> MarketOrder:

        ib_BS_str, ib_qty = resolveBS(trade)
        ib_order = MarketOrder(ib_BS_str, ib_qty)
        if account != "":
            ib_order.account = account

        return ib_order


    def broker_get_daily_fx_data(self, ccy1, ccy2="USD", bar_freq="D") -> pd.Series:
        """
        Get some spot fx data

        :param ccy1: first currency in pair
        :param ccy2: second currency in pair
        :return: pd.Series
        """

        ccy_code = ccy1 + ccy2
        log = self.log.setup(currency_code=ccy_code)

        ibcontract = self.ib_spotfx_contract(ccy1, ccy2=ccy2)

        if ibcontract is missing_contract:
            log.warn("Can't find IB contract for %s%s" % (ccy1, ccy2))
            return missing_data

        # uses parent class ibClientPrices
        fx_data = self._get_generic_data_for_contract(
            ibcontract, log=log, bar_freq=bar_freq, whatToShow="MIDPOINT")

        return fx_data


    def ib_spotfx_contract(self, ccy1, ccy2="USD") -> Forex:

        ibcontract = Forex(ccy1 + ccy2)
        ibcontract = self.ib_resolve_unique_contract(ibcontract)

        return ibcontract