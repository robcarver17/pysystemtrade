"""
Populate a mongo DB collection with instrument data from the instrument data in csv

"""
from syscore.genutils import new_removing_existing
from syscore.interactive.input import true_if_answer_is_yes
from sysdata.mongodb.mongo_futures_instruments import mongoFuturesInstrumentData
from sysdata.csv.csv_instrument_data import csvFuturesInstrumentData
from sysdata.data_blob import dataBlob
from sysproduction.data.prices import diagPrices


def copy_instrument_config_from_csv_to_mongo(data: dataBlob):
    data_out = mongoFuturesInstrumentData(data.mongo_db)
    data_in = csvFuturesInstrumentData()

    print("Transferring from %s to %s" % (str(data_in), str(data_out)))

    new_instrument_list = data_in.get_list_of_instruments()
    existing_instrument_list = data_out.get_list_of_instruments()

    changes_made = new_removing_existing(
        original_list=existing_instrument_list, new_list=new_instrument_list
    )

    new_instruments = changes_made.new
    deleted_instruments = changes_made.removing
    modified_instruments = changes_made.existing

    process_new_instruments(
        data_in=data_in, data_out=data_out, new_instruments=new_instruments
    )

    process_deleted_instruments(
        data_out=data_out, deleted_instruments=deleted_instruments
    )

    process_modified_instruments(
        data_in=data_in, data_out=data_out, modified_instruments=modified_instruments
    )


def process_new_instruments(data_in, data_out, new_instruments):

    if len(new_instruments) == 0:
        return None

    print("New instruments %s " % str(new_instruments))
    check_on_add = true_if_answer_is_yes(
        "Check when adding new instruments? (say no if doing in bulk)"
    )

    for instrument_code in new_instruments:
        instrument_object = data_in.get_instrument_data(instrument_code)
        if check_on_add:
            okay_to_add = true_if_answer_is_yes(
                "Add %s to database?" % str(instrument_object)
            )
            if not okay_to_add:
                continue

        data_out.add_instrument_data(instrument_object)

        # check
        instrument_added = data_out.get_instrument_data(instrument_code)
        print("Added %s to %s" % (instrument_added.instrument_code, data_out))


def process_modified_instruments(data_in, data_out, modified_instruments):

    actually_modified_instruments = []
    for instrument_code in modified_instruments:
        instrument_object = data_in.get_instrument_data(instrument_code)
        existing_instrument_object = data_out.get_instrument_data(instrument_code)
        if existing_instrument_object == instrument_object:
            # no change don't bother
            continue
        actually_modified_instruments.append(instrument_code)

    if len(actually_modified_instruments) == 0:
        return None

    print(
        "Existing instruments which may be updated %s"
        % str(actually_modified_instruments)
    )
    check_on_modify = true_if_answer_is_yes(
        "Check when modifying instruments? (probably should be yes except for bulk modify)"
    )

    diag_prices = diagPrices()
    instruments_with_prices = diag_prices.get_list_of_instruments_in_multiple_prices()

    for instrument_code in actually_modified_instruments:

        instrument_object = data_in.get_instrument_data(instrument_code)
        existing_instrument_object = data_out.get_instrument_data(instrument_code)
        has_prices = instrument_code in instruments_with_prices
        if has_prices:
            print(
                "%s has price data. Probably OK to change slippage but be careful about changing currency or pointsize"
                % instrument_code
            )

        if check_on_modify:
            okay_to_modify = true_if_answer_is_yes(
                "Okay to replace \n%s with \n%s?"
                % (str(existing_instrument_object), str(instrument_object))
            )
            if not okay_to_modify:
                continue

        data_out.delete_instrument_data(instrument_code, are_you_sure=True)
        data_out.add_instrument_data(instrument_object)

        # check
        instrument_added = data_out.get_instrument_data(instrument_code)
        print("Added %s to %s" % (instrument_added.instrument_code, data_out))


def process_deleted_instruments(data_out, deleted_instruments):

    if len(deleted_instruments) == 0:
        return None

    print("Deleted instruments which will be removed %s" % str(deleted_instruments))
    check_on_delete = true_if_answer_is_yes("Check when deleting instruments?")

    diag_prices = diagPrices()
    instruments_with_prices = diag_prices.get_list_of_instruments_in_multiple_prices()

    for instrument_code in deleted_instruments:
        has_prices = instrument_code in instruments_with_prices
        if has_prices:
            print(
                "%s has price data. ARE YOU REALLY SURE ABOUT THIS?" % instrument_code
            )

        if check_on_delete or has_prices:
            okay_to_delete = true_if_answer_is_yes(
                "Okay to delete %s?" % instrument_code
            )
            if not okay_to_delete:
                continue

        data_out.delete_instrument_data(instrument_code, are_you_sure=True)


if __name__ == "__main__":
    print("Transfer instrument config from csv to mongo DB")
    # modify flags as required
    copy_instrument_config_from_csv_to_mongo(dataBlob())
