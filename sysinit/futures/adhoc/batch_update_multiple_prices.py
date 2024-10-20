from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysproduction.data.prices import diagPrices
from sysinit.futures.seed_price_data_from_IB import seed_price_data_from_IB
diag_prices = diagPrices()

if __name__ == "__main__":
    errored = []
    csv_multiple_prices = csvFuturesMultiplePricesData()
    instrument_list = csv_multiple_prices.get_list_of_instruments()
    for instrument_code in instrument_list:
        try:
            seed_price_data_from_IB(instrument_code)
        except Exception as e:
            print(f"Error seeding price data for {instrument_code}: {e}")
            errored.append(instrument_code)
            
    print(f"Errored on {errored}")