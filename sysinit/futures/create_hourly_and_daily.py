
from syscore.dateutils import DAILY_PRICE_FREQ, HOURLY_FREQ
from syscore.pdutils import get_intraday_df_at_frequency, closing_date_rows_in_pd_object
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData

def write_split_data_for_instrument(instrument_code):
    a = arcticFuturesContractPriceData()
    list_of_contracts = a.contracts_with_merged_price_data_for_instrument_code(instrument_code)
    for contract in list_of_contracts:
        print(contract)
        merged_data = a.get_merged_prices_for_contract_object(contract)
        if len(merged_data) == 0:
            continue
        daily_data = closing_date_rows_in_pd_object(merged_data)
        hourly_data = get_intraday_df_at_frequency(merged_data, frequency="H")
        if len(daily_data) > 0:
            a.write_prices_at_frequency_for_contract_object(contract,
                                                            futures_price_data=daily_data,
                                                            ignore_duplication=False,
                                                            frequency=DAILY_PRICE_FREQ)
        if len(hourly_data) > 0:
            a.write_prices_at_frequency_for_contract_object(contract,
                                                            futures_price_data=hourly_data,
                                                            ignore_duplication=False,
                                                            frequency=HOURLY_FREQ)


if __name__ == "__main__":
    input("This script will delete any existing hourly and daily data in arctic, and replace with hourly and data inferred from 'merged' (legacy) data. CTL-C to abort")

    a = arcticFuturesContractPriceData()
    instrument_list = a.get_list_of_instrument_codes_with_merged_price_data()
    for instrument_code in instrument_list:
        print(instrument_code)
        write_split_data_for_instrument(instrument_code)