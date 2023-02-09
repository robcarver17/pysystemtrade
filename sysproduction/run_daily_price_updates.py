from syscontrol.run_process import processToRun
from sysproduction.update_historical_prices import updateHistoricalPrices

from sysdata.data_blob import dataBlob


def run_daily_price_updates():
    process_name = "run_daily_prices_updates"
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = get_list_of_timer_functions_for_price_update()
    price_process = processToRun(process_name, data, list_of_timer_names_and_functions)
    price_process.run_process()


def get_list_of_timer_functions_for_price_update():
    data_historical = dataBlob(log_name="update_historical_prices")

    historical_update_object = updateHistoricalPrices(data_historical)

    list_of_timer_names_and_functions = [
        ("update_historical_prices", historical_update_object),
    ]

    return list_of_timer_names_and_functions


if __name__ == "__main__":
    run_daily_price_updates()
