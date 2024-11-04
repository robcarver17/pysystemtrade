from syscore.constants import arg_not_supplied
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData

from sysproduction.data.prices import diagPrices

diag_prices = diagPrices()


def init_db_with_csv_futures_contract_prices(
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
        init_db_with_csv_prices_for_code(
            instrument_code,
            multiple_price_datapath=multiple_price_datapath,
            adj_price_datapath=adj_price_datapath,
        )


def init_db_with_csv_prices_for_code(
    instrument_code: str,
    multiple_price_datapath=arg_not_supplied,
    adj_price_datapath=arg_not_supplied,
):
    print(instrument_code)
    csv_mult_data = csvFuturesMultiplePricesData(multiple_price_datapath)
    db_mult_data = diag_prices.db_futures_multiple_prices_data

    mult_prices = csv_mult_data.get_multiple_prices(instrument_code)
    db_mult_data.add_multiple_prices(
        instrument_code, mult_prices, ignore_duplication=True
    )

    csv_adj_data = csvFuturesAdjustedPricesData(adj_price_datapath)
    db_adj_data = diag_prices.db_futures_adjusted_prices_data

    adj_prices = csv_adj_data.get_adjusted_prices(instrument_code)
    db_adj_data.add_adjusted_prices(
        instrument_code, adj_prices, ignore_duplication=True
    )


if __name__ == "__main__":
    ## modify datapaths if required
    init_db_with_csv_futures_contract_prices(
        adj_price_datapath=arg_not_supplied, multiple_price_datapath=arg_not_supplied
    )
