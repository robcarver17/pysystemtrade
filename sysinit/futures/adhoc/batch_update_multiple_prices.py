from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysproduction.data.prices import diagPrices
from sysinit.futures.seed_price_data_from_IB import seed_price_data_from_IB
diag_prices = diagPrices()

MYLIST = ['BB3M', 'BRE', 'BRENT-LAST', 'BRENT_W', 'CHF_micro', 'CNH-onshore', 'COCOA', 'COCOA_LDN', 'COFFEE', 'DOW_mini', 'ETHANOL', 'ETHER-micro', 'ETHEREUM', 'EU-AUTO', 'EU-BANKS', 'EU-BASIC', 'EU-CHEM', 'EU-TECH', 'EU-UTILS', 'EUA', 'EURIBOR', 'EURIBOR-ICE', 'FED', 'GAS-LAST', 'GAS-PEN', 'GASOIL', 'GASOILINE', 'HEATOIL', 'LUMBER-new', 'MIB', 'MUMMY', 'MXP', 'NASDAQ', 'NASDAQ_micro', 'NICKEL_LME', 'NIKKEI', 'NIKKEI400', 'NOK', 'NZD', 'OAT', 'OATIES', 'OMX', 'PALLAD', 'PLAT', 'PLN', 'R1000', 'REDWHEAT', 'SONIA3', 'SOYBEAN', 'SOYBEAN_mini', 'SOYMEAL', 'SOYOIL', 'SP400', 'SP500', 'SP500_micro', 'SPI200', 'US-REALESTATE', 'US2', 'US3', 'US30', 'V2X', 'VIX_mini', 'VNKI']
if __name__ == "__main__":
    errored = []
    csv_multiple_prices = csvFuturesMultiplePricesData()
    instrument_list = csv_multiple_prices.get_list_of_instruments()
    for instrument_code in MYLIST:
        try:
            seed_price_data_from_IB(instrument_code)
        except Exception as e:
            print(f"Error seeding price data for {instrument_code}: {e}")
            errored.append(instrument_code)
            
    print(f"Errored on {errored}")