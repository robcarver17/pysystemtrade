from syscore.constants import arg_not_supplied
from syscore.dateutils import MIXED_FREQ, HOURLY_FREQ, DAILY_PRICE_FREQ
from syscore.pandas.frequency import merge_data_with_different_freq
from sysdata.csv.csv_futures_contract_prices import csvFuturesContractPriceData
from sysobjects.contracts import futuresContract
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysproduction.data.prices import diagPrices

diag_prices = diagPrices()
db_prices = diag_prices.db_futures_contract_price_data


def init_db_with_split_freq_csv_prices(
    datapath: str,
    csv_config=arg_not_supplied,
    ignore_duplication: bool = True,  # if True, we overwrite existing prices
):
    csv_prices = csvFuturesContractPriceData(datapath)
    input(
        "WARNING THIS WILL ERASE ANY EXISTING DATABASE PRICES WITH DATA FROM %s ARE YOU SURE?! (CTRL-C TO STOP)"
        % csv_prices.datapath
    )

    instrument_codes = csv_prices.get_list_of_instrument_codes_with_merged_price_data()
    instrument_codes.sort()
    for instrument_code in instrument_codes:
        init_db_with_split_freq_csv_prices_for_code(
            instrument_code,
            datapath,
            csv_config=csv_config,
            ignore_duplication=ignore_duplication,
        )


def init_db_with_split_freq_csv_prices_for_code(
    instrument_code: str,
    datapath: str,
    csv_config=arg_not_supplied,
    ignore_duplication: bool = True,
):
    same_length = []
    too_short = []
    print(f"Importing split freq csv prices for {instrument_code}")
    csv_prices = csvFuturesContractPriceData(datapath, config=csv_config)

    print(f"Getting split freq .csv prices may take some time")
    hourly_dict = csv_prices.get_prices_at_frequency_for_instrument(
        instrument_code,
        frequency=HOURLY_FREQ,
    )
    daily_dict = csv_prices.get_prices_at_frequency_for_instrument(
        instrument_code,
        frequency=DAILY_PRICE_FREQ,
    )

    hourly_and_daily = sorted(hourly_dict.keys() & daily_dict.keys())
    daily_only = sorted(set(daily_dict.keys()) - set(hourly_dict.keys()))
    hourly_only = sorted(set(hourly_dict.keys()) - set(daily_dict.keys()))

    print(f"hourly_and_daily: {sorted(hourly_and_daily)}")
    print(f"daily_only: {sorted(daily_only)}")
    print(f"hourly_only: {sorted(hourly_only)}")

    print(f"Have hourly and daily .csv prices for: {str(hourly_and_daily)}")
    for contract_date_str in hourly_and_daily:
        print(f"Processing {contract_date_str}")

        contract = futuresContract(instrument_code, contract_date_str)
        print(f"Contract object is {str(contract)}")

        hourly = hourly_dict[contract_date_str]
        write_prices_for_contract_at_frequency(
            contract, hourly, HOURLY_FREQ, ignore_duplication=ignore_duplication
        )

        daily = daily_dict[contract_date_str]
        write_prices_for_contract_at_frequency(
            contract, daily, DAILY_PRICE_FREQ, ignore_duplication=ignore_duplication
        )

        merged = futuresContractPrices(merge_data_with_different_freq([hourly, daily]))
        write_prices_for_contract_at_frequency(
            contract, merged, MIXED_FREQ, ignore_duplication=ignore_duplication
        )

        if len(hourly) == len(daily):
            same_length.append(contract_date_str)

    print(f"Have daily only .csv prices for: {str(daily_only)}")
    for contract_date_str in daily_only:
        print(f"Processing {contract_date_str}")

        contract = futuresContract(instrument_code, contract_date_str)
        print(f"Contract object is {str(contract)}")

        daily = daily_dict[contract_date_str]
        write_prices_for_contract_at_frequency(
            contract, daily, DAILY_PRICE_FREQ, ignore_duplication=ignore_duplication
        )

        # if we already have hourly data in the db, get it and merge with daily
        if db_prices.has_price_data_for_contract_at_frequency(
            contract, frequency=HOURLY_FREQ
        ):
            hourly = db_prices.get_prices_at_frequency_for_contract_object(
                contract, frequency=HOURLY_FREQ
            )
            merged = futuresContractPrices(
                merge_data_with_different_freq([hourly, daily])
            )
        else:
            merged = daily
        write_prices_for_contract_at_frequency(
            contract, merged, MIXED_FREQ, ignore_duplication=ignore_duplication
        )

        if len(daily) < 65:
            too_short.append(contract_date_str)

    print(f"Have hourly only .csv prices for: {str(hourly_only)}")
    for contract_date_str in hourly_only:
        print(f"Processing {contract_date_str}")

        contract = futuresContract(instrument_code, contract_date_str)
        print(f"Contract object is {str(contract)}")

        hourly = hourly_dict[contract_date_str]
        write_prices_for_contract_at_frequency(
            contract, hourly, HOURLY_FREQ, ignore_duplication=ignore_duplication
        )

        # if we already have daily data in the db, get it and merge with hourly
        if db_prices.has_price_data_for_contract_at_frequency(
            contract, frequency=DAILY_PRICE_FREQ
        ):
            daily = db_prices.get_prices_at_frequency_for_contract_object(
                contract, frequency=DAILY_PRICE_FREQ
            )
            merged = futuresContractPrices(
                merge_data_with_different_freq([hourly, daily])
            )
        else:
            merged = hourly
        write_prices_for_contract_at_frequency(
            contract, merged, MIXED_FREQ, ignore_duplication=ignore_duplication
        )

    print(f"These contracts have the same length for daily and hourly: {same_length}")
    print(f"These daily contracts are short: {too_short}")


def write_prices_for_contract_at_frequency(
    contract, prices, frequency, ignore_duplication=False
):
    print(f"{frequency} .csv prices are \n{str(prices)}")
    print("Writing to db")
    db_prices.write_prices_at_frequency_for_contract_object(
        contract,
        prices,
        frequency=frequency,
        ignore_duplication=ignore_duplication,
    )
    print("Reading back prices from db to check")
    written_prices = db_prices.get_prices_at_frequency_for_contract_object(
        contract, frequency=frequency
    )
    print(f"Read back prices ({frequency}) are \n{str(written_prices)}")


if __name__ == "__main__":
    input("Will overwrite existing prices are you sure?! CTL-C to abort")
    # modify flags as required
    datapath = "*** NEED TO DEFINE A DATAPATH***"
    init_db_with_split_freq_csv_prices(datapath)
