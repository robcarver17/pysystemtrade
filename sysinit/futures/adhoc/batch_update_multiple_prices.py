from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysproduction.data.prices import diagPrices
from sysinit.futures.seed_price_data_from_IB import seed_price_data_from_IB
import argparse
diag_prices = diagPrices()

from sysinit.futures.seed_price_data_from_IB import seed_price_data_from_IB
from sysdata.data_blob import dataBlob
from sysproduction.data.prices import get_list_of_instruments
import pandas as pd 
from sysinit.futures.rollcalendars_from_arcticprices_to_csv import build_and_write_roll_calendar  
from sysinit.futures.multipleprices_from_db_prices_and_csv_calendars_to_db import process_multiple_prices_single_instrument
from sysinit.futures.adjustedprices_from_db_multiple_to_db import process_adjusted_prices_single_instrument
from sysproduction.data.broker import dataBroker
from sysbrokers.IB.ib_futures_contract_price_data import (
    futuresContract,
)
from syscore.constants import arg_not_supplied
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData

from sysproduction.data.prices import diagPrices
from syscore.exceptions import missingData
from sysbrokers.IB.ib_futures_contract_price_data import (
    futuresContract,
)
from syscore.dateutils import DAILY_PRICE_FREQ, HOURLY_FREQ, Frequency
from sysdata.data_blob import dataBlob

from sysproduction.data.broker import dataBroker
from sysproduction.data.prices import updatePrices
from sysproduction.update_historical_prices import write_merged_prices_for_contract

from syscore.constants import arg_not_supplied
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysobjects.roll_calendars import rollCalendar
from sysdata.csv.csv_roll_calendars import csvRollCalendarData
from sysdata.data_blob import dataBlob
import os
diag_prices = diagPrices()


def seed_price_data_for_contract(data: dataBlob, contract_object: futuresContract):
    log_attrs = {**contract_object.log_attributes(), "method": "temp"}

    list_of_frequencies = [HOURLY_FREQ, DAILY_PRICE_FREQ]
    for frequency in list_of_frequencies:
        data.log.debug("Getting data at frequency %s" % str(frequency), **log_attrs)
        seed_price_data_for_contract_at_frequency(
            data=data, contract_object=contract_object, frequency=frequency
        )

    data.log.debug("Writing merged data for %s" % str(contract_object), **log_attrs)
    write_merged_prices_for_contract(
        data, contract_object=contract_object, list_of_frequencies=list_of_frequencies
    )


def seed_price_data_for_contract_at_frequency(
    data: dataBlob, contract_object: futuresContract, frequency: Frequency
):
    data_broker = dataBroker(data)
    update_prices = updatePrices(data)
    log_attrs = {**contract_object.log_attributes(), "method": "temp"}

    try:
        prices = (
            data_broker.get_prices_at_frequency_for_potentially_expired_contract_object(
                contract_object, frequency=frequency
            )
        )
    except missingData:
        data.log.warning(
            "Error getting data for %s" % str(contract_object),
            **log_attrs,
        )
        return None

    data.log.debug(
        "Got %d lines of prices for %s" % (len(prices), str(contract_object)),
        **log_attrs,
    )

    if len(prices) == 0:
        data.log.warning(
            "No price data for %s" % str(contract_object),
            **log_attrs,
        )
    else:
        update_prices.overwrite_prices_at_frequency_for_contract(
            contract_object=contract_object, frequency=frequency, new_prices=prices
        )

def run_seed_price(instrument):
    try:
        seed_price_data_from_IB(instrument)
        return True
    except Exception as e:
        print(e)
        return False

def create_roll_calendar(instrument, pysys_data_dir):
    try:
        build_and_write_roll_calendar(instrument, output_datapath=os.path.join(pysys_data_dir, "futures/roll_calendars_csv/"),check_before_writing=False)
        return True
    except Exception as e:
        print(e)
        return False


def run_multiple_prices(instrument, csv_multiple_data_path, csv_roll_data_path):
    try:
        process_multiple_prices_single_instrument(
            instrument,
            csv_multiple_data_path=csv_multiple_data_path,
            csv_roll_data_path=csv_roll_data_path,
            ADD_TO_DB=True,
            ADD_TO_CSV=True,
        )
        return True
    except Exception as e:
        print(e)
        return False

def _get_data_inputs(csv_adj_data_path):
    db_multiple_prices = diag_prices.db_futures_multiple_prices_data
    db_adjusted_prices = diag_prices.db_futures_adjusted_prices_data
    csv_adjusted_prices = csvFuturesAdjustedPricesData(csv_adj_data_path)
    return db_multiple_prices, db_adjusted_prices, csv_adjusted_prices


def run_adjusted_prices(instrument):
    db_multiple_prices, _notused, _alsonotused = _get_data_inputs(arg_not_supplied)
    instrument_list = db_multiple_prices.get_list_of_instruments()
    try:
        process_adjusted_prices_single_instrument(
            instrument,
            csv_adj_data_path=arg_not_supplied,
            ADD_TO_DB=True,
            ADD_TO_CSV=True,
        )
        return True
    except Exception as e:
        print(e)
        return False
    

def generate_roll_calendars_from_provided_multiple_csv_prices(instrument_code,
    output_datapath=arg_not_supplied, 
):
    if output_datapath is arg_not_supplied:
        print("USING DEFAULT DATAPATH WILL OVERWRITE PROVIDED DATA in /data/futures/")
    else:
        print("Writing to %s" % output_datapath)
    csv_roll_calendars = csvRollCalendarData(datapath=output_datapath)
    sim_futures_data = csvFuturesSimData()


    multiple_prices = sim_futures_data.get_multiple_prices(instrument_code)
    roll_calendar = rollCalendar.back_out_from_multiple_prices(multiple_prices)
    # We ignore duplicates since this is run regularly
    csv_roll_calendars.add_roll_calendar(
        instrument_code, roll_calendar, ignore_duplication=True
    )
       
def merge_multiple_prices(instrument_code, pysys_data_dir):
        
    df = pd.read_csv(os.path.join(pysys_data_dir, f'futures/multiple_prices_csv/{instrument_code}.csv'))
    df2 = pd.read_csv(os.path.join(pysys_data_dir,f'futures/multiple_prices_csv/{instrument_code}.csv'))

    # Merge the two dataframes on DATE_TIME
    df2 = df2.iloc[:-1]
    df = pd.concat([df, df2]).drop_duplicates().reset_index(drop=True).sort_values('DATETIME')  

    # BEGIN: Remove duplicated rows based on all columns
    df = df.drop_duplicates()
    df['PRICE'] = df['PRICE'].round(1)
    df['CARRY'] = df['CARRY'].round(1)
    df['FORWARD'] = df['FORWARD'].round(1)

    # END:
    df.to_csv(os.path.join(pysys_data_dir,f'futures/multiple_prices_csv/{instrument_code}.csv'), index=False)
    df.to_csv(os.path.join(pysys_data_dir,f'futures/multiple_prices_csv/{instrument_code}.csv'), index=False)

def init_arctic_with_csv_futures_contract_prices(instrument_code,
    multiple_price_datapath=arg_not_supplied, adj_price_datapath=arg_not_supplied
):
    csv_multiple_prices = csvFuturesMultiplePricesData(multiple_price_datapath)
    csv_adj_prices = csvFuturesAdjustedPricesData(adj_price_datapath)

    init_arctic_with_csv_prices_for_code(
        instrument_code,
        multiple_price_datapath=multiple_price_datapath,
        adj_price_datapath=adj_price_datapath,
    )

def init_arctic_with_csv_prices_for_code(
    instrument_code: str,
    multiple_price_datapath=arg_not_supplied,
    adj_price_datapath=arg_not_supplied,
):
    print(instrument_code)
    csv_mult_data = csvFuturesMultiplePricesData(multiple_price_datapath)
    db_mult_data = diag_prices.db_futures_multiple_prices_data

    mult_prices = csv_mult_data.get_multiple_prices(instrument_code)
    db_mult_data.add_multiple_prices(
        instrument_code, mult_prices, ignore_duplication=True
    )

    csv_adj_data = csvFuturesAdjustedPricesData(adj_price_datapath)
    db_adj_data = diag_prices.db_futures_adjusted_prices_data

    adj_prices = csv_adj_data.get_adjusted_prices(instrument_code)
    db_adj_data.add_adjusted_prices(
        instrument_code, adj_prices, ignore_duplication=True
    )
    
    print("Finishing init_arctic_with_csv_prices_for_code for %s" % instrument_code)
    
    
def download_all(instrument_list):
    errored = []
   
    for instrument_code in instrument_list:
        try:
            seed_price_data_from_IB(instrument_code)
        except Exception as e:
            print(f"Error seeding price data for {instrument_code}: {e}")
            errored.append(instrument_code)
            
    # Remove errored instruments from the instrument list
    return [instrument for instrument in instrument_list if instrument not in errored]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch update multiple prices.")
    parser.add_argument('--upload', action='store_true', help='Upload the data after seeding prices')
    args = parser.parse_args()
    
    
    roll_calendars_from_db = os.path.join(os.sep, 'home', 'vcaldas', "aptrade", 'data', 'futures', 'roll_calendars_from_db')
    if not os.path.exists(roll_calendars_from_db):
        os.makedirs(roll_calendars_from_db)

    multiple_prices_from_db = os.path.join(os.sep,'home', 'vcaldas', "aptrade", 'data', 'futures', 'multiple_from_db')
    if not os.path.exists(multiple_prices_from_db):
        os.makedirs(multiple_prices_from_db)
    
    spliced_multiple_prices = os.path.join(os.sep, 'home', 'vcaldas', "aptrade", 'data', 'futures', 'multiple_prices_csv_spliced')
    if not os.path.exists(spliced_multiple_prices):
        os.makedirs(spliced_multiple_prices)
        
    pysys_data_dir = os.getenv('PYSYS_DATA_DIR')
    if pysys_data_dir:
        print(f"PYSYS_DATA_DIR is set to {pysys_data_dir}")
    else:
        print("PYSYS_DATA_DIR is not set")
    csv_multiple_data_path = os.path.join(pysys_data_dir, "futures/multiple_prices_csv")
    csv_roll_data_path =  os.path.join(pysys_data_dir, "futures/roll_calendars_csv")


    csv_multiple_prices = csvFuturesMultiplePricesData()
    
    instrument_list = csv_multiple_prices.get_list_of_instruments()

    errored = []
    for instrument_code in instrument_list:
        ## Check if the file exists
        if not os.path.exists(os.path.join("/home/vcaldas/aptrade/data/parquet/futures_adjusted_prices", instrument_code+'.parquet')):
            try:
                if args.upload:
                    print("Upload flag is set. Data will be uploaded after seeding prices.")
                    seed_price_data_from_IB(instrument_code)
                else:
                    print("Upload flag is not set. Data will not be uploaded.")
                # After donwloading the data, we need to create the roll calendar
                folder_path = "/home/vcaldas/aptrade/data/parquet/futures_contract_prices/"

                non_empty_dfs = []
                for file_name in os.listdir(folder_path):
                    if file_name.endswith(".parquet") and "instrument_code" in file_name:
                        file_path = os.path.join(folder_path, file_name)
                        df = pd.read_parquet(file_path)
                        if df.empty:
                            os.remove(file_path)    
                        
                print(f"{instrument_code}: Build and write roll callendars")
                build_and_write_roll_calendar(instrument_code, output_datapath=roll_calendars_from_db, check_before_writing=False)
                print(f"{instrument_code}: Proccess multiple prices")

                process_multiple_prices_single_instrument(instrument_code,
                                                        csv_multiple_data_path=multiple_prices_from_db,
                                                        csv_roll_data_path=roll_calendars_from_db,
                                                        ADD_TO_DB=False,
                                                        ADD_TO_CSV=True)
                
                
                # print(f"Processing {instrument_code}")
                # # # Updating Multiple Prices
                # run_multiple_prices(instrument_code, csv_multiple_data_path, csv_roll_data_path)
                # # merge_multiple_prices(instrument_code, pysys_data_dir)


                supplied_file = os.path.join(os.sep, 'home', 'vcaldas', "aptrade", 'data', 'futures', 'multiple_prices_csv',
                                            instrument_code + '.csv')  # repo data
                generated_file = os.path.join(multiple_prices_from_db, instrument_code + '.csv')

                supplied = pd.read_csv(supplied_file, index_col=0, parse_dates=True)
                generated = pd.read_csv(generated_file, index_col=0, parse_dates=True)


                # Merge the two dataframes on DATE_TIME
                last_supplied = supplied.index[-1]
                first_generated = generated.index[0]

                if first_generated == last_supplied:
                    generated = generated.iloc[1:]
                    
                # Remove overlapping rows based on datetime. Keep the ones generated
                overlap_start = max(last_supplied, first_generated)
                supplied = supplied[supplied.index < overlap_start]

                # check we're using the same price and forward contracts
                # (i.e. no rolls missing, which there shouldn't be if there is date overlap)
                # Note that this might cause errors because IB cannot go back that long.

                # df2 = df2.iloc[:-1]
                # df = pd.concat([df, df2]).drop_duplicates().reset_index(drop=True).sort_values('DATETIME')  

                spliced = pd.concat([supplied, generated]).sort_values('DATETIME')
                spliced = spliced[~spliced.index.duplicated(keep='first')]
                # Remove some annoying decimal places
                spliced['PRICE'] = spliced['PRICE'].round(2)
                spliced['CARRY'] = spliced['CARRY'].round(2)
                spliced['FORWARD'] = spliced['FORWARD'].round(2)
                
            
                # Count duplicated entries in the dataframe
                duplicate_count = spliced.index.duplicated().sum()
                if duplicate_count > 0:
                    print("Duplicated indexes:")
                    print(spliced[spliced.index.duplicated(keep=False)])
                # assert duplicate_count == 0, f"There are {duplicate_count} duplicated entries in the dataframe."
                print("Saving spliced dataframe at %s" % os.path.join(spliced_multiple_prices, instrument_code+'.csv'))
                spliced.to_csv(os.path.join(spliced_multiple_prices, instrument_code+'.csv'))


                # # # ## Then update the roll calendar from the multiple prices available
                generate_roll_calendars_from_provided_multiple_csv_prices(instrument_code, output_datapath=os.path.join(pysys_data_dir, "futures/roll_calendars_csv" ))

                # # # Create the file in parquet format
                init_arctic_with_csv_prices_for_code(instrument_code, multiple_price_datapath=spliced_multiple_prices)
                
                # # # # Get adjusted prices
                run_adjusted_prices(instrument_code)
            except Exception as e:
                print(e)
    
                errored.append(instrument_code)
                
    # Save the list of errored instruments to a text file
    errored_file_path = os.path.join(pysys_data_dir, "errored_instruments.txt")
    with open(errored_file_path, 'w') as f:
        for instrument in errored:
            f.write(f"{instrument}\n")
    print(f"List of errored instruments saved to {errored_file_path}")