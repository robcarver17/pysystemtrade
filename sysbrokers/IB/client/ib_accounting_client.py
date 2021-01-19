import datetime
from sysbrokers.IB.client.ib_client import ibClient, STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY
from sysobjects.spot_fx_prices import currencyValue

class ibAccountingClient(ibClient):

    def broker_get_account_value_across_currency_across_accounts(
        self
    ) -> list:
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

    def get_liquidation_value_for_currency_across_accounts(self, currency: str) -> float:
        liquidiation_values_across_accounts_dict = (
            self.get_net_liquidation_value_across_accounts()
        )
        list_of_account_ids = liquidiation_values_across_accounts_dict.keys()
        values_for_currency = [
            liquidiation_values_across_accounts_dict[account_id].get(currency, 0.0)
            for account_id in list_of_account_ids
        ]

        return sum(values_for_currency)

    def get_list_of_currencies_for_liquidation_values(self) -> list:
        liquidiation_values_across_accounts_dict = (
            self.get_net_liquidation_value_across_accounts()
        )
        currencies = [
            list(account_dict.keys())
            for account_dict in liquidiation_values_across_accounts_dict.values()
        ]
        currencies = sum(currencies, [])  # flatten

        return list(set(currencies))

    def get_net_liquidation_value_across_accounts(self) -> dict:
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

    def get_liquidation_values_for_single_account(self, account_id: str) -> dict:
        # returns a dict, with currencies as keys
        account_summary_dict = self.ib_get_account_summary()
        return account_summary_dict[account_id]["NetLiquidation"]


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

