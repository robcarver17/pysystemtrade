"""
Populate a mongo DB collection with instrument data from the instrument data in csv

"""

from sysdata.mongodb.mongo_futures_instruments import mongoFuturesInstrumentData
from sysdata.csv.csv_instrument_data import csvFuturesInstrumentData

if __name__ == "__main__":
    print("Transfer from csv to mongo DB")
    input("Will overwrite existing instrument config are you sure?! CTL-C to abort")
    # modify flags as required

    data_out = mongoFuturesInstrumentData()
    data_in = csvFuturesInstrumentData()
    print(data_in)
    instrument_list = data_in.get_list_of_instruments()
    existing_instrument_list = data_out.get_list_of_instruments()

    new_instruments = list(set(instrument_list).difference(set(existing_instrument_list)))
    deleted_instruments =  list(set(instrument_list).difference(set(existing_instrument_list)))
    modified_instruments =list(set(instrument_list).intersection(set(existing_instrument_list)))

    print("New instruments %s " % str(new_instruments))
    for instrument_code in new_instruments:
        instrument_object = data_in.get_instrument_data(instrument_code)
        data_out.add_instrument_data(instrument_object)

        # check
        instrument_added = data_out.get_instrument_data(instrument_code)
        print("Added %s to %s" % (instrument_added.instrument_code, data_out))

    print("Existing instruments which may be updated %s" % str(modified_instruments))
    for instrument_code in modified_instruments:
        instrument_object = data_in.get_instrument_data(instrument_code)
        data_out.delete_instrument_data(instrument_code, are_you_sure=True)
        data_out.add_instrument_data(instrument_object)

        # check
        instrument_added = data_out.get_instrument_data(instrument_code)
        print("Added %s to %s" % (instrument_added.instrument_code, data_out))

    print("Deleted instruments which will be removed %s" % str(deleted_instruments))
    for instrument_code in deleted_instruments:
        data_out.delete_instrument_data(instrument_code, are_you_sure=True)
