"""
Populate a mongo DB collection with instrument data from a csv
"""

from sysdata.csv.csv_instrument_data import csvFuturesInstrumentData
from sysdata.mongodb.mongo_futures_instruments import mongoFuturesInstrumentData

INSTRUMENT_CONFIG_PATH = "data.futures.csvconfig"

data_out = mongoFuturesInstrumentData()
data_in = csvFuturesInstrumentData(datapath=INSTRUMENT_CONFIG_PATH)
print(data_in)
instrument_list = data_in.get_list_of_instruments()

if __name__ == "__main__":
    input("Will overwrite existing data are you sure?! CTL-C to abort")
    # modify flags as required
    for instrument_code in instrument_list:
        instrument_object = data_in.get_instrument_data(instrument_code)
        data_out.delete_instrument_data(instrument_code, are_you_sure=True)
        data_out.add_instrument_data(instrument_object)

        # check
        instrument_added = data_out.get_instrument_data(instrument_code)
        print("Added %s to %s" % (instrument_added.instrument_code, data_out))
