"""
Populate a mongo DB collection with roll data from a csv
"""

from sysdata.mongodb.mongo_roll_data import mongoRollParametersData
from sysinit.futures.csv_data_readers.rolldata_from_csv import initCsvFuturesRollData

data_out = mongoRollParametersData()
data_in = initCsvFuturesRollData()

instrument_list = data_in.get_list_of_instruments()

for instrument_code in instrument_list:
    instrument_object = data_in.get_roll_parameters(instrument_code)

    data_out.delete_roll_parameters(instrument_code, are_you_sure=True)
    data_out.add_roll_parameters(instrument_object, instrument_code)

    # check
    instrument_added = data_out.get_roll_parameters(instrument_code)
    print("Added %s: %s to %s" % (instrument_code, instrument_added, data_out))
