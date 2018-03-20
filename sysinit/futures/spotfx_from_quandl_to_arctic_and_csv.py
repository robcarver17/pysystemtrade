"""
Get FX prices from Quandl and write to Arctic
"""
from sysdata.quandl.quandl_spotfx_prices import quandlFxPricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.csv.csv_spot_fx import csvFxPricesData

# could get these from stdin
ADD_TO_ARCTIC = True
ADD_TO_CSV = False

if __name__ == '__main__':
    quandl_fx_prices = quandlFxPricesData()
    arctic_fx_prices = arcticFxPricesData()
    csv_fx_prices = csvFxPricesData()

    list_of_ccy_codes = quandl_fx_prices.get_list_of_fxcodes()

    for currency_code in list_of_ccy_codes:
        fx_prices = quandl_fx_prices.get_fx_prices(currency_code)
        print(fx_prices)

        if ADD_TO_CSV:
            csv_fx_prices.add_fx_prices(currency_code, fx_prices)

        if ADD_TO_ARCTIC:
            arctic_fx_prices.add_fx_prices(currency_code, fx_prices)