"""
Roll adjusted and multiple prices for a given contract, after checking that we do not have positions

NOTE: this does not update the roll calendar .csv files stored elsewhere. Under DRY the sole source of production
  roll info is the multiple prices series
"""

from syscore.objects import success, failure

from sysdata.futures.adjusted_prices import futuresAdjustedPrices
from sysdata.futures.multiple_prices_functions import update_multiple_prices_on_roll

from sysdata.mongodb.mongo_connection import mongoDb
from sysdata.production.roll_state_storage import \
    allowable_roll_state_from_current_and_position, explain_roll_state, roll_adj_state, no_state_available, default_state

from sysproduction.get_roll_info import roll_report_config
from sysproduction.diagnostic.reporting import run_report_with_data_blob, landing_strip
from sysproduction.data.positions import diagPositions
from sysproduction.data.contracts import diagContracts
from sysproduction.data.get_data import dataBlob


from syslogdiag.log import logToMongod as logger

def update_roll_state(instrument_code: str):
    """
    Update the roll state for a particular instrument
    This includes the option, where possible, to switch the adjusted price series on to a new contract

    :param instrument_code: str
    :return: None
    """

    """
    mongo_db = mongoDb()
    log=logger("Update-Sampled_Contracts", mongo_db=mongo_db)
    """
    with mongoDb() as mongo_db,\
        logger("Update-Roll-Adjusted-Prices", mongo_db=mongo_db, instrument_code=instrument_code) as log:

        data = dataBlob("mongoRollStateData",
                        mongo_db=mongo_db, log=log)

        ## First get the roll info
        # This will also update to console
        report_results = run_report_with_data_blob(roll_report_config, data, instrument_code=instrument_code)
        if report_results is failure:
            print("Can't run roll report, so can't change status")
            return failure

        current_roll_status, roll_state_required = get_required_roll_state(data, instrument_code)
        if roll_state_required is no_state_available:
            return failure

        data.mongo_roll_state.set_roll_state(instrument_code, roll_state_required)

        if roll_state_required is roll_adj_state:
            ## Going to roll adjusted prices
            roll_result = _roll_adjusted_and_multiple_prices(data, instrument_code)
            if roll_result is success:
                ## Return the state back to default (no roll) state
                data.log.msg("Successful roll! Returning roll state of %s to %s" % (instrument_code, default_state))
                data.mongo_roll_state.set_roll_state(instrument_code, default_state)
            else:
                data.log.msg("Something has gone wrong with rolling adjusted of %s! Returning roll state to previous state of %s" % (instrument_code, current_roll_status))
                data.mongo_roll_state.set_roll_state(instrument_code, current_roll_status)

        return success

def get_required_roll_state(data, instrument_code):
    data.add_class_list("mongoRollStateData")
    diag_state = diagPositions(data)
    diag_contracts = diagContracts(data)

    current_roll_status = data.mongo_roll_state.get_roll_state(instrument_code)
    priced_contract_date = diag_contracts.get_priced_contract_id(instrument_code)
    position_priced_contract = diag_state.get_position_for_instrument_and_contract_date(instrument_code, priced_contract_date)

    allowable_roll_states = allowable_roll_state_from_current_and_position(current_roll_status, position_priced_contract)
    max_possible_states = len(allowable_roll_states)-1

    roll_state_required = no_state_available
    while roll_state_required is no_state_available:
        display_roll_query_banner(current_roll_status, position_priced_contract, allowable_roll_states)
        number_of_state_required = input("Which state do you want? [0-%d] " % max_possible_states)
        try:
            number_of_state_required = int(number_of_state_required)
            assert number_of_state_required>=0 # avoid weird behaviour
            roll_state_required = allowable_roll_states[number_of_state_required]
        except:
            print("State %s is not an integer specifying a possible roll state\n" % number_of_state_required)
            roll_state_required = no_state_available
            ## will try again
            continue

        ## Update roll state
        if roll_state_required != current_roll_status:
            # check if changing
            print("")
            check = input("Changing roll state for %s from %s to %s, are you sure y/n: " %
                  (instrument_code, current_roll_status, roll_state_required))
            print("")
            if check=="y":
                # happy
                break
            else:
                print("OK. Choose again.")
                roll_state_required = no_state_available
                # back to top of loop
                continue

    return current_roll_status, roll_state_required

def display_roll_query_banner(current_roll_status, position_priced_contract, allowable_roll_states):
    print(landing_strip(80))
    print("Current State: %s" % current_roll_status)
    print("Current position in priced contract %d (if zero can Roll Adjusted prices)" % position_priced_contract)
    print("")
    print("These are your options:")
    print("")

    for state_number, state in enumerate(allowable_roll_states):
        print("%d) %s: %s" % (state_number, state, explain_roll_state(state)))

    print("")

    return success

def _roll_adjusted_and_multiple_prices(data, instrument_code):
    """
    Roll multiple and adjusted prices

    THE POSITION MUST BE ZERO IN THE PRICED CONTRACT! WE DON'T CHECK THIS HERE

    :param data: dataBlob
    :param instrument_code: str
    :return:
    """
    print(landing_strip(80))
    print("")
    print("Rolling adjusted prices!")
    print("")

    data.add_class_list("arcticFuturesMultiplePricesData arcticFuturesAdjustedPricesData")
    current_multiple_prices = data.arctic_futures_multiple_prices.get_multiple_prices(instrument_code)

    # Only required for potential rollback
    current_adjusted_prices = data.arctic_futures_adjusted_prices.get_adjusted_prices(instrument_code)

    try:
        updated_multiple_prices = update_multiple_prices_on_roll(data, current_multiple_prices, instrument_code)
        new_adj_prices = futuresAdjustedPrices.stich_multiple_prices(updated_multiple_prices)
    except Exception as e:
        data.log.warn("%s : went wrong when rolling: No roll has happened" % e)
        return failure

    # We want user input before we do anything
    compare_old_and_new_prices([current_multiple_prices, updated_multiple_prices,
                                current_adjusted_prices, new_adj_prices],
                               ["Current multiple prices", "New multiple prices",
                               "Current adjusted prices", "New adjusted prices"])
    print("")
    confirm_roll = input("Confirm roll adjusted prices for %s are you sure y/n:" % instrument_code)
    if confirm_roll!="y":
        print("\nUSER DID NOT WANT TO ROLL: Setting roll status back to previous state")
        return failure

    try:
        # Apparently good let's try and write rolled data
        data.arctic_futures_adjusted_prices.add_adjusted_prices(instrument_code, new_adj_prices,
                                                                ignore_duplication=True)
        data.arctic_futures_multiple_prices.add_multiple_prices(instrument_code, updated_multiple_prices,
                                                                ignore_duplication=True)

    except Exception as e:
        data.log.warn("%s went wrong when rolling: Going to roll-back to original multiple/adjusted prices" % e)
        rollback_adjustment(data, instrument_code, current_adjusted_prices, current_multiple_prices)
        return failure

    return success

def compare_old_and_new_prices(price_list, price_list_names):
    for df_prices, df_name in zip(price_list, price_list_names):
        print(df_name)
        print("")
        print(df_prices.tail(3))
        print("")

def rollback_adjustment(data, instrument_code, current_adjusted_prices, current_multiple_prices):

    data.add_class_list("arcticFuturesMultiplePricesData arcticFuturesAdjustedPricesData")
    try:
        data.arctic_futures_adjusted_prices.add_adjusted_prices(instrument_code, current_adjusted_prices,
                                                                ignore_duplication=True)
        data.arctic_futures_multiple_prices.add_multiple_prices(instrument_code, current_multiple_prices,
                                                                ignore_duplication=True)
    except Exception as e:
        data.log.warn("***** ROLLBACK FAILED! %s!You may need to rebuild your data! Check before trading!! *****" % e)
        return failure

    return success

