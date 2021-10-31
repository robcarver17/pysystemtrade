import datetime
import pandas as pd

from sysproduction.data.prices import diagPrices

from syscore.objects import header, table, body_text

# We want a roll report (We could merge this into another kind of report)
# We want to be able to have it emailed, or run it offline
# To have it emailed, we'll call the report function and optionally pass the output to a text file not stdout
# Reports consist of multiple calls to functions with data object, each of which returns a displayable object
# We also chuck in a title and a timestamp
from sysproduction.utilities.rolls import get_roll_data_for_instrument

ALL_ROLL_INSTRUMENTS = "ALL"

def roll_info(data, instrument_code=ALL_ROLL_INSTRUMENTS):
    """
    Get some roll info. For all markets which are:

    - currently rolling
    - need to have roll status changed now or in the near future

    We calculate:
    - Volume data
    - Curve data
    - Length to expiry data (contract and/or carry)
    - Current roll status
    - Suggested roll status

    :param: data blob
    :return: list of pd.DataFrame
    """
    diag_prices = diagPrices(data)

    if instrument_code == ALL_ROLL_INSTRUMENTS:
        list_of_instruments = diag_prices.get_list_of_instruments_in_multiple_prices()

    else:
        list_of_instruments = [instrument_code]

    results_dict = {}
    for instrument_code in list_of_instruments:
        roll_data = get_roll_data_for_instrument(instrument_code, data)
        results_dict[instrument_code] = roll_data

    formatted_output = format_roll_data_for_instrument(results_dict)

    return formatted_output


def format_roll_data_for_instrument(results_dict):
    """
    Put the results into a printable format

    :param results_dict: dict, keys are instruments, contains roll information
    :return:
    """

    instrument_codes = list(results_dict.keys())

    formatted_output = []

    formatted_output.append(
        header(
            "Roll status report produced on %s" % str(
                datetime.datetime.now())))

    table1_df = pd.DataFrame(
        dict(
            Status=[results_dict[code]["status"] for code in instrument_codes],
            Roll_exp=[results_dict[code]["roll_expiry"] for code in instrument_codes],
            Prc_exp=[results_dict[code]["price_expiry"] for code in instrument_codes],
            Crry_exp=[results_dict[code]["carry_expiry"] for code in instrument_codes],
        ),
        index=instrument_codes,
    )

    # sort by time to theoretical roll, and apply same sort order for all
    # tables
    table1_df = table1_df.sort_values("Roll_exp")
    instrument_codes = list(table1_df.index)

    table1 = table("Status and time to roll in days", table1_df)
    formatted_output.append(table1)
    formatted_output.append(
        body_text(
            "Roll_exp is days until preferred roll set by roll parameters. Prc_exp is days until price contract expires, "
            "Crry_exp is days until carry contract expires"
        )
    )

    # will always be 6 wide
    width_contract_columns = len(
        results_dict[instrument_codes[0]]["contract_labels"])

    table2_dict = {}
    for col_number in range(width_contract_columns):
        table2_dict["C%d" % col_number] = [
            str(results_dict[code]["contract_labels"][col_number])
            for code in instrument_codes
        ]

    table2_df = pd.DataFrame(table2_dict, index=instrument_codes)
    table2 = table("List of contracts", table2_df)
    formatted_output.append(table2)
    formatted_output.append(body_text("Suffix: p=price, f=forward, c=carry"))

    table2b_dict = {}
    for col_number in range(width_contract_columns):
        table2b_dict["Pos%d" % col_number] = [results_dict[code][
            "positions"][col_number] for code in instrument_codes]

    table2b_df = pd.DataFrame(table2b_dict, index=instrument_codes)

    table2b = table("Positions", table2b_df)
    formatted_output.append(table2b)

    table3_dict = {}
    for col_number in range(width_contract_columns):
        table3_dict["V%d" % col_number] = [results_dict[code][
            "volumes"][col_number] for code in instrument_codes]

    table3_df = pd.DataFrame(table3_dict, index=instrument_codes)
    table3_df = table3_df.round(2)

    table3 = table("Relative volumes", table3_df)
    formatted_output.append(table3)
    formatted_output.append(
        body_text(
            "Contract volumes over recent days, normalised so largest volume is 1.0"
        )
    )


    formatted_output.append(header("END OF ROLL REPORT"))

    return formatted_output
