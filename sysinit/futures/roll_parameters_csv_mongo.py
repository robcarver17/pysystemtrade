"""
Populate a mongo DB collection with roll data from a csv
"""

from sysdata.mongodb.mongo_roll_data import mongoRollParametersData
from sysdata.csv.csv_roll_parameters import csvRollParametersData

if __name__ == "__main__":
    print("Transfer roll parameters from csv to mongo DB")
    print("*** NOT RECOMENDED FOR EXISTING INSTRUMENTS - USE sysinit/futures/safely_modify_roll_parameters.py instead")
    input("Will overwrite existing data are you sure?! CTL-C to abort")
    # modify flags as required

    data_out = mongoRollParametersData()
    data_in = csvRollParametersData()

    new_instrument_list = data_in.get_list_of_instruments()
    existing_instrument_list = data_out.get_list_of_instruments()

    new_instruments = list(set(new_instrument_list).difference(set(existing_instrument_list)))
    deleted_instruments =  list(set(new_instrument_list).difference(set(existing_instrument_list)))
    modified_instruments =list(set(new_instrument_list).intersection(set(existing_instrument_list)))

    print("New instruments %s " % str(new_instruments))
    for instrument_code in new_instruments:
        instrument_object = data_in.get_roll_parameters(instrument_code)
        data_out.add_roll_parameters(instrument_code, instrument_object)

        # check
        instrument_added = data_out.get_roll_parameters(instrument_code)
        print("Added %s: %s to %s" % (instrument_code, instrument_added, data_out))

    print("Existing instruments that might be modified %s " % str(modified_instruments))
    for instrument_code in modified_instruments:
        instrument_object = data_in.get_roll_parameters(instrument_code)

        data_out.delete_roll_parameters(instrument_code, are_you_sure=True)
        data_out.add_roll_parameters(instrument_code, instrument_object)

        # check
        instrument_added = data_out.get_roll_parameters(instrument_code)
        print("Added %s: %s to %s" % (instrument_code, instrument_added, data_out))

    print("Instruments to be deleted %s " % str(deleted_instruments))
    for instrument_code in deleted_instruments:
        data_out.delete_roll_parameters(instrument_code, are_you_sure=True)
