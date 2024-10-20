import os
import pandas as pd

from sysinit.futures.multiple_and_adjusted_from_csv_to_arctic import init_arctic_with_csv_prices_for_code
from sysinit.futures.multipleprices_from_db_prices_and_csv_calendars_to_db import \
    process_multiple_prices_single_instrument
from sysinit.futures.rollcalendars_from_arcticprices_to_csv import build_and_write_roll_calendar
from sysproduction.data.prices import get_valid_instrument_code_from_user

roll_calendars_from_db = os.path.join(os.sep, 'home', 'vcaldas', "aptrade", 'data', 'futures', 'roll_calendars_from_db')
if not os.path.exists(roll_calendars_from_db):
    os.makedirs(roll_calendars_from_db)

multiple_prices_from_db = os.path.join(os.sep,'home', 'vcaldas', "aptrade", 'data', 'futures', 'multiple_from_db')
if not os.path.exists(multiple_prices_from_db):
    os.makedirs(multiple_prices_from_db)

spliced_multiple_prices = os.path.join(os.sep, 'home', 'vcaldas', "aptrade", 'data', 'futures', 'multiple_prices_csv_spliced')
if not os.path.exists(spliced_multiple_prices):
    os.makedirs(spliced_multiple_prices)

instrument_code = get_valid_instrument_code_from_user(source="multiple")
build_and_write_roll_calendar(instrument_code, output_datapath=roll_calendars_from_db)
input("Review roll calendar, press Enter to continue")

process_multiple_prices_single_instrument(instrument_code,
                                          csv_multiple_data_path=multiple_prices_from_db,
                                          csv_roll_data_path=roll_calendars_from_db,
                                          ADD_TO_DB=False,
                                          ADD_TO_CSV=True)
input("Review multiple prices, press Enter to continue")

supplied_file = os.path.join(os.sep, 'home', 'todd', 'pysystemtrade', 'data', 'futures', 'multiple_prices_csv',
                             instrument_code + '.csv')  # repo data
generated_file = os.path.join(multiple_prices_from_db, instrument_code + '.csv')

supplied = pd.read_csv(supplied_file, index_col=0, parse_dates=True)
generated = pd.read_csv(generated_file, index_col=0, parse_dates=True)

# get final datetime of the supplied multiple_prices for this instrument
last_supplied = supplied.index[-1]

print(f"last datetime of supplied prices {last_supplied}, first datetime of updated prices is {generated.index[0]}")

# assuming the latter is later than the former, truncate the generated data:
generated = generated.loc[last_supplied:]

# if first datetime in generated is the same as last datetime in repo, skip that row
first_generated = generated.index[0]
if first_generated == last_supplied:
    generated = generated.iloc[1:]

# check we're using the same price and forward contracts
# (i.e. no rolls missing, which there shouldn't be if there is date overlap)
try:
    assert (supplied.iloc[-1].PRICE_CONTRACT == generated.loc[last_supplied:].iloc[0].PRICE_CONTRACT)
    assert (supplied.iloc[-1].FORWARD_CONTRACT == generated.loc[last_supplied:].iloc[0].FORWARD_CONTRACT)
except AssertionError as e:
    print(supplied)
    print(generated)
    raise e
# nb we don't assert that the CARRY_CONTRACT is the same for supplied and generated,
# as some rolls implicit in the supplied multiple_prices don't match the pattern in the rollconfig.csv

spliced = pd.concat([supplied, generated])
spliced.to_csv(os.path.join(spliced_multiple_prices, instrument_code+'.csv'))

init_arctic_with_csv_prices_for_code(instrument_code, multiple_price_datapath=spliced_multiple_prices)
