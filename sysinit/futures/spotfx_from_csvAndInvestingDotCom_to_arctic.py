"""
Get FX prices from investing.com files, and from csv, merge and write to Arctic and/or optionally overwrite csv files
"""
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.csv.csv_spot_fx import csvFxPricesData
import pandas as pd

ADD_TO_ARCTIC = True
ADD_TO_CSV = True

# You may need to change this!
# There must be ONLY fx prices here, with filenames "GBPUSD.csv" etc
INVESTING_DATA_PATH = "data.other_sources.investing_dot_com.spotfx"

if __name__ == "__main__":
    # You can adapt this for different providers by changing these parameters
    investingDotCom_csv_fx_prices = csvFxPricesData(
        datapath=INVESTING_DATA_PATH,
        price_column="Price",
        date_column="Date",
        date_format="%b %d, %Y",
    )
    if ADD_TO_ARCTIC:
        arctic_fx_prices = arcticFxPricesData()
    my_csv_fx_prices = csvFxPricesData()

    list_of_ccy_codes = investingDotCom_csv_fx_prices.get_list_of_fxcodes()

    for currency_code in list_of_ccy_codes:

        print(currency_code)

        fx_prices_investingDotCom = investingDotCom_csv_fx_prices.get_fx_prices(
            currency_code)
        fx_prices_my_csv = my_csv_fx_prices.get_fx_prices(currency_code)
        print(
            "%d rows for my csv files, %d rows for investing.com"
            % (len(fx_prices_my_csv), len(fx_prices_investingDotCom))
        )
        # Merge;
        last_date_in_my_csv = fx_prices_my_csv.index[-1]
        fx_prices_investingDotCom = fx_prices_investingDotCom[last_date_in_my_csv:]
        fx_prices = pd.concat([fx_prices_my_csv, fx_prices_investingDotCom])
        fx_prices = fx_prices.loc[~fx_prices.index.duplicated(keep="first")]

        print("%d rows to write for %s" % (len(fx_prices), currency_code))

        if ADD_TO_CSV:
            my_csv_fx_prices.add_fx_prices(
                currency_code, fx_prices, ignore_duplication=True
            )

        if ADD_TO_ARCTIC:
            arctic_fx_prices.add_fx_prices(
                currency_code, fx_prices, ignore_duplication=True
            )
