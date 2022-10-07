"""
Populate a mongo DB collection with roll data from a csv
"""
import argparse
from syscore.genutils import new_removing_existing
from syscore.interactive import true_if_answer_is_yes
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData
from sysdata.csv.csv_roll_parameters import csvRollParametersData
from sysdata.data_blob import dataBlob
from sysproduction.data.prices import diagPrices

# modify flags as required


def copy_roll_parameters_from_csv_to_mongo(
    data: dataBlob, echo_difference=False, check_only=False
):
    data_out = mongoRollParametersData(data.mongo_db)
    data_in = csvRollParametersData()

    print("Transferring from %s to %s" % (str(data_in), str(data_out)))

    new_instrument_list = data_in.get_list_of_instruments()
    existing_instrument_list = data_out.get_list_of_instruments()

    changes_made = new_removing_existing(
        original_list=existing_instrument_list, new_list=new_instrument_list
    )

    new_instruments = changes_made.new
    deleted_instruments = changes_made.removing
    existing_instruments_maybe_modified = changes_made.existing

    process_new_instruments(
        data_in=data_in, data_out=data_out, new_instruments=new_instruments
    )

    process_deleted_instruments(
        data_out=data_out, deleted_instruments=deleted_instruments
    )

    process_modified_instruments(
        data_in=data_in,
        data_out=data_out,
        existing_instruments_maybe_modified=existing_instruments_maybe_modified,
        echo_difference=echo_difference,
        check_only=check_only,
    )


def process_new_instruments(data_in, data_out, new_instruments):
    if len(new_instruments) == 0:
        return None

    print("New instruments %s " % str(new_instruments))
    check_adding = true_if_answer_is_yes("Confirm every instrument to add?")

    for instrument_code in new_instruments:
        instrument_object = data_in.get_roll_parameters(instrument_code)
        if check_adding:
            okay_to_add = true_if_answer_is_yes(
                "OK to add %s?" % str(instrument_object)
            )
            if not okay_to_add:
                continue

        data_out.add_roll_parameters(instrument_code, instrument_object)

        # check
        instrument_added = data_out.get_roll_parameters(instrument_code)
        print("Added %s: %s to %s" % (instrument_code, instrument_added, data_out))


def process_modified_instruments(
    data_in,
    data_out,
    existing_instruments_maybe_modified,
    echo_difference: bool,
    check_only: bool,
):
    modified_instruments = []
    for instrument_code in existing_instruments_maybe_modified:
        roll_object = data_in.get_roll_parameters(instrument_code)
        existing_roll_object = data_out.get_roll_parameters(instrument_code)

        if roll_object != existing_roll_object:
            if echo_difference:
                print(f"\nFound difference in roll configs for {instrument_code}:")
                print(f"\tExisting config: {existing_roll_object}")
                print(f"\tNew config: {roll_object}")
            modified_instruments.append(instrument_code)

    if len(modified_instruments) == 0:
        return None
    if check_only:
        print(f'\nFound changes in roll config for {", ".join(modified_instruments)}')
        return

    diag_prices = diagPrices()
    instruments_with_prices = diag_prices.get_list_of_instruments_in_multiple_prices()

    check_if_modifying = true_if_answer_is_yes("Check if modifying an instrument?")

    print("Existing instruments that might be modified %s " % str(modified_instruments))
    for instrument_code in modified_instruments:
        roll_object = data_in.get_roll_parameters(instrument_code)

        instrument_has_price = instrument_code in instruments_with_prices
        if instrument_has_price:
            print(
                f"{instrument_code} has prices. Are you REALLY sure you want to modify it's roll config?"
                "You would be much better off using /sysinit/futures/safely_modify_roll_parameters.py"
            )

        if check_if_modifying or instrument_has_price:
            existing_roll_object = data_out.get_roll_parameters(instrument_code)
            okay_to_modify = true_if_answer_is_yes(
                "Do you want to replace \n%s with \n%s for %s"
                % (str(existing_roll_object), str(roll_object), instrument_code)
            )

            if not okay_to_modify:
                continue

        data_out.delete_roll_parameters(instrument_code, are_you_sure=True)
        data_out.add_roll_parameters(instrument_code, roll_object)

        # check
        instrument_added = data_out.get_roll_parameters(instrument_code)
        print("Added %s: %s to %s" % (instrument_code, instrument_added, data_out))


def process_deleted_instruments(data_out, deleted_instruments):
    if len(deleted_instruments) == 0:
        return None

    print("Instrument roll config to be deleted %s " % str(deleted_instruments))
    confim_delete = true_if_answer_is_yes("Confirm each deletion?")

    diag_prices = diagPrices()
    instruments_with_prices = diag_prices.get_list_of_instruments_in_multiple_prices()

    for instrument_code in deleted_instruments:
        instrument_has_price = instrument_code in instruments_with_prices
        if instrument_has_price:
            print(
                "%s has prices. Are you REALLY sure you want to delete it's roll config?"
                % instrument_code
            )
        if confim_delete or instrument_has_price:
            okay_to_delete = true_if_answer_is_yes(
                "Okay to delete roll config for %s?" % instrument_code
            )
            if not okay_to_delete:
                continue

        data_out.delete_roll_parameters(instrument_code, are_you_sure=True)


if __name__ == "__main__":
    print(__doc__)
    parser = argparse.ArgumentParser()
    parser.add_argument("--echo-diff", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parsed = parser.parse_args()
    copy_roll_parameters_from_csv_to_mongo(
        dataBlob(), echo_difference=parsed.echo_diff, check_only=parsed.check_only
    )
