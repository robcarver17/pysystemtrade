from sysproduction.data.get_data import dataBlob
from syscore.pdutils import check_df_equals, check_ts_equals
from sysdata.private_config import get_private_then_default_key_value
import os

def backup_arctic_to_csv():
    data = get_data_and_create_csv_directories()
    backup_fx_to_csv(data)
    backup_futures_contract_prices_to_csv(data)
    backup_multiple_to_csv(data)
    backup_adj_to_csv(data)


def get_data_and_create_csv_directories():

    backup_dir = get_private_then_default_key_value('csv_backup_directory')

    class_paths = dict(csvFuturesContractPriceData="contract_prices",
                       csvFuturesAdjustedPricesData="adjusted_prices",
                       csvFuturesMultiplePricesData="multiple_prices",
                       csvFxPricesData="fx_prices")

    for class_name, path in class_paths.items():
        dir_name = "%s/%s/" % (backup_dir, path)
        class_paths[class_name] = dir_name
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)

    data = dataBlob(csv_data_paths=class_paths, keep_original_prefix=True)

    data.add_class_list("csvFuturesContractPriceData csvFuturesAdjustedPricesData csvFuturesMultiplePricesData csvFxPricesData")
    data.add_class_list("arcticFuturesContractPriceData arcticFuturesMultiplePricesData arcticFuturesAdjustedPricesData arcticFxPricesData")

    return data


## Write function for each thing we want to backup
## Think about how to check for duplicates (data frame equals?)

## Futures contract data
def backup_futures_contract_prices_to_csv(data):
    instrument_list = data.arctic_futures_contract_price.get_instruments_with_price_data()
    for instrument_code in instrument_list:
        contract_dates = data.arctic_futures_contract_price.\
            contract_dates_with_price_data_for_instrument_code(instrument_code)

        for contract_date in contract_dates:
            arctic_data = data.arctic_futures_contract_price.\
                get_prices_for_instrument_code_and_contract_date(instrument_code, contract_date)

            csv_data = data.csv_futures_contract_price.\
                get_prices_for_instrument_code_and_contract_date(instrument_code, contract_date)

            if check_df_equals(arctic_data, csv_data):
                ## No updated needed, move on
                print("No update needed")
            else:
                ## Write backup
                try:
                    data.csv_futures_contract_price.write_prices_for_instrument_code_and_contract_date(
                                                                                                       instrument_code,
                                                                                                       contract_date,
                                                                                                        arctic_data,
                                                                                                       ignore_duplication=True)
                    data.log.msg("Written backup .csv of prices for %s %s" % (instrument_code, contract_date))
                except:
                    data.log.warn("Problem writing .csv of prices for %s %s" % (instrument_code, contract_date))
# fx
def backup_fx_to_csv(data):
    fx_codes = data.arctic_fx_prices.get_list_of_fxcodes()
    for fx_code in fx_codes:
        arctic_data = data.arctic_fx_prices.get_fx_prices(fx_code)
        csv_data = data.csv_fx_prices.get_fx_prices(fx_code)
        if check_ts_equals(arctic_data, csv_data):
            print("No updated needed")
        else:
            ## Write backup
            try:
                data.csv_fx_prices.add_fx_prices(fx_code, arctic_data, ignore_duplication=True)
                data.log.msg("Written .csv backup for %s" % fx_code)
            except:
                data.log.warn("Problem writing .csv backup for %s" % fx_code)

def backup_multiple_to_csv(data):
    instrument_list = data.arctic_futures_multiple_prices.get_list_of_instruments()
    for instrument_code in instrument_list:
        arctic_data = data.arctic_futures_multiple_prices.get_multiple_prices(instrument_code)
        csv_data = data.csv_futures_multiple_prices.get_multiple_prices(instrument_code)

        if check_df_equals(arctic_data, csv_data):
            print("No update needed")
            pass
        else:
            try:
                data.csv_futures_multiple_prices.add_multiple_prices(instrument_code, arctic_data, ignore_duplication=True)
                data.log.msg("Written .csv backup multiple prices for %s" % instrument_code)
            except:
                data.log.warn("Problem writing .csv backup multiple prices for %s" % instrument_code)

def backup_adj_to_csv(data):
    instrument_list = data.arctic_futures_adjusted_prices.get_list_of_instruments()
    for instrument_code in instrument_list:
        arctic_data = data.arctic_futures_adjusted_prices.get_adjusted_prices(instrument_code)
        csv_data = data.csv_futures_adjusted_prices.get_adjusted_prices(instrument_code)

        if check_ts_equals(arctic_data, csv_data):
            print("No update needed")
            pass
        else:
            try:
                data.csv_futures_adjusted_prices.add_adjusted_prices(instrument_code, arctic_data, ignore_duplication=True)
                data.log.msg("Written .csv backup for adjusted prices %s" % instrument_code)
            except:
                data.log.warn("Problem writing .csv backup for adjusted prices %s" % instrument_code)