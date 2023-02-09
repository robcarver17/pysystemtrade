from syscore.constants import arg_not_supplied
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData


def init_arctic_with_csv_futures_contract_prices(
    multiple_price_datapath=arg_not_supplied, adj_price_datapath=arg_not_supplied
):
    csv_multiple_prices = csvFuturesMultiplePricesData(multiple_price_datapath)
    csv_adj_prices = csvFuturesAdjustedPricesData(adj_price_datapath)
    input(
        "WARNING THIS WILL ERASE ANY EXISTING ARCTIC PRICES WITH DATA FROM %s,%s ARE YOU SURE?! CTRL-C TO ABORT"
        % (csv_adj_prices.datapath, csv_multiple_prices.datapath)
    )

    instrument_codes = csv_multiple_prices.get_list_of_instruments()
    for instrument_code in instrument_codes:
        init_arctic_with_csv_prices_for_code(
            instrument_code,
            multiple_price_datapath=multiple_price_datapath,
            adj_price_datapath=adj_price_datapath,
        )


def init_arctic_with_csv_prices_for_code(
    instrument_code: str,
    multiple_price_datapath=arg_not_supplied,
    adj_price_datapath=arg_not_supplied,
):
    print(instrument_code)
    csv_mult_data = csvFuturesMultiplePricesData(multiple_price_datapath)
    arctic_mult_data = arcticFuturesMultiplePricesData()

    mult_prices = csv_mult_data.get_multiple_prices(instrument_code)
    arctic_mult_data.add_multiple_prices(
        instrument_code, mult_prices, ignore_duplication=True
    )

    csv_adj_data = csvFuturesAdjustedPricesData(adj_price_datapath)
    arctic_adj_data = arcticFuturesAdjustedPricesData()

    adj_prices = csv_adj_data.get_adjusted_prices(instrument_code)
    arctic_adj_data.add_adjusted_prices(
        instrument_code, adj_prices, ignore_duplication=True
    )


if __name__ == "__main__":
    ## modify datapaths if required
    init_arctic_with_csv_futures_contract_prices(
        adj_price_datapath=arg_not_supplied, multiple_price_datapath=arg_not_supplied
    )
