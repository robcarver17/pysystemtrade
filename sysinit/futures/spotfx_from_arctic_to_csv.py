"""
Get FX prices from arctic and write to csv

WARNING WILL OVERWRITE EXISTING!
"""
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.csv.csv_spot_fx import csvFxPricesData

if __name__ == "__main__":
    arctic_fx_prices = arcticFxPricesData()
    csv_fx_prices = csvFxPricesData()

    list_of_ccy_codes = csv_fx_prices.get_list_of_fxcodes()

    for currency_code in list_of_ccy_codes:
        fx_prices = arctic_fx_prices.get_fx_prices(currency_code)
        print(fx_prices)

        csv_fx_prices.add_fx_prices(
            currency_code, fx_prices, ignore_duplication=True)
