"""
Get FX prices from investing.com files, and from csv, merge and write to Arctic and/or optionally overwrite csv files
"""
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.csv.csv_spot_fx import csvFxPricesData, ConfigCsvFXPrices
import pandas as pd


# You may need to change this!
# There must be ONLY fx prices here, with filenames "GBPUSD.csv" etc


investing_dot_com_config = ConfigCsvFXPrices(
    price_column="Close", date_column="Date Time", date_format="%Y-%m-%d"
)


def spotfx_from_csv_and_investing_dot_com(
    datapath, ADD_TO_ARCTIC=True, ADD_TO_CSV=True, ADD_EXTRA_DATA=True
):
    # You can adapt this for different providers by changing these parameters
    if ADD_EXTRA_DATA:
        investingDotCom_csv_fx_prices = csvFxPricesData(
            datapath=datapath, config=investing_dot_com_config
        )
    if ADD_TO_ARCTIC:
        arctic_fx_prices = arcticFxPricesData()
    my_csv_fx_prices_data = csvFxPricesData()

    list_of_ccy_codes = my_csv_fx_prices_data.get_list_of_fxcodes()

    for currency_code in list_of_ccy_codes:

        print(currency_code)

        fx_prices_my_csv = my_csv_fx_prices_data.get_fx_prices(currency_code)

        fx_prices = investingDotCom_csv_fx_prices.get_fx_prices(currency_code)

        if ADD_EXTRA_DATA:
            fx_prices_investingDotCom = investingDotCom_csv_fx_prices.get_fx_prices(
                currency_code
            )
            print(
                "%d rows for my csv files, %d rows for investing.com"
                % (len(fx_prices_my_csv), len(fx_prices_investingDotCom))
            )
            # Merge;
            last_date_in_my_csv = fx_prices_my_csv.index[-1]
            fx_prices_investingDotCom = fx_prices_investingDotCom[last_date_in_my_csv:]
            fx_prices = pd.concat([fx_prices_my_csv, fx_prices_investingDotCom])
            fx_prices = fx_prices.loc[~fx_prices.index.duplicated(keep="first")]
        else:
            fx_prices = fx_prices_my_csv

        print("%d rows to write for %s" % (len(fx_prices), currency_code))

        if ADD_TO_CSV:
            my_csv_fx_prices_data.add_fx_prices(
                currency_code, fx_prices, ignore_duplication=True
            )

        if ADD_TO_ARCTIC:
            arctic_fx_prices.add_fx_prices(
                currency_code, fx_prices, ignore_duplication=True
            )
