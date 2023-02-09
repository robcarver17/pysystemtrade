import datetime

from sysbrokers.IB.client.ib_client import (
    ibClient,
    STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY,
)

from syscore.constants import arg_not_supplied

from sysobjects.spot_fx_prices import currencyValue, listOfCurrencyValues


class ibAccountingClient(ibClient):
    def broker_get_account_value_across_currency(
        self, account_id: str = arg_not_supplied
    ) -> listOfCurrencyValues:

        list_of_values_per_currency = self._get_named_value_across_currency(
            named_value="NetLiquidation", account_id=account_id
        )

        return list_of_values_per_currency

    def broker_get_excess_liquidity_value_across_currency(
        self, account_id: str = arg_not_supplied
    ) -> listOfCurrencyValues:

        list_of_values_per_currency = self._get_named_value_across_currency(
            named_value="FullExcessLiquidity", account_id=account_id
        )

        return list_of_values_per_currency

    def _get_named_value_across_currency(
        self, named_value: str, account_id: str = arg_not_supplied
    ) -> listOfCurrencyValues:

        list_of_currencies = self._get_list_of_currencies_for_named_values(named_value)
        list_of_values_per_currency = list(
            [
                currencyValue(
                    currency,
                    self._get_named_value_for_currency_across_accounts(
                        currency, account_id=account_id, named_value=named_value
                    ),
                )
                for currency in list_of_currencies
            ]
        )

        list_of_values_per_currency = listOfCurrencyValues(list_of_values_per_currency)

        return list_of_values_per_currency

    def _get_named_value_for_currency_across_accounts(
        self,
        currency: str,
        named_value: str,
        account_id: str = arg_not_supplied,
    ) -> float:
        liquidiation_values_across_accounts_dict = (
            self._get_named_value_across_accounts(named_value)
        )
        if account_id is arg_not_supplied:
            list_of_account_ids = liquidiation_values_across_accounts_dict.keys()
        else:
            list_of_account_ids = [account_id]

        values_for_currency = [
            liquidiation_values_across_accounts_dict[account_id].get(currency, 0.0)
            for account_id in list_of_account_ids
        ]

        return sum(values_for_currency)

    def _get_list_of_currencies_for_named_values(self, named_value: str) -> list:
        liquidiation_values_across_accounts_dict = (
            self._get_named_value_across_accounts(named_value)
        )
        currencies = [
            list(account_dict.keys())
            for account_dict in liquidiation_values_across_accounts_dict.values()
        ]
        currencies = sum(currencies, [])  # flatten

        return list(set(currencies))

    def _get_named_value_across_accounts(self, named_value: str) -> dict:
        # returns a dict, accountid as keys, of dicts, currencies as keys
        account_summary_dict = self._ib_get_account_summary()
        accounts = account_summary_dict.keys()
        liquidiation_values_across_accounts_dict = dict(
            [
                (
                    account_id,
                    self._get_named_account_value_for_single_account(
                        account_id=account_id, named_value=named_value
                    ),
                )
                for account_id in accounts
            ]
        )

        return liquidiation_values_across_accounts_dict

    def _get_named_account_value_for_single_account(
        self, named_value: str, account_id: str
    ) -> dict:
        # returns a dict, with currencies as keys
        # eg FullExcessLiquidity, or NetLiquidation
        account_summary_dict = self._ib_get_account_summary()
        return account_summary_dict[account_id][named_value]

    def _ib_get_account_summary(self) -> dict:
        data_stale = self._is_ib_account_summary_cache_stale()
        if data_stale:
            self._ib_update_account_summary_cache()

        account_summary_data = self.account_summary_data

        return account_summary_data

    @property
    def account_summary_data(self) -> dict:
        return self._account_summary_data

    def _is_ib_account_summary_cache_stale(self) -> bool:
        elapsed_seconds = self._get_elapsed_seconds_since_last_cache_update()
        if elapsed_seconds > STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY:
            return True
        else:
            return False

    def _get_elapsed_seconds_since_last_cache_update(self) -> float:
        account_summary_data_update = getattr(
            self, "_account_summary_data_update", None
        )
        if account_summary_data_update is None:
            # force an update
            return STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY * 9999

        elapsed_seconds = (
            datetime.datetime.now() - account_summary_data_update
        ).total_seconds()

        return elapsed_seconds

    def _ib_update_account_summary_cache(self):
        account_summary_dict = self._ib_get_account_summary_from_broker()
        self._record_cache_update()
        self._account_summary_data = account_summary_dict

    def _record_cache_update(self):
        self._account_summary_data_update = datetime.datetime.now()

    def _ib_get_account_summary_from_broker(self) -> dict:

        account_summary_rawdata = self.ib.accountSummary()

        # Weird format let's clean it up
        account_summary_dict = clean_up_account_summary(account_summary_rawdata)

        return account_summary_dict


def clean_up_account_summary(account_summary_rawdata: list) -> dict:
    list_of_accounts = _unique_list_from_total(account_summary_rawdata, "account")
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


def _unique_list_from_total(account_summary_data: list, tag_name: str):
    list_of_items = [
        getattr(account_value, tag_name) for account_value in account_summary_data
    ]
    list_of_items = list(set(list_of_items))
    return list_of_items
