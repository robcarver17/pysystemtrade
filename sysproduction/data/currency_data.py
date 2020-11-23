from syscore.objects import arg_not_supplied
from syscore.genutils import print_menu_of_values_and_get_response

from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysobjects.spot_fx_prices import currencyValue, fxPrices
from sysdata.private_config import get_private_then_default_key_value

from sysproduction.data.get_data import dataBlob


class currencyData(object):
    """
    Translate between currency values
    """

    def __init__(self, data: dataBlob=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(arcticFxPricesData)
        self.data = data

    def update_fx_prices(self, fx_code: str, new_fx_prices: fxPrices, check_for_spike: bool=True):
        return self.data.db_fx_prices.update_fx_prices(
            fx_code, new_fx_prices, check_for_spike=check_for_spike
        )

    def total_of_list_of_currency_values_in_base(
            self, list_of_currency_values: list) -> float:
        value_in_base = [
            self.currency_value_in_base(currency_value)
            for currency_value in list_of_currency_values
        ]

        return sum(value_in_base)

    def currency_value_in_base(self, currency_value: currencyValue) -> float:
        value = currency_value.value
        fx_rate = self.get_last_fx_rate_to_base(currency_value.currency)
        base_value = value * fx_rate

        return base_value

    def get_last_fx_rate_to_base(self, currency: str) -> float:
        """

        :param currency: eg GBP
        :return: eg fx rate for GBPUSD if base was USD
        """
        base = self.get_base_currency()
        currency_pair = currency + base

        return self.get_last_fx_rate_for_pair(currency_pair)

    def get_base_currency(self) -> str:
        """

        :return: eg USD
        """
        return get_private_then_default_key_value("base_currency")

    def get_last_fx_rate_for_pair(self, currency_pair: str)-> float:
        """

        :param currency_pair: eg AUDUSD

        :return: float
        """
        fx_data = self.get_fx_prices(currency_pair)
        return fx_data.values[-1]

    def get_fx_prices_to_base(self, currency: str) -> fxPrices:
        """

        :param currency: eg GBP
        :return: eg fx rate for GBPUSD if base was USD
        """
        base = self.get_base_currency()
        currency_pair = currency + base

        return self.get_fx_prices(currency_pair)

    def get_fx_prices(self, fx_code: str) -> fxPrices:
        return self.data.db_fx_prices.get_fx_prices(fx_code)

    def get_list_of_fxcodes(self) -> list:
        return self.data.db_fx_prices.get_list_of_fxcodes()


def get_list_of_fxcodes(data=arg_not_supplied):
    if data is arg_not_supplied:
        data = dataBlob()
    c = currencyData(data)
    return c.get_list_of_fxcodes()


def get_valid_fx_code_from_user(data=arg_not_supplied):
    if data is arg_not_supplied:
        data = dataBlob()
    all_fx_codes = get_list_of_fxcodes(data)
    fx_code = print_menu_of_values_and_get_response(all_fx_codes)

    return fx_code
