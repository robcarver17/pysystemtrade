from sysdata.csv.csv_futures_contract_prices import ConfigCsvFuturesPrices
from sysinit.futures.contract_prices_from_csv_to_arctic import init_arctic_with_csv_futures_contract_prices

barchart_symbol_map = { "AEX" : 'ae', "AUD" : "a6", "BOBL" : "hr", "BTP" : "ii", "CAC" : "mx", "BUND" : "gg",
                        "COPPER" : "hg", "CORN": "zc", "CRUDE_W" : "cl", "EDOLLAR" : "ge", "EUR" : "e6", "GAS_US" : "ng",
                        "GBP" : "b6", "GOLD" : "gc", "JPY" : "j6", "LEANHOG" : "he", "LIVECOW" : "le", 
                        "MXP" : "m6", "NASDAQ" : "nq", "NZD" : "n6", "OAT" : "fn", 
                        "PALLAD" : "pa", "SHATZ" : "hf", "PLAT" : "pl", "SOYBEAN" : "zs", 
                        "SP500" : "es", "US2" : "zt", "US5" : "zf", "US10" : "zn",
                        "US20" : "zb", "VIX" : "vi", "WHEAT" : "zw",
                        "V2X" : "dv", "US30" : "ud", "EUROSTX" : "fx", 
                        "GOLD_micro" : "gr", "NASDAQ_micro":"nm", "CRUDE_W_mini":"qm", "GAS_US_mini":"qg", "SP500_micro":"et",
                        "BITCOIN" : "ba", "COPPER-mini" : "qc" }

barchart_input_filename_format="%{BS}%{LETTER}%{YEAR2}_%{IGNORE}.csv"
# Scans files in target directory corresponding to format above. 
# For example 'plf19_daily_historical-data-07-04-2021.csv' translates to PLAT JAN 2019

example_1_barchart_input_filename_format="%{IGNORE}_%{BS}/%{BS}%{LETTER}%{YEAR2}_%{IGNORE}.csv"
# Scans files in target directory and its subdirectories corresponding to format abobe.
# For example file 'PLAT_pl/plf19_daily_historical-data-07-04-2021.csv' translates to PLAT JAN 2019 in directory 'PLAT_pl'
# Note that here the instrument code 'PLAT' in directory name is ignored and conversion from broker symbol to instrument code 
# is done with the symbol map above

example_2_barchart_input_filename_format="%{IC}_%{IGNORE}/%{IGNORE}%{LETTER}%{YEAR2}_%{IGNORE}.csv"
# Scans files in target directory and its subdirectories corresponding to format above. 
# For example file 'PLAT_pl/plf19_daily_historical-data-07-04-2021.csv' translates to PLAT JAN 2019 in directory 'PLAT_pl'
# Note that here the broker symbol instead is ignored and we extract the instrument code directly from the directory name

# Please see sysdata/csv/parametric_csv_database.py for the translation codes (e.g. %{BS})

# Unit multiplier: Because our saved contract price data from IB has for example JPY prices in USD/YEN but in Barchart (and other sources..) the units 
# are USD/ 100 YEN, so we need to multiply these prices accordingly.  
# If adding other instruments please check that prices match or add corresponding multiplier here
barchart_instrument_price_multiplier = { "JPY" : 0.01  }


barchart_csv_config = ConfigCsvFuturesPrices(input_date_index_name="Time",
                                input_skiprows=0, input_skipfooter=1,
                                input_date_format="%m/%d/%Y",
                                input_column_mapping=dict(OPEN='Open',
                                                          HIGH='High',
                                                          LOW='Low',
                                                          FINAL='Last',
                                                          VOLUME='Volume'),
                                input_filename_format = barchart_input_filename_format,
                                instrument_price_multiplier = barchart_instrument_price_multiplier,
                                append_default_daily_time = True,   # we add 23:00:00 because the time is missing from .csv files
                                broker_symbols = barchart_symbol_map )

def transfer_barchart_prices_to_arctic(datapath):
    init_arctic_with_csv_futures_contract_prices(datapath, csv_config= barchart_csv_config)

if __name__ == "__main__":
    input("Will overwrite existing prices are you sure?! CTL-C to abort")
    # modify flags as required
    datapath = "*** NEED TO DEFINE A DATAPATH ***"
    transfer_barchart_prices_to_arctic(datapath)
