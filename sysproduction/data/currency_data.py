from syscore.constants import arg_not_supplied
from syscore.interactive.menus import print_menu_of_values_and_get_response

from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.fx.spotfx import fxPricesData
from sysdata.data_blob import dataBlob

from sysobjects.spot_fx_prices import currencyValue, fxPrices

from sysproduction.data.generic_production_data import productionDataLayerGeneric


class dataCurrency(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data: dataBlob) -> dataBlob:
        data.add_class_object(arcticFxPricesData)
        return data

    @property
    def db_fx_prices_data(self) -> fxPricesData:
        return self.data.db_fx_prices

    def update_fx_prices_and_return_rows_added(
        self, fx_code: str, new_fx_prices: fxPrices, check_for_spike: bool = True
    ) -> int:
        rows_added = self.db_fx_prices_data.update_fx_prices(
            fx_code, new_fx_prices, check_for_spike=check_for_spike
        )
        return rows_added

    def total_of_list_of_currency_values_in_base(
        self, list_of_currency_values: list
    ) -> float:
        value_in_base = [
            self.currency_value_in_base(currency_value)
            for currency_value in list_of_currency_values
        ]

        return sum(value_in_base)

    def currency_value_in_base(self, currency_value: currencyValue) -> float:
        value = currency_value.value
        if value == 0.0:
            return 0.0

        last_fx_rate = self.get_last_fx_rate_to_base(currency_value.currency)
        base_value = value * last_fx_rate

        return base_value

    def get_last_fx_rate_to_base(self, currency: str) -> float:
        """

        :param currency: eg GBP
        :return: eg fx rate for GBPUSD if base was USD
        """
        if currency == "":
            raise Exception("Empty currency field!")

        base = self.get_base_currency()
        if currency == base:
            return 1.0

        currency_pair = currency + base

        last_fx_rate = self.get_last_fx_rate_for_pair(currency_pair)
        return last_fx_rate

    def get_base_currency(self) -> str:
        """

        :return: eg USD
        """
        config = self.data.config
        return config.get_element_or_missing_data("base_currency")

    def get_last_fx_rate_for_pair(self, currency_pair: str) -> float:
        """

        :param currency_pair: eg AUDUSD

        :return: float
        """
        fx_data = self.get_fx_prices(currency_pair)
        last_fx_rate = fx_data.values[-1]
        return last_fx_rate

    def get_fx_prices_to_base(self, currency: str) -> fxPrices:
        """

        :param currency: eg GBP
        :return: eg fx rate for GBPUSD if base was USD
        """
        base = self.get_base_currency()
        currency_pair = currency + base

        prices = self.get_fx_prices(currency_pair)

        return prices

    def get_fx_prices(self, fx_code: str) -> fxPrices:
        prices = self.db_fx_prices_data.get_fx_prices(fx_code)
        return prices

    def get_list_of_fxcodes(self) -> list:
        list_of_codes = self.db_fx_prices_data.get_list_of_fxcodes()
        return list_of_codes


def get_list_of_fxcodes(data: dataBlob = arg_not_supplied) -> list:
    if data is arg_not_supplied:
        data = dataBlob()
    data_currency = dataCurrency(data)
    list_of_codes = data_currency.get_list_of_fxcodes()
    return list_of_codes


def get_valid_fx_code_from_user(
    data: dataBlob = arg_not_supplied, allow_none=False, none_str="None"
) -> str:
    if data is arg_not_supplied:
        data = dataBlob()
    all_fx_codes = get_list_of_fxcodes(data)
    if allow_none:
        fx_code = print_menu_of_values_and_get_response(
            all_fx_codes, default_str=none_str
        )
    else:
        fx_code = print_menu_of_values_and_get_response(all_fx_codes)

    return fx_code
