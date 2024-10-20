import matplotlib
import pandas as pd
from matplotlib import pyplot as plt

from syscore.dateutils import adjust_timestamp_to_include_notional_close_and_time_offset
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.csv.csv_futures_contract_prices import csvFuturesContractPriceData, ConfigCsvFuturesPrices
from sysobjects.contracts import futuresContract
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysobjects.dict_of_futures_per_contract_prices import dictFuturesContractPrices


def process_barchart_data(instrument):
    config = ConfigCsvFuturesPrices(input_date_index_name="Time",
                                    input_date_format="%m/%d/%Y",
                                    input_skiprows=0, input_skipfooter=1,
                                    input_column_mapping=dict(OPEN='Open',
                                                              HIGH='High',
                                                              LOW='Low',
                                                              FINAL='Last',
                                                              VOLUME='Volume'
                                                              ))

    csv_futures_contract_prices = csvFuturesContractPriceData(
        datapath="/home/todd/Documents/Gibson Trading/Data/Bitcoin",
        config=config)

    all_barchart_data_original_ts = csv_futures_contract_prices.get_merged_prices_for_instrument(instrument)
    all_barchart_data = dict([(contractid, index_to_closing(data, csv_time_offset, original_close, actual_close))
                              for contractid, data in all_barchart_data_original_ts.items()])

    all_barchart_data = dictFuturesContractPrices(
        [(key, futuresContractPrices(x)) for key, x in all_barchart_data.items()])

    return all_barchart_data


def index_to_closing(data_object, time_offset, original_close, actual_close):
    """
    Allows us to mix daily and intraday prices and seperate if required

    If index is daily, mark to actual_close
    If index is original_close, mark to actual_close
    If index is intraday, add time_offset

     :return: data_object
    """
    new_index = []
    for index_entry in data_object.index:
        # Check for genuine daily data
        new_index_entry = adjust_timestamp_to_include_notional_close_and_time_offset(index_entry, actual_close,
                                                                                     original_close, time_offset)
        new_index.append(new_index_entry)

    new_data_object = pd.DataFrame(data_object.values, index=new_index, columns=data_object.columns)
    new_data_object = new_data_object.loc[~new_data_object.index.duplicated(keep='first')]

    return new_data_object


def write_barchart_data(instrument, barchart_prices, delete_first=False):
    artic_futures_price_data = arcticFuturesContractPriceData()
    # want a clean sheet
    if delete_first:
        artic_futures_price_data.delete_merged_prices_for_instrument_code(instrument, areyousure=True)

    list_of_contracts = barchart_prices.keys()
    for contractid in list_of_contracts:
        futures_contract = futuresContract(instrument, contractid)
        artic_futures_price_data.write_merged_prices_for_contract_object(futures_contract, barchart_prices[contractid])


# slightly weird this stuff, but basically to ensure we get onto UTC time
original_close = pd.DateOffset(hours=23, minutes=0, seconds=1)
csv_time_offset = pd.DateOffset(hours=6)
actual_close = pd.DateOffset(hours=0, minutes=0, seconds=0)
barchart_data = process_barchart_data("BITCOIN")
barchart_prices_final = barchart_data.final_prices()
barchart_prices_final_as_pd = pd.concat(barchart_prices_final, axis=1)

# Inspect prices
# barchart_prices_final_as_pd.plot()
# matplotlib.use('TkAgg')
# plt.show()

# Inspect % change
# perc=barchart_prices_final_as_pd.diff()/barchart_prices_final_as_pd.shift(1)
# perc.plot()
# matplotlib.use('TkAgg')
# plt.show()

# Write
write_barchart_data("BITCOIN", barchart_data, delete_first=True)
