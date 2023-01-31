"""
Roll adjusted and multiple prices for a given contract, after checking that we do not have positions

NOTE: this does not update the roll calendar .csv files stored elsewhere. Under DRY the sole source of production
  roll info is the multiple prices series
"""
from dataclasses import dataclass
import numpy as np

from syscore.interactive.input import (
    get_input_from_user_and_convert_to_type,
    true_if_answer_is_yes,
)
from syscore.interactive.menus import print_menu_of_values_and_get_response
from syscore.constants import named_object, status, success, failure
from syscore.interactive.display import (
    print_with_landing_strips_around,
    landing_strip,
)

from sysdata.data_blob import dataBlob

from sysobjects.contracts import futuresContract
from sysobjects.production.roll_state import (
    default_state,
    roll_adj_state,
    explain_roll_state_str,
    allowable_roll_state_from_current_and_position,
    RollState,
    no_roll_state,
    roll_close_state,
)

from sysproduction.reporting.report_configs import roll_report_config
from sysproduction.reporting.reporting_functions import run_report_with_data_blob

from sysproduction.data.positions import diagPositions, updatePositions
from sysproduction.data.controls import dataPositionLimits
from sysproduction.data.contracts import dataContracts
from sysproduction.data.prices import diagPrices, get_valid_instrument_code_from_user

from sysproduction.reporting.data.rolls import (
    rollingAdjustedAndMultiplePrices,
    relative_volume_in_forward_contract_versus_price,
)


no_change_required = named_object("No roll required")
EXIT_CODE = "EXIT"


def interactive_update_roll_status():

    with dataBlob(log_name="Interactive_Update-Roll-Status") as data:
        function_to_call = get_rolling_master_function()
        function_to_call(data)


def get_rolling_master_function():
    MANUAL_INPUT = "Manually input instrument codes and manually decide when to roll"
    MENU_OPTIONS = [
        MANUAL_INPUT,
        "Cycle through instrument codes automatically, but manually decide when to roll",
        "Cycle through instrument codes automatically, auto decide when to roll, manually confirm rolls",
        "Cycle through instrument codes automatically, auto decide when to roll, automatically roll",
    ]

    function_list = [
        update_roll_status_manual_cycle,
        update_roll_status_auto_cycle_manual_decide,
        update_roll_status_auto_cycle_manual_confirm,
        update_roll_status_full_auto,
    ]

    print("How do you want to do your rolls today?")
    selection = print_menu_of_values_and_get_response(
        MENU_OPTIONS, default_str=MANUAL_INPUT
    )
    selection_idx = MENU_OPTIONS.index(selection)

    function_to_call = function_list[selection_idx]

    return function_to_call


@dataclass
class RollDataWithStateReporting(object):
    instrument_code: str
    original_roll_status: RollState
    position_priced_contract: int
    allowable_roll_states_as_list_of_str: list
    days_until_roll: int
    relative_volume: float

    @property
    def original_roll_status_as_string(self):
        return self.original_roll_status.name

    def display_roll_query_banner(self):

        print(landing_strip(80))
        print("Current State: %s" % self.original_roll_status)
        print(
            "Current position in priced contract %d (if zero can Roll Adjusted prices)"
            % self.position_priced_contract
        )
        print("")
        print("These are your options:")
        print("")

        for state_number, state in enumerate(self.allowable_roll_states_as_list_of_str):
            print("%s: %s" % (state, explain_roll_state_str(state)))

        print("")


def update_roll_status_manual_cycle(data: dataBlob):

    do_another = True
    while do_another:
        instrument_code = get_valid_instrument_code_from_user(
            data=data, allow_exit=True, exit_code=EXIT_CODE
        )
        if instrument_code is EXIT_CODE:
            # belt and braces
            do_another = False
        else:
            manually_report_and_update_roll_state_for_code(data, instrument_code)

    return success


def update_roll_status_auto_cycle_manual_decide(data: dataBlob):
    days_ahead = get_days_ahead_to_consider_when_auto_cycling()
    instrument_list = get_list_of_instruments_to_auto_cycle(data, days_ahead=days_ahead)
    for instrument_code in instrument_list:
        manually_report_and_update_roll_state_for_code(
            data=data, instrument_code=instrument_code
        )

    return success


def update_roll_status_auto_cycle_manual_confirm(data: dataBlob):
    days_ahead = get_days_ahead_to_consider_when_auto_cycling()
    auto_parameters = get_auto_roll_parameters()
    instrument_list = get_list_of_instruments_to_auto_cycle(data, days_ahead=days_ahead)

    for instrument_code in instrument_list:
        roll_data = setup_roll_data_with_state_reporting(data, instrument_code)
        roll_state_required = auto_selected_roll_state_instrument(
            data=data, roll_data=roll_data, auto_parameters=auto_parameters
        )

        if roll_state_required is no_change_required:
            warn_not_rolling(instrument_code, auto_parameters)
        else:
            modify_roll_state(
                data=data,
                instrument_code=instrument_code,
                original_roll_state=roll_data.original_roll_status,
                roll_state_required=roll_state_required,
                confirm_adjusted_price_change=True,
            )


def update_roll_status_full_auto(data: dataBlob):
    days_ahead = get_days_ahead_to_consider_when_auto_cycling()
    instrument_list = get_list_of_instruments_to_auto_cycle(data, days_ahead=days_ahead)
    auto_parameters = get_auto_roll_parameters()

    for instrument_code in instrument_list:
        roll_data = setup_roll_data_with_state_reporting(data, instrument_code)
        roll_state_required = auto_selected_roll_state_instrument(
            data=data, roll_data=roll_data, auto_parameters=auto_parameters
        )

        if roll_state_required is no_change_required:
            warn_not_rolling(instrument_code, auto_parameters)
        else:

            modify_roll_state(
                data=data,
                instrument_code=instrument_code,
                original_roll_state=roll_data.original_roll_status,
                roll_state_required=roll_state_required,
                confirm_adjusted_price_change=False,
            )


def get_days_ahead_to_consider_when_auto_cycling() -> int:
    days_ahead = get_input_from_user_and_convert_to_type(
        "How many days ahead should I look for expiries?",
        type_expected=int,
        allow_default=True,
        default_value=10,
    )

    return days_ahead


def get_list_of_instruments_to_auto_cycle(data: dataBlob, days_ahead: int = 10) -> list:

    diag_prices = diagPrices()
    list_of_potential_instruments = (
        diag_prices.get_list_of_instruments_in_multiple_prices()
    )
    instrument_list = [
        instrument_code
        for instrument_code in list_of_potential_instruments
        if include_instrument_in_auto_cycle(
            data=data, instrument_code=instrument_code, days_ahead=days_ahead
        )
    ]

    print_with_landing_strips_around(
        "Identified following instruments that are near expiry %s"
        % str(instrument_list)
    )

    return instrument_list


def include_instrument_in_auto_cycle(
    data: dataBlob, instrument_code: str, days_ahead: int = 10
) -> bool:

    days_until_expiry = days_until_earliest_expiry(data, instrument_code)
    return days_until_expiry <= days_ahead


def days_until_earliest_expiry(data: dataBlob, instrument_code: str) -> int:

    data_contracts = dataContracts(data)
    carry_days = data_contracts.days_until_carry_expiry(instrument_code)
    roll_days = data_contracts.days_until_roll(instrument_code)
    price_days = data_contracts.days_until_price_expiry(instrument_code)

    return min([carry_days, roll_days, price_days])


@dataclass
class autoRollParameters:
    min_volume: float
    manual_prompt_for_position: bool
    state_when_position_held: RollState


def get_auto_roll_parameters() -> autoRollParameters:
    min_volume = get_input_from_user_and_convert_to_type(
        "Minimum relative volume before rolling",
        type_expected=float,
        allow_default=True,
        default_value=0.1,
    )

    manual_prompt_for_position = true_if_answer_is_yes(
        "Manually prompt for state if have position? (y/n)"
    )

    if manual_prompt_for_position:
        state_when_position_held = no_change_required
    else:
        state_when_position_held = get_state_to_use_for_held_position()

    auto_parameters = autoRollParameters(
        min_volume=min_volume,
        manual_prompt_for_position=manual_prompt_for_position,
        state_when_position_held=state_when_position_held,
    )

    return auto_parameters


STATE_OPTIONS = [
    RollState.Passive,
    RollState.Force,
    RollState.Force_Outright,
    RollState.Close,
]
STATE_OPTIONS_AS_STR = [str(state) for state in STATE_OPTIONS]


def get_state_to_use_for_held_position() -> RollState:

    print(
        "Choose state to automatically assume if we have a position in priced contract AND roll state is currently NO ROLL"
    )

    select_state_for_position_held = print_menu_of_values_and_get_response(
        STATE_OPTIONS_AS_STR, default_str=STATE_OPTIONS_AS_STR[0]
    )

    state_when_position_held = STATE_OPTIONS[
        STATE_OPTIONS_AS_STR.index(select_state_for_position_held)
    ]

    return state_when_position_held


def auto_selected_roll_state_instrument(
    data: dataBlob,
    roll_data: RollDataWithStateReporting,
    auto_parameters: autoRollParameters,
) -> RollState:

    if roll_data.relative_volume < auto_parameters.min_volume:

        run_roll_report(data, roll_data.instrument_code)
        print_with_landing_strips_around(
            "For %s relative volume of %f is less than minimum of %s : NOT AUTO ROLLING"
            % (
                roll_data.instrument_code,
                roll_data.relative_volume,
                auto_parameters.min_volume,
            )
        )
        return no_change_required

    no_position_held = roll_data.position_priced_contract == 0

    if no_position_held:
        run_roll_report(data, roll_data.instrument_code)
        print_with_landing_strips_around(
            "No position held, auto rolling adjusted price for %s"
            % roll_data.instrument_code
        )
        return roll_adj_state

    if auto_parameters.manual_prompt_for_position:
        run_roll_report(data, roll_data.instrument_code)
        roll_state_required = get_roll_state_required(roll_data)
        return roll_state_required

    original_roll_status = roll_data.original_roll_status
    if original_roll_status is no_roll_state:
        roll_state_required = auto_parameters.state_when_position_held

        print_with_landing_strips_around(
            "Automatically changing state from %s to %s for %s"
            % (original_roll_status, roll_state_required, roll_data.instrument_code)
        )
    else:
        print_with_landing_strips_around(
            "Roll status already set to %s for %s: not changing"
            % (original_roll_status, roll_data.instrument_code)
        )
        return no_change_required

    return roll_state_required


def warn_not_rolling(instrument_code: str, auto_parameters: autoRollParameters):

    print_with_landing_strips_around(
        "\n NOT rolling %s as doesn't meet auto parameters %s\n"
        % (instrument_code, str(auto_parameters))
    )


def manually_report_and_update_roll_state_for_code(
    data: dataBlob, instrument_code: str
):
    run_roll_report(data, instrument_code)
    manually_update_roll_state_for_code(data, instrument_code)


def manually_update_roll_state_for_code(data: dataBlob, instrument_code: str):
    # First get the roll info
    # This will also update to console

    data.log.setup(instrument_code=instrument_code)
    roll_data = setup_roll_data_with_state_reporting(data, instrument_code)

    roll_state_required = get_roll_state_required(roll_data)

    modify_roll_state(
        data=data,
        instrument_code=instrument_code,
        original_roll_state=roll_data.original_roll_status,
        roll_state_required=roll_state_required,
        confirm_adjusted_price_change=True,
    )

    return success


def run_roll_report(data: dataBlob, instrument_code: str):
    config = roll_report_config.new_config_with_modified_output("console")
    config.modify_kwargs(instrument_code=instrument_code)
    report_results = run_report_with_data_blob(config, data)
    if report_results is failure:
        raise Exception("Can't run roll report, so can't change status")


def get_roll_state_required(roll_data: RollDataWithStateReporting) -> RollState:
    invalid_input = True
    while invalid_input:
        roll_data.display_roll_query_banner()
        roll_state_required_as_str = print_menu_of_values_and_get_response(
            roll_data.allowable_roll_states_as_list_of_str
        )

        if roll_state_required_as_str != roll_data.original_roll_status_as_string:
            # check if changing
            print("")
            okay_to_change = true_if_answer_is_yes(
                "Changing roll state for %s from %s to %s, are you sure y/n to try again/<RETURN> to exit: "
                % (
                    roll_data.instrument_code,
                    roll_data.original_roll_status_as_string,
                    roll_state_required_as_str,
                ),
                allow_empty_to_return_none=True,
            )
            print("")
            if okay_to_change is None:
                return no_change_required

            if okay_to_change:
                # happy
                return RollState[roll_state_required_as_str]
            else:
                print("OK. Choose again.")
                # back to top of loop
                continue
        else:
            print("No change")
            return no_change_required


def setup_roll_data_with_state_reporting(
    data: dataBlob, instrument_code: str
) -> RollDataWithStateReporting:
    diag_positions = diagPositions(data)
    diag_contracts = dataContracts(data)

    original_roll_status = diag_positions.get_roll_state(instrument_code)
    priced_contract_date = diag_contracts.get_priced_contract_id(instrument_code)

    contract = futuresContract(instrument_code, priced_contract_date)

    position_priced_contract = int(diag_positions.get_position_for_contract(contract))

    allowable_roll_states = allowable_roll_state_from_current_and_position(
        original_roll_status, position_priced_contract
    )

    days_until_roll = diag_contracts.days_until_roll(instrument_code)

    relative_volume = relative_volume_in_forward_contract_versus_price(
        data=data, instrument_code=instrument_code
    )
    if np.isnan(relative_volume):
        relative_volume = 0.0

    roll_data_with_state = RollDataWithStateReporting(
        instrument_code=instrument_code,
        original_roll_status=original_roll_status,
        position_priced_contract=position_priced_contract,
        allowable_roll_states_as_list_of_str=allowable_roll_states,
        days_until_roll=days_until_roll,
        relative_volume=relative_volume,
    )

    return roll_data_with_state


def modify_roll_state(
    data: dataBlob,
    instrument_code: str,
    original_roll_state: RollState,
    roll_state_required: RollState,
    confirm_adjusted_price_change: bool = True,
):

    if roll_state_required is no_change_required:
        return

    if roll_state_required is original_roll_state:
        return

    update_positions = updatePositions(data)

    if original_roll_state is roll_close_state:
        roll_state_was_closed_now_something_else(data, instrument_code)

    update_positions.set_roll_state(instrument_code, roll_state_required)
    if roll_state_required is roll_adj_state:
        state_change_to_roll_adjusted_prices(
            data=data,
            instrument_code=instrument_code,
            original_roll_state=original_roll_state,
            confirm_adjusted_price_change=confirm_adjusted_price_change,
        )

    if roll_state_required is roll_close_state:
        roll_state_is_now_closing(data, instrument_code)


def roll_state_was_closed_now_something_else(data: dataBlob, instrument_code: str):
    print(
        "Roll state is no longer closed, so removing temporary position limit of zero"
    )
    data_position_limits = dataPositionLimits(data)
    data_position_limits.reset_position_limit_for_instrument_to_original_value(
        instrument_code
    )


def roll_state_is_now_closing(data: dataBlob, instrument_code: str):
    print("Roll state is Close, so setting temporary position limit of zero")
    data_position_limits = dataPositionLimits(data)
    data_position_limits.temporarily_set_position_limit_to_zero_and_store_original_limit(
        instrument_code
    )


def state_change_to_roll_adjusted_prices(
    data: dataBlob,
    instrument_code: str,
    original_roll_state: RollState,
    confirm_adjusted_price_change: bool = True,
):
    # Going to roll adjusted prices
    update_positions = updatePositions(data)

    roll_result = roll_adjusted_and_multiple_prices(
        data=data,
        instrument_code=instrument_code,
        confirm_adjusted_price_change=confirm_adjusted_price_change,
    )

    if roll_result is success:
        # Return the state back to default (no roll) state
        data.log.msg(
            "Successful roll! Returning roll state of %s to %s"
            % (instrument_code, default_state)
        )

        update_positions.set_roll_state(instrument_code, default_state)
    else:
        data.log.msg(
            "Something has gone wrong with rolling adjusted of %s! Returning roll state to previous state of %s"
            % (instrument_code, original_roll_state)
        )
        update_positions.set_roll_state(instrument_code, original_roll_state)


def roll_adjusted_and_multiple_prices(
    data: dataBlob, instrument_code: str, confirm_adjusted_price_change: bool = True
) -> status:
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
    rolling_adj_and_mult_object = get_roll_adjusted_multiple_prices_object(
        data=data, instrument_code=instrument_code
    )
    if rolling_adj_and_mult_object is failure:
        print("Error when trying to calculate roll prices")
        return failure

    ## prints to screen
    rolling_adj_and_mult_object.compare_old_and_new_prices()

    if confirm_adjusted_price_change:
        is_okay_to_roll = true_if_answer_is_yes(
            "Confirm roll adjusted prices for %s are you sure y/n:" % instrument_code
        )
        if not is_okay_to_roll:
            print(
                "\nUSER DID NOT WANT TO ROLL: Setting roll status back to previous state"
            )
            return failure
    else:
        print_with_landing_strips_around("AUTO ROLLING - NO USER CONFIRMATION REQUIRED")

    try:
        rolling_adj_and_mult_object.write_new_rolled_data()
    except Exception as e:
        data.log.warn(
            "%s went wrong when rolling: Going to roll-back to original multiple/adjusted prices"
            % e
        )
        rolling_adj_and_mult_object.rollback()
        return failure

    return success


def get_roll_adjusted_multiple_prices_object(
    data: dataBlob,
    instrument_code: str,
) -> rollingAdjustedAndMultiplePrices:

    ## returns failure if goes wrong
    try:
        rolling_adj_and_mult_object = rollingAdjustedAndMultiplePrices(
            data, instrument_code
        )
        ## We do this as getting the object doesn't guarantee it works
        _unused_ = rolling_adj_and_mult_object.updated_multiple_prices
        _unused_ = rolling_adj_and_mult_object.new_adjusted_prices

    except Exception as e:
        print("Error %s when trying to calculate roll prices" % str(e))
        ## Possibly forward fill
        rolling_adj_and_mult_object = (
            _get_roll_adjusted_multiple_prices_object_ffill_option(
                data, instrument_code
            )
        )

    return rolling_adj_and_mult_object


def _get_roll_adjusted_multiple_prices_object_ffill_option(
    data: dataBlob, instrument_code: str
) -> rollingAdjustedAndMultiplePrices:

    ## returns failure if goes wrong
    try_forward_fill = true_if_answer_is_yes(
        "Do you want to try forward filling prices first (less accurate, but guarantees roll)? [y/n]"
    )

    if not try_forward_fill:
        print("OK, nothing I can do")
        return failure

    try:
        rolling_adj_and_mult_object = rollingAdjustedAndMultiplePrices(
            data, instrument_code, allow_forward_fill=True
        )
        ## We do this as getting the object doesn't guarantee it works
        _unused_ = rolling_adj_and_mult_object.updated_multiple_prices

    except Exception as e:
        print(
            "Error %s when trying to calculate roll prices, even when forward filling"
            % str(e)
        )
        return failure

    return rolling_adj_and_mult_object


if __name__ == "__main__":
    interactive_update_roll_status()
