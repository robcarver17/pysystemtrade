from sysdata.quandl.quandl_futures import quandlFuturesConfiguration, quandlFuturesContractPriceData
from sysdata.futures.contracts import listOfFuturesContracts
from sysdata.futures.instruments import futuresInstrument
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData

import numpy as np
import pandas as pd

def get_roll_parameters_from_mongo(instrument_code):

    mongo_roll_parameters = mongoRollParametersData()

    roll_parameters = mongo_roll_parameters.get_roll_parameters(instrument_code)
    if roll_parameters.empty():
        raise Exception("Instrument %s missing from %s" % (instrument_code, mongo_roll_parameters))

    return roll_parameters


def get_first_contract_date_from_quandl(instrument_code):
    config = quandlFuturesConfiguration()
    return config.get_first_contract_date(instrument_code)


def create_list_of_contracts(instrument_code):
    instrument_object = futuresInstrument(instrument_code)
    print(instrument_code)
    roll_parameters = get_roll_parameters_from_mongo(instrument_code)
    first_contract_date = get_first_contract_date_from_quandl(instrument_code)

    list_of_contracts = listOfFuturesContracts.historical_price_contracts(instrument_object, roll_parameters,
                                                                      first_contract_date)

    return list_of_contracts


def atr(price_frame, smooth=20):
    """
    Average true range from a pandas data frame

    :param pd_row: A row from a pandas data frame with elements CLOSE, HIGH, OPEN, LOW
    :return: ATR
    """

    last_close = price_frame.shift(1).SETTLE

    atr = pd.concat([(price_frame.HIGH - price_frame.LOW).abs(),
                     (price_frame.HIGH - last_close).abs(), (price_frame.LOW - last_close).abs()], axis=1)

    atr = atr.max(axis=1)

    atr = atr.rolling(smooth).mean()

    return atr


def get_vol_atr_compare(list_of_contracts):
    quandl_prices_data = quandlFuturesContractPriceData()

    ratio_list = []
    for contract_object in list_of_contracts:

        price_frame = quandl_prices_data.get_prices_for_contract_object(contract_object)
        price_returns = price_frame.SETTLE.diff()
        std_series = price_returns.rolling(20).std()
        atr_series = atr(price_frame)

        ratio_series = std_series / atr_series
        avg_ratio = ratio_series.mean()

        print(avg_ratio)

        ratio_list.append(avg_ratio)

    print("Average ratio DAILY STD DEV /ATR = %.3f" % np.nanmean(ratio_list))

if __name__ == '__main__':
    instrument_code = "EDOLLAR"
    list_of_contracts = create_list_of_contracts(instrument_code)
    print(list_of_contracts)

    print("Generated %d contracts" % len(list_of_contracts))

    get_vol_atr_compare(list_of_contracts)