# Copyright 2026 Google LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
Non-interactive automatic roll status update script.

Runs daily after multiple/adjusted prices are updated and before the stack handler.
Automatically updates roll status for instruments based on configured parameters.
"""
import datetime

from syscontrol.run_process import processToRun
from sysdata.data_blob import dataBlob
from sysproduction.reporting.api import reportingApi
from sysobjects.production.roll_state import RollState
from sysproduction.interactive_update_roll_status import (
    autoRollParameters,
    get_list_of_instruments_to_auto_cycle,
    setup_roll_data_with_state_reporting,
    suggest_roll_state_for_instrument,
    modify_roll_state,
    get_auto_roll_parameters_potentially_using_default,
    ASK_FOR_STATE,
)
from sysproduction.data.contracts import dataContracts
from sysproduction.data.positions import diagPositions


def run_auto_roll_status():
    """Main entry point — integrates with processToRun for dashboard monitoring."""
    process_name = "run_auto_roll_status"
    with dataBlob(log_name=process_name) as data:
        list_of_timer_names_and_functions = (
            get_list_of_timer_functions_for_auto_roll_status()
        )
        auto_roll_process = processToRun(
            process_name, data, list_of_timer_names_and_functions
        )
        auto_roll_process.run_process()


def get_list_of_timer_functions_for_auto_roll_status():
    with dataBlob(log_name="update_auto_roll_status") as data:
        auto_roll_object = updateAutoRollStatus(data)
        list_of_timer_names_and_functions = [
            ("update_auto_roll_status", auto_roll_object),
        ]
        return list_of_timer_names_and_functions


class updateAutoRollStatus(object):
    """Callable timer function for the processToRun framework."""

    def __init__(self, data: dataBlob):
        self.data = data

    def update_auto_roll_status(self):
        data = self.data
        api = reportingApi(data)
        auto_roll_status_main(api=api, data=data)


def auto_roll_status_main(api: reportingApi, data: dataBlob):
    """
    Automatically update roll status for all eligible instruments.

    KEY FLOW:
    1. Get auto parameters from config
    2. days_ahead = max(passive_start_days, near_expiry_days) = max(30, 10) = 30
    3. Get instrument list via get_list_of_instruments_to_auto_cycle()
    4. Process each via process_instrument_roll_status()

    NOTE: Instruments with a priced contract more than days_ahead days out
    will be excluded from processing. This is by design — but means instruments
    with orphaned positions in expired contracts (while priced contract is far out)
    will also be missed by this pipeline.
    """
    auto_parameters = get_auto_roll_parameters_potentially_using_default(
        data=data, use_default=True
    )

    days_ahead = max(
        auto_parameters.passive_start_days, auto_parameters.near_expiry_days
    )

    instrument_list = get_list_of_instruments_to_auto_cycle(
        data=api.data, days_ahead=days_ahead
    )

    if not instrument_list:
        data.log.debug(
            "No instruments within %d-day window requiring roll status check"
            % days_ahead
        )
        return

    data.log.debug(
        "Instruments within %d-day window for roll status check: %s"
        % (days_ahead, instrument_list)
    )

    for instrument_code in instrument_list:
        try:
            process_instrument_roll_status(
                data=data,
                api=api,
                instrument_code=instrument_code,
                auto_parameters=auto_parameters,
            )
        except Exception as e:
            data.log.critical(
                "Error processing roll status for %s: %s" % (instrument_code, e)
            )
            continue


def process_instrument_roll_status(
    data: dataBlob,
    api: reportingApi,
    instrument_code: str,
    auto_parameters: autoRollParameters,
):
    """
    Process roll status for a single instrument.

    EXPIRY ESCALATION LOGIC:
    - Fires only if instrument is already in the selection list (passed days_ahead filter)
    - Uses days_until_price_expiry (NOT days_until_roll, NOT min())
    - Condition: days_until_expiry < near_expiry_days (10) AND position != 0

    FORCE ROLL STUCK ESCALATION LOGIC:
    - If instrument has been in Force state for more than force_roll_max_trading_days
      without completing the roll, escalate to Force_Outright
    - This handles cases where spread orders cannot execute due to missing tick data
      or illiquid spread contracts (e.g., CRUDE_W_mini BAG contracts on IB)
    """
    roll_data = setup_roll_data_with_state_reporting(data, instrument_code)

    _log_auto_roll_position_diagnostics(data, instrument_code, roll_data)

    priced_contract_expiring_soon = (
        roll_data.days_until_expiry < auto_parameters.near_expiry_days
    )
    position_held = roll_data.position_priced_contract != 0

    # Check if Force roll is stuck and needs escalation to Force_Outright
    if roll_data.original_roll_status == RollState.Force and position_held:
        force_roll_stuck, trading_days = _is_force_roll_stuck(
            data, instrument_code, auto_parameters
        )
        if force_roll_stuck:
            roll_state_required = RollState.Force_Outright
            data.log.critical(
                "FORCE ROLL STUCK for %s: In Force state for %d trading days "
                "(threshold: %d) without completing roll. "
                "Escalating to Force_Outright to execute outright orders instead of spread."
                % (
                    instrument_code,
                    trading_days,
                    auto_parameters.force_roll_max_trading_days,
                )
            )
            # Skip normal logic, go straight to state change
            _apply_roll_state_change(
                data, instrument_code, roll_data, roll_state_required
            )
            return

    if priced_contract_expiring_soon and position_held:
        roll_state_required = RollState.Force
        reason = "expiry_escalation"
        data.log.critical(
            "EXPIRY ESCALATION for %s: "
            "Priced contract has expired (days_until_expiry=%d) but position=%d is still held. "
            "Overriding suggested state to Force."
            % (
                instrument_code,
                roll_data.days_until_expiry,
                roll_data.position_priced_contract,
            )
        )
    else:
        roll_state_required = suggest_roll_state_for_instrument(
            roll_data=roll_data,
            auto_parameters=auto_parameters,
        )

        # Determine reason for state selection
        if (
            roll_state_required == RollState.Force
            and roll_data.days_until_roll < 0
            and roll_data.position_priced_contract != 0
        ):
            reason = "late_roll_escalation"
        elif roll_state_required == RollState.Passive:
            reason = "early_passive"
        elif roll_state_required == RollState.No_Open:
            reason = "forward_illiquid_close_to_roll"
        elif roll_state_required == RollState.Roll_Adjusted:
            if getattr(roll_data, "any_key_contract_expired", False):
                reason = "expired_key_contract_auto_roll"
            else:
                reason = "roll_adjusted"
        elif roll_state_required == RollState.No_Roll:
            reason = "no_roll"
        else:
            reason = "default"

        # If config says "Ask", auto-resolve to Force in non-interactive mode.
        if roll_state_required == ASK_FOR_STATE:
            roll_state_required = RollState.Force
            reason = "auto_resolved_ask"
            data.log.critical(
                "AUTO-RESOLVED ASK_FOR_STATE to Force for %s: "
                "Config default_roll_state_if_undecided is 'Ask' but running "
                "non-interactively. Forward liquid, position=%d, "
                "days_to_roll=%d, rel_vol=%.4f. "
                "Consider changing config to 'Force' to silence this."
                % (
                    instrument_code,
                    roll_data.position_priced_contract,
                    roll_data.days_until_roll,
                    roll_data.relative_volume,
                )
            )

        if roll_state_required == RollState.Roll_Adjusted:
            blocked, block_reason = _roll_adjusted_blocked_by_expiring_positions(
                data=data,
                instrument_code=instrument_code,
                auto_parameters=auto_parameters,
            )
            if blocked:
                data.log.critical(
                    "ROLL_ADJUSTED BLOCKED for %s: %s. "
                    "Leaving roll state unchanged and requiring manual/Force roll review."
                    % (instrument_code, block_reason)
                )
                return

    # No change needed
    if roll_data.original_roll_status == roll_state_required:
        data.log.debug(
            "No roll status change needed for %s (current: %s)"
            % (instrument_code, roll_data.original_roll_status.name)
        )
        return

    allowable_states = roll_data.allowable_roll_states_as_list_of_str
    if roll_state_required.name not in allowable_states:
        data.log.critical(
            "INVALID TRANSITION for %s: "
            "Cannot change from %s to %s (position=%d). "
            "Allowable transitions: %s. Skipping."
            % (
                instrument_code,
                roll_data.original_roll_status.name,
                roll_state_required.name,
                roll_data.position_priced_contract,
                allowable_states,
            )
        )
        return

    data.log.debug(
        "Auto-updating roll state for %s: %s -> %s "
        "reason=%s "
        "(position=%d, days_until_expiry=%d, days_to_roll=%d, rel_vol=%.4f, fwd_vol=%d)"
        % (
            instrument_code,
            roll_data.original_roll_status.name,
            roll_state_required.name,
            reason,
            roll_data.position_priced_contract,
            roll_data.days_until_expiry,
            roll_data.days_until_roll,
            roll_data.relative_volume,
            roll_data.absolute_forward_volume,
        )
    )

    modify_roll_state(
        data=data,
        instrument_code=instrument_code,
        original_roll_state=roll_data.original_roll_status,
        roll_state_required=roll_state_required,
        confirm_adjusted_price_change=False,
        allow_auto_forward_fill=True,
    )


def _log_auto_roll_position_diagnostics(
    data: dataBlob,
    instrument_code: str,
    roll_data,
):
    """
    Log the exact priced contract input and all current DB contract positions.

    This makes the auto-roll decision auditable: if the priced-contract position
    is zero but there are live positions in expiring/non-priced contracts, the
    log will show that before any state change is made.
    """
    data_contracts = dataContracts(data)

    priced_contract_id = data_contracts.get_priced_contract_id(instrument_code)
    try:
        priced_actual_expiry = data_contracts.get_actual_expiry(
            instrument_code, priced_contract_id
        ).as_str()
    except Exception as exc:
        priced_actual_expiry = "unknown (%s)" % str(exc)

    current_positions = _current_contract_positions_for_instrument_as_strings(
        data=data, instrument_code=instrument_code
    )

    data.log.debug(
        "AUTO ROLL DIAGNOSTIC for %s: priced_contract=%s actual_expiry=%s "
        "position_priced_contract=%d days_until_expiry=%d days_until_roll=%d "
        "current_db_contract_positions=%s"
        % (
            instrument_code,
            priced_contract_id,
            priced_actual_expiry,
            roll_data.position_priced_contract,
            roll_data.days_until_expiry,
            roll_data.days_until_roll,
            current_positions,
        )
    )


def _current_contract_positions_for_instrument_as_strings(
    data: dataBlob, instrument_code: str
) -> list:
    diag_positions = diagPositions(data)
    current_positions = diag_positions.get_all_current_contract_positions()

    return [
        str(position_entry)
        for position_entry in current_positions
        if position_entry.instrument_code == instrument_code
    ]


def _roll_adjusted_blocked_by_expiring_positions(
    data: dataBlob,
    instrument_code: str,
    auto_parameters: autoRollParameters,
) -> tuple:
    """
    Block no-position Roll_Adjusted if any DB contract position is expiring soon.

    The normal decision is based on the current priced contract's position, so
    a stale or orphaned non-priced DB leg can be missed once contract metadata
    advances. Before changing to Roll_Adjusted, scan all current DB contract
    positions for the instrument and refuse the adjusted-price roll if any live
    position maps to an actual expiry inside the near-expiry window.
    """
    diag_positions = diagPositions(data)
    data_contracts = dataContracts(data)
    now = datetime.datetime.now()

    blocking_positions = []
    current_positions = diag_positions.get_all_current_contract_positions()
    for position_entry in current_positions:
        if position_entry.instrument_code != instrument_code:
            continue
        if position_entry.position == 0:
            continue

        contract = position_entry.contract
        try:
            actual_expiry = data_contracts.get_actual_expiry(
                instrument_code, contract.date_str
            )
        except Exception as exc:
            blocking_positions.append(
                "%s position %d actual_expiry=unknown (%s)"
                % (str(contract), position_entry.position, str(exc))
            )
            continue

        days_until_actual_expiry = (actual_expiry - now).days
        if days_until_actual_expiry < auto_parameters.near_expiry_days:
            blocking_positions.append(
                "%s position %d actual_expiry=%s days_until_expiry=%d"
                % (
                    str(contract),
                    position_entry.position,
                    actual_expiry.as_str(),
                    days_until_actual_expiry,
                )
            )

    if not blocking_positions:
        return False, ""

    return (
        True,
        "expiring DB contract positions exist despite zero priced-contract position: %s"
        % blocking_positions,
    )


def _is_force_roll_stuck(
    data: dataBlob,
    instrument_code: str,
    auto_parameters: autoRollParameters,
) -> tuple:
    """
    Check if a Force roll has been stuck for more than the configured
    number of trading days.

    Returns:
        tuple: (is_stuck: bool, trading_days: int)
    """
    from sysproduction.data.positions import diagPositions

    diag_positions = diagPositions(data)
    force_since = diag_positions.db_roll_state_data.get_roll_state_set_time(
        instrument_code
    )

    if force_since is None:
        # No timestamp recorded - state was set before this feature existed
        # or state was changed manually. Can't determine stuck status.
        return False, 0

    trading_days = _count_trading_days_since(force_since)
    max_days = getattr(auto_parameters, "force_roll_max_trading_days", 2)

    return trading_days >= max_days, trading_days


def _count_trading_days_since(start_date) -> int:
    """
    Count the number of trading days (weekdays) since the given date.
    Uses a simple weekday count as a proxy for trading days.
    """
    import datetime

    now = datetime.datetime.now()
    # Convert to date if datetime
    if hasattr(start_date, "date"):
        start_date = start_date.date()
    today = now.date()

    trading_days = 0
    current = start_date
    while current < today:
        # Monday = 0, Sunday = 6; count Mon-Fri as trading days
        if current.weekday() < 5:
            trading_days += 1
        current += datetime.timedelta(days=1)

    return trading_days


def _apply_roll_state_change(
    data: dataBlob,
    instrument_code: str,
    roll_data,
    roll_state_required: RollState,
    reason: str = "force_roll_stuck",
):
    """
    Apply a roll state change, checking allowable transitions.
    Used by the force roll stuck escalation logic.
    """
    allowable_states = roll_data.allowable_roll_states_as_list_of_str
    if roll_state_required.name not in allowable_states:
        data.log.critical(
            "INVALID TRANSITION for %s: "
            "Cannot change from %s to %s (position=%d). "
            "Allowable transitions: %s. Skipping."
            % (
                instrument_code,
                roll_data.original_roll_status.name,
                roll_state_required.name,
                roll_data.position_priced_contract,
                allowable_states,
            )
        )
        return

    data.log.debug(
        "Auto-updating roll state for %s: %s -> %s "
        "reason=%s "
        "(position=%d, days_until_expiry=%d, days_to_roll=%d, rel_vol=%.4f, fwd_vol=%d)"
        % (
            instrument_code,
            roll_data.original_roll_status.name,
            roll_state_required.name,
            reason,
            roll_data.position_priced_contract,
            roll_data.days_until_expiry,
            roll_data.days_until_roll,
            roll_data.relative_volume,
            roll_data.absolute_forward_volume,
        )
    )

    modify_roll_state(
        data=data,
        instrument_code=instrument_code,
        original_roll_state=roll_data.original_roll_status,
        roll_state_required=roll_state_required,
        confirm_adjusted_price_change=False,
        allow_auto_forward_fill=True,
    )


if __name__ == "__main__":
    run_auto_roll_status()
