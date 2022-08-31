#!/usr/bin/env python
"""
Get FX prices from csv repo files and write to arctic

WARNING WILL OVERWRITE EXISTING!
"""
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.csv.csv_spot_fx import csvFxPricesData

if __name__ == "__main__":
    input("Will overwrite existing prices are you sure?! CTL-C to abort")

    arctic_fx_prices = arcticFxPricesData()
    csv_fx_prices = csvFxPricesData()

    currency_code = input("Currency code? <return for ALL currencies> ")
    if currency_code == "":
        list_of_ccy_codes = csv_fx_prices.get_list_of_fxcodes()
    else:
        list_of_ccy_codes = [currency_code]

    for currency_code in list_of_ccy_codes:
        fx_prices = csv_fx_prices.get_fx_prices(currency_code)
        print(fx_prices)

        arctic_fx_prices.add_fx_prices(
            currency_code, fx_prices, ignore_duplication=True
        )
