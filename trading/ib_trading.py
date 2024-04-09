from sysinit.futures import repocsv_spread_costs
from sysdata.data_blob import dataBlob
from sysinit.futures import seed_price_data_from_IB
from syscore.constants import arg_not_supplied
from sysinit.futures.rollcalendars_from_arcticprices_to_csv import build_and_write_roll_calendar
from sysproduction.data.prices import get_valid_instrument_code_from_user
from sysinit.futures.multipleprices_from_db_prices_and_csv_calendars_to_db import (
    process_multiple_prices_all_instruments,
)
from sysinit.futures.multiple_and_adjusted_from_csv_to_arctic import init_arctic_with_csv_futures_contract_prices
from sysproduction.update_sampled_contracts import update_sampled_contracts
from sysinit.futures.rollcalendars_from_providedcsv_prices import \
    generate_roll_calendars_from_provided_multiple_csv_prices
from sysinit.futures.adjustedprices_from_db_multiple_to_db import process_adjusted_prices_all_instruments

if __name__ == "__main__":

    # Instrument configuration and spread costs
    # ps wuax | grep mongo
    # mongod --dbpath ~/data/mongodb/
    # print("Transfer instrument spread costs config from csv to mongo DB")
    # modify flags as required
    # repocsv_spread_costs.copy_spread_costs_from_csv_to_mongo(dataBlob())

    ####################################################################################################################

    # Getting data from the broker (Interactive brokers)
    # print("Get initial price data from IB")
    # instrument_code = input("Instrument code? <return to abort> ")
    # if instrument_code == "":
    #     exit()
    #
    # seed_price_data_from_IB.seed_price_data_from_IB(instrument_code)

    ####################################################################################################################

    # Creating and storing multiple prices
    # Generate a roll calendar from actual futures prices
    # input("Will overwrite existing roll calendar are you sure?! CTL-C to abort")
    # instrument_code = get_valid_instrument_code_from_user(source="single")
    # # MODIFY DATAPATH IF REQUIRED
    # build_and_write_roll_calendar(instrument_code, output_datapath=arg_not_supplied)
    # build_and_write_roll_calendar(instrument_code, output_datapath="/Users/eonum/data")

    ####################################################################################################################

    # input("Will overwrite existing prices are you sure?! CTL-C to abort")
    # # change if you want to write elsewhere
    # csv_multiple_data_path = arg_not_supplied
    #
    # # only change if you have written the files elsewhere
    # csv_roll_data_path = arg_not_supplied
    #
    # # modify flags as required
    # process_multiple_prices_all_instruments(
    #     csv_multiple_data_path=csv_multiple_data_path,
    #     csv_roll_data_path=csv_roll_data_path,
    # )

    ####################################################################################################################

    # Writing multiple prices from .csv to database
    # init_arctic_with_csv_futures_contract_prices(
    #     adj_price_datapath=arg_not_supplied, multiple_price_datapath=arg_not_supplied
    # )

    ####################################################################################################################

    # Updating shipped multiple prices
    # Updating sampled contracts (Daily)
    # update_sampled_contracts()

    ####################################################################################################################

    # Updating historical prices (Daily)
    # from sysproduction.update_historical_prices import update_historical_prices
    # update_historical_prices()

    ####################################################################################################################

    # Interactive manual check historical prices
    # from sysproduction.interactive_manual_check_historical_prices import interactive_manual_check_historical_prices
    #
    # interactive_manual_check_historical_prices()

    ####################################################################################################################

    # Generate roll calendars from provided multiple csv prices
    # generate_roll_calendars_from_provided_multiple_csv_prices()

    ####################################################################################################################

    # Updating adjusted prices
    # import os
    #
    # roll_calendars_from_arctic = os.path.join('/Users/eonum/PycharmProjects/pysystemtrade/data', 'futures',
    #                                           'roll_calendars_from_arctic')
    # if not os.path.exists(roll_calendars_from_arctic):
    #     os.makedirs(roll_calendars_from_arctic)
    #
    # multiple_prices_from_arctic = os.path.join('/Users/eonum/PycharmProjects/pysystemtrade/data', 'futures',
    #                                            'multiple_from_arctic')
    # if not os.path.exists(multiple_prices_from_arctic):
    #     os.makedirs(multiple_prices_from_arctic)
    #
    # spliced_multiple_prices = os.path.join('/Users/eonum/PycharmProjects/pysystemtrade/data', 'futures',
    #                                        'multiple_prices_csv_spliced')
    # if not os.path.exists(spliced_multiple_prices):
    #     os.makedirs(spliced_multiple_prices)
    #
    # from sysinit.futures.rollcalendars_from_arcticprices_to_csv import build_and_write_roll_calendar
    #
    # instrument_code = input("Instrument code? <return to abort> ")
    # if instrument_code == "":
    #     exit()
    # build_and_write_roll_calendar(instrument_code,
    #                               output_datapath=roll_calendars_from_arctic)

    ####################################################################################################################

    # Updating multiple prices

    # import os
    #
    # from sysinit.futures.multipleprices_from_db_prices_and_csv_calendars_to_db import \
    #     process_multiple_prices_single_instrument
    #
    # process_multiple_prices_single_instrument(instrument_code,
    #                                           csv_multiple_data_path=multiple_prices_from_arctic, ADD_TO_DB=True,
    #                                           csv_roll_data_path=roll_calendars_from_arctic, ADD_TO_CSV=True)

    ####################################################################################################################

    # Splicing multiple prices

    # import os
    #
    # supplied_file = os.path.join('/Users/eonum/PycharmProjects/pysystemtrade/data', 'futures', 'multiple_prices_csv',
    #                              instrument_code + '.csv')  # repo data
    # generated_file = os.path.join(multiple_prices_from_arctic, instrument_code + '.csv')
    #
    # import pandas as pd
    #
    # supplied = pd.read_csv(supplied_file, index_col=0, parse_dates=True)
    # generated = pd.read_csv(generated_file, index_col=0, parse_dates=True)
    #
    # # get final datetime of the supplied multiple_prices for this instrument
    # last_supplied = supplied.index[-1]
    #
    # print(f"last datetime of supplied prices {last_supplied}, first datetime of updated prices is {generated.index[0]}")
    #
    # # assuming the latter is later than the former, truncate the generated data:
    # generated = generated.loc[last_supplied:]
    #
    # # if first datetime in generated is the same as last datetime in repo, skip that row
    # first_generated = generated.index[0]
    # if first_generated == last_supplied:
    #     generated = generated.iloc[1:]
    #
    # # check we're using the same price and forward contracts (i.e. no rolls missing, which there shouldn't be if there is date overlap)
    # assert (supplied.iloc[-1].PRICE_CONTRACT == generated.loc[last_supplied:].iloc[0].PRICE_CONTRACT)
    # assert (supplied.iloc[-1].FORWARD_CONTRACT == generated.loc[last_supplied:].iloc[0].FORWARD_CONTRACT)
    # # nb we don't assert that the CARRY_CONTRACT is the same for supplied and generated, as some of the rolls implicit in the supplied multiple_prices don't match the pattern in the rollconfig.csv

    ####################################################################################################################

    # Writing spliced multiple prices to csv

    # spliced = pd.concat([supplied, generated])
    # spliced.to_csv(os.path.join(spliced_multiple_prices, instrument_code + '.csv'))
    #
    # from sysinit.futures.multiple_and_adjusted_from_csv_to_arctic import init_arctic_with_csv_prices_for_code
    #
    # init_arctic_with_csv_prices_for_code(instrument_code, multiple_price_datapath=spliced_multiple_prices)

    ####################################################################################################################

    # Updating adjusted prices

    # input("Will overwrite existing prices are you sure?! CTL-C to abort")
    # # modify flags and datapath as required
    # process_adjusted_prices_all_instruments(
    #     csv_adj_data_path=arg_not_supplied, ADD_TO_DB=True, ADD_TO_CSV=True
    # )

    ####################################################################################################################

    # Stitching multiple prices

    # from sysobjects.adjusted_prices import futuresAdjustedPrices
    # from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
    #
    # # assuming we have some multiple prices
    # arctic_multiple_prices = arcticFuturesMultiplePricesData()
    #
    # instrument_code = input("Instrument code? <return to abort> ")
    # if instrument_code == "":
    #     exit()
    # multiple_prices = arctic_multiple_prices.get_multiple_prices(instrument_code=instrument_code)
    #
    # adjusted_prices = futuresAdjustedPrices.stitch_multiple_prices(multiple_prices)

    ####################################################################################################################

    # from sysinit.futures.spotfx_from_csvAndInvestingDotCom_to_db import spotfx_from_csv_and_investing_dot_com
    #
    # spotfx_from_csv_and_investing_dot_com()

    # from sysdata.csv.csv_spot_fx import *
    #
    # data = csvFxPricesData()
    # data.get_fx_prices("GBPUSD")