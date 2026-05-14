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
Comprehensive tests for the automatic roll status system.

Tests cover:
  1. suggest_roll_state_for_instrument — all decision branches
  2. Volume threshold logic (liquid vs illiquid forward)
  3. Time boundary logic (near_expiry_days, passive_start_days)
  4. Early passive rolling
  5. ASK_FOR_STATE auto-resolution
  6. State transition validation against the allowable transition matrix
  7. process_instrument_roll_status integration logic
  8. Expiry escalation: Passive+position+expiring_soon → Force
"""
import pytest
from unittest.mock import MagicMock, patch

from sysobjects.production.roll_state import (
    RollState,
    allowable_roll_state_from_current_and_position,
)
from sysproduction.interactive_update_roll_status import (
    suggest_roll_state_for_instrument,
    check_if_forward_liquid,
    check_if_within_passive_start_window,
    check_if_getting_close_to_desired_roll_date,
    include_instrument_in_auto_cycle,
    check_if_any_key_contract_has_expired,
    autoRollParameters,
    RollDataWithStateReporting,
    ASK_FOR_STATE,
)


# ============================================================================
# Fixtures: default parameters and roll data builders
# ============================================================================


def make_auto_params(
    auto_roll_if_relative_volume_higher_than=1.0,
    min_relative_volume=0.01,
    min_absolute_volume=100,
    near_expiry_days=10,
    default_roll_state_if_undecided=RollState.Force,
    auto_roll_expired=True,
    passive_start_days=30,
    force_roll_max_trading_days=2,
):
    return autoRollParameters(
        auto_roll_if_relative_volume_higher_than=auto_roll_if_relative_volume_higher_than,
        min_relative_volume=min_relative_volume,
        min_absolute_volume=min_absolute_volume,
        near_expiry_days=near_expiry_days,
        default_roll_state_if_undecided=default_roll_state_if_undecided,
        auto_roll_expired=auto_roll_expired,
        passive_start_days=passive_start_days,
        force_roll_max_trading_days=force_roll_max_trading_days,
    )


def make_roll_data(
    instrument_code="TEST",
    original_roll_status=RollState.No_Roll,
    position_priced_contract=0,
    days_until_roll=50,
    relative_volume=0.0,
    absolute_forward_volume=0,
    days_until_expiry=60,
):
    allowable = allowable_roll_state_from_current_and_position(
        original_roll_status, position_priced_contract
    )
    return RollDataWithStateReporting(
        instrument_code=instrument_code,
        original_roll_status=original_roll_status,
        position_priced_contract=position_priced_contract,
        allowable_roll_states_as_list_of_str=allowable,
        days_until_roll=days_until_roll,
        relative_volume=relative_volume,
        absolute_forward_volume=absolute_forward_volume,
        days_until_expiry=days_until_expiry,
    )


DEFAULT_PARAMS = make_auto_params()


# ============================================================================
# 1. CORE DECISION LOGIC: suggest_roll_state_for_instrument
# ============================================================================


class TestSuggestRollStateExpired:
    """Expired priced contract scenarios.

    NOTE: suggest_roll_state_for_instrument only handles expired+NO_POSITION
    via check_if_expired_and_auto_rolling_expired. The expired+POSITION case
    is handled upstream in process_instrument_roll_status (expiry escalation).
    These tests verify what suggest returns in each case so the escalation
    logic knows what it's overriding.
    """

    def test_expired_no_position_auto_roll(self):
        """Expired + no position + auto_roll_expired=True → Roll_Adjusted."""
        roll_data = make_roll_data(
            position_priced_contract=0,
            days_until_expiry=-1,
            days_until_roll=50,
            relative_volume=0.0,
            absolute_forward_volume=0,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Roll_Adjusted

    def test_expired_no_position_auto_roll_disabled(self):
        """Expired + no position + auto_roll_expired=False → falls through to normal logic."""
        params = make_auto_params(auto_roll_expired=False)
        roll_data = make_roll_data(
            position_priced_contract=0,
            days_until_expiry=-1,
            days_until_roll=50,
            relative_volume=0.0,
            absolute_forward_volume=0,
        )
        # Forward illiquid, far from roll → No_Roll
        result = suggest_roll_state_for_instrument(roll_data, params)
        assert result == RollState.No_Roll

    def test_expired_with_position_suggest_returns_no_roll(self):
        """Expired + position held → suggest returns No_Roll (the gap).

        This documents the known gap: suggest_roll_state_for_instrument does NOT
        escalate to Force when expired+position. The escalation is handled by
        process_instrument_roll_status (see TestExpiryEscalation).
        """
        roll_data = make_roll_data(
            position_priced_contract=10,
            days_until_expiry=-1,
            days_until_roll=50,
            relative_volume=0.0,
            absolute_forward_volume=0,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        # Has position, forward illiquid, far from roll → No_Roll. The
        # higher-level expiry escalation in process_instrument_roll_status is
        # what catches this case; suggest itself does not.
        assert result == RollState.No_Roll

    def test_expired_exactly_at_zero(self):
        """Expired at exactly day 0 → Roll_Adjusted for no position."""
        roll_data = make_roll_data(
            position_priced_contract=0,
            days_until_expiry=0,
            days_until_roll=50,
            relative_volume=0.0,
            absolute_forward_volume=0,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Roll_Adjusted

    def test_expired_key_contract_no_position_auto_roll(self):
        """Expired carry/key contract + no position → Roll_Adjusted even if priced expiry is far out.

        Regression for BUTTER/CHEESE/MILKWET: the carry contract can expire while
        the priced contract remains outside the normal auto-roll look-ahead window.
        """
        roll_data = make_roll_data(
            instrument_code="BUTTER",
            position_priced_contract=0,
            days_until_expiry=33,  # priced contract still outside 30-day window
            days_until_roll=-7,
            relative_volume=0.05,
            absolute_forward_volume=27,
        )
        roll_data.any_key_contract_expired = True

        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Roll_Adjusted

    def test_expired_key_contract_no_position_respects_auto_roll_disabled(self):
        """Expired key contract does not force Roll_Adjusted if auto_roll_expired=False."""
        params = make_auto_params(auto_roll_expired=False)
        roll_data = make_roll_data(
            instrument_code="BUTTER",
            position_priced_contract=0,
            days_until_expiry=33,
            days_until_roll=-7,
            relative_volume=0.0,
            absolute_forward_volume=0,
        )
        roll_data.any_key_contract_expired = True

        result = suggest_roll_state_for_instrument(roll_data, params)
        assert result == RollState.No_Open

    def test_expired_key_contract_with_position_still_uses_late_escalation(self):
        """Expired key contract + position should not Roll_Adjusted over a live position."""
        roll_data = make_roll_data(
            instrument_code="BUTTER",
            original_roll_status=RollState.No_Roll,
            position_priced_contract=1,
            days_until_expiry=33,
            days_until_roll=-7,
            relative_volume=0.05,
            absolute_forward_volume=27,
        )
        roll_data.any_key_contract_expired = True

        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Force


class TestSuggestRollStateForwardLiquid:
    """Forward contract is liquid scenarios."""

    def test_liquid_no_position(self):
        """Forward liquid + no position → Roll_Adjusted."""
        roll_data = make_roll_data(
            position_priced_contract=0,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_roll=50,
            days_until_expiry=60,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Roll_Adjusted

    def test_liquid_with_position_far_from_roll(self):
        """Forward liquid + position + far from roll → Passive."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_roll=50,
            days_until_expiry=60,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Passive

    def test_liquid_with_position_close_to_roll_force(self):
        """Forward liquid + position + close to roll + default=Force → Force."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_roll=5,
            days_until_expiry=15,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Force

    def test_liquid_with_position_close_to_roll_force_outright(self):
        """Forward liquid + position + close to roll + default=Force_Outright."""
        params = make_auto_params(
            default_roll_state_if_undecided=RollState.Force_Outright
        )
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_roll=5,
            days_until_expiry=15,
        )
        result = suggest_roll_state_for_instrument(roll_data, params)
        assert result == RollState.Force_Outright

    def test_liquid_with_position_close_to_roll_close(self):
        """Forward liquid + position + close to roll + default=Close."""
        params = make_auto_params(default_roll_state_if_undecided=RollState.Close)
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_roll=5,
            days_until_expiry=15,
        )
        result = suggest_roll_state_for_instrument(roll_data, params)
        assert result == RollState.Close

    def test_liquid_with_position_close_to_roll_ask(self):
        """Forward liquid + position + close to roll + default=Ask → 'Ask' string."""
        params = make_auto_params(default_roll_state_if_undecided=ASK_FOR_STATE)
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_roll=5,
            days_until_expiry=15,
        )
        result = suggest_roll_state_for_instrument(roll_data, params)
        assert result == ASK_FOR_STATE
        assert result == "Ask"

    def test_liquid_at_exactly_near_expiry_boundary(self):
        """days_until_roll == 9 (< near_expiry_days=10) → close → Force."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_roll=9,
            days_until_expiry=20,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Force

    def test_liquid_at_exactly_near_expiry_boundary_not_close(self):
        """days_until_roll == 10 (== near_expiry_days, NOT < 10) → not close → Passive."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_roll=10,
            days_until_expiry=20,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Passive


class TestSuggestRollStateForwardIlliquid:
    """Forward contract is illiquid scenarios."""

    def test_illiquid_far_from_roll_no_position(self):
        """Forward illiquid + no position + far from roll → No_Roll."""
        roll_data = make_roll_data(
            position_priced_contract=0,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_roll=50,
            days_until_expiry=60,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Roll

    def test_illiquid_close_to_roll_no_position(self):
        """Forward illiquid + no position + close to roll → No_Open."""
        roll_data = make_roll_data(
            position_priced_contract=0,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_roll=5,
            days_until_expiry=15,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Open

    def test_illiquid_close_to_roll_with_position(self):
        """Forward illiquid + position + close to roll + zero volume → No_Open."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_roll=5,
            days_until_expiry=15,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Open

    def test_illiquid_far_from_roll_with_position(self):
        """Forward illiquid + position + far from everything → No_Roll."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_roll=50,
            days_until_expiry=60,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Roll


# ============================================================================
# 2. EARLY PASSIVE ROLLING
# ============================================================================


class TestEarlyPassiveRolling:
    """Forward illiquid but has *some* volume within passive_start_days window."""

    def test_early_passive_within_window_some_volume(self):
        """Illiquid forward + position + within 30 days + some volume → Passive."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.005,
            absolute_forward_volume=20,
            days_until_roll=20,
            days_until_expiry=30,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Passive

    def test_early_passive_within_window_zero_volume(self):
        """Illiquid forward + position + within 30 days + zero volume → NOT Passive."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_roll=20,
            days_until_expiry=30,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Roll

    def test_early_passive_outside_window_some_volume(self):
        """Illiquid forward + position + OUTSIDE 30 days + some volume → No_Roll."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.005,
            absolute_forward_volume=20,
            days_until_roll=35,
            days_until_expiry=45,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Roll

    def test_early_passive_no_position_within_window(self):
        """Illiquid forward + NO position + within 30 days + some volume → No_Roll (not Passive)."""
        roll_data = make_roll_data(
            position_priced_contract=0,
            relative_volume=0.005,
            absolute_forward_volume=20,
            days_until_roll=20,
            days_until_expiry=30,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Roll

    def test_early_passive_at_boundary(self):
        """Illiquid forward + position + at exactly passive_start_days boundary → NOT Passive."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.005,
            absolute_forward_volume=20,
            days_until_roll=30,  # == passive_start_days, NOT < 30
            days_until_expiry=40,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Roll

    def test_early_passive_just_inside_boundary(self):
        """Illiquid forward + position + at 29 days (just inside) → Passive."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.005,
            absolute_forward_volume=20,
            days_until_roll=29,
            days_until_expiry=39,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Passive

    def test_early_passive_relative_vol_zero_but_absolute_nonzero(self):
        """relative_volume=0 but absolute_forward_volume>0 → NOT Passive (both must be >0)."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.0,
            absolute_forward_volume=20,
            days_until_roll=20,
            days_until_expiry=30,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Roll

    def test_early_passive_relative_vol_nonzero_but_absolute_zero(self):
        """relative_volume>0 but absolute_forward_volume=0 → NOT Passive."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.005,
            absolute_forward_volume=0,
            days_until_roll=20,
            days_until_expiry=30,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.No_Roll

    def test_early_passive_close_to_roll_with_some_volume(self):
        """Within passive window AND near_expiry_days + some volume → Passive wins over No_Open."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            relative_volume=0.005,
            absolute_forward_volume=20,
            days_until_roll=5,  # within both passive_start_days AND near_expiry_days
            days_until_expiry=15,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        # Early passive check comes BEFORE the near_expiry check in the illiquid branch
        assert result == RollState.Passive


# ============================================================================
# 3. VOLUME THRESHOLD LOGIC: check_if_forward_liquid
# ============================================================================


class TestCheckIfForwardLiquid:
    """Volume-based liquidity determination."""

    def test_very_high_relative_volume(self):
        """relative > auto_roll_if_relative_volume_higher_than → liquid."""
        roll_data = make_roll_data(relative_volume=1.5)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is True

    def test_exactly_at_auto_roll_threshold(self):
        """relative == threshold → NOT liquid (must be > not >=)."""
        roll_data = make_roll_data(relative_volume=1.0)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is False

    def test_relative_and_absolute_both_met(self):
        """relative > min_relative AND absolute > min_absolute → liquid."""
        roll_data = make_roll_data(relative_volume=0.05, absolute_forward_volume=200)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is True

    def test_relative_met_absolute_not(self):
        """relative > min but absolute below threshold → NOT liquid."""
        roll_data = make_roll_data(relative_volume=0.05, absolute_forward_volume=50)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is False

    def test_absolute_met_relative_not(self):
        """absolute > min but relative below threshold → NOT liquid."""
        roll_data = make_roll_data(relative_volume=0.005, absolute_forward_volume=200)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is False

    def test_both_below_threshold(self):
        """Both below → NOT liquid."""
        roll_data = make_roll_data(relative_volume=0.005, absolute_forward_volume=50)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is False

    def test_zero_volume(self):
        """Zero everything → NOT liquid."""
        roll_data = make_roll_data(relative_volume=0.0, absolute_forward_volume=0)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is False

    def test_at_min_relative_boundary(self):
        """relative == min_relative_volume (0.01) → NOT liquid (must be >)."""
        roll_data = make_roll_data(relative_volume=0.01, absolute_forward_volume=200)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is False

    def test_at_min_absolute_boundary(self):
        """absolute == min_absolute_volume (100) → NOT liquid (must be >)."""
        roll_data = make_roll_data(relative_volume=0.05, absolute_forward_volume=100)
        assert check_if_forward_liquid(roll_data, DEFAULT_PARAMS) is False


# ============================================================================
# 4. TIME BOUNDARY LOGIC
# ============================================================================


class TestTimeBoundaries:
    """Near-expiry and passive start window checks."""

    def test_close_to_roll(self):
        roll_data = make_roll_data(days_until_roll=5)
        assert (
            check_if_getting_close_to_desired_roll_date(roll_data, DEFAULT_PARAMS)
            is True
        )

    def test_not_close_to_roll(self):
        roll_data = make_roll_data(days_until_roll=15)
        assert (
            check_if_getting_close_to_desired_roll_date(roll_data, DEFAULT_PARAMS)
            is False
        )

    def test_exactly_at_near_expiry_days(self):
        """days_until_roll == 10 → NOT close (strict <)."""
        roll_data = make_roll_data(days_until_roll=10)
        assert (
            check_if_getting_close_to_desired_roll_date(roll_data, DEFAULT_PARAMS)
            is False
        )

    def test_one_day_before_near_expiry(self):
        roll_data = make_roll_data(days_until_roll=9)
        assert (
            check_if_getting_close_to_desired_roll_date(roll_data, DEFAULT_PARAMS)
            is True
        )

    def test_within_passive_window(self):
        roll_data = make_roll_data(days_until_roll=20)
        assert check_if_within_passive_start_window(roll_data, DEFAULT_PARAMS) is True

    def test_outside_passive_window(self):
        roll_data = make_roll_data(days_until_roll=35)
        assert check_if_within_passive_start_window(roll_data, DEFAULT_PARAMS) is False

    def test_at_passive_window_boundary(self):
        """days_until_roll == 30 → NOT within (strict <)."""
        roll_data = make_roll_data(days_until_roll=30)
        assert check_if_within_passive_start_window(roll_data, DEFAULT_PARAMS) is False

    def test_just_inside_passive_window(self):
        roll_data = make_roll_data(days_until_roll=29)
        assert check_if_within_passive_start_window(roll_data, DEFAULT_PARAMS) is True


class TestAutoCycleSelectionExpiredKeyContracts:
    """Selection tests for expired carry/key contracts.

    Regression for BUTTER/CHEESE/MILKWET: daily_fx_and_contract_updates checks
    every key contract, but auto-roll previously selected only by priced-contract
    expiry. These tests ensure an expired carry contract brings the instrument
    into the auto-roll cycle even when the priced contract is still outside the
    normal look-ahead window.
    """

    @patch("sysproduction.interactive_update_roll_status.dataContracts")
    def test_include_when_priced_expiry_outside_window_but_key_contract_expired(
        self, mock_data_contracts_class
    ):
        mock_data_contracts = mock_data_contracts_class.return_value
        mock_data_contracts.days_until_price_expiry.return_value = 33
        mock_data_contracts.get_labelled_dict_of_current_contracts.return_value = {
            "contracts": ["20260400", "20260500", "20260600"],
            "labels": ["20260400c", "20260500p", "20260600f"],
        }

        expired_contract = MagicMock()
        expired_contract.expired.return_value = True
        active_contract = MagicMock()
        active_contract.expired.return_value = False
        mock_data_contracts.get_contract_from_db.side_effect = [
            expired_contract,
            active_contract,
            active_contract,
        ]

        assert (
            include_instrument_in_auto_cycle(
                data=MagicMock(), instrument_code="BUTTER", days_ahead=30
            )
            is True
        )

    @patch("sysproduction.interactive_update_roll_status.dataContracts")
    def test_do_not_include_when_priced_expiry_outside_window_and_no_key_expired(
        self, mock_data_contracts_class
    ):
        mock_data_contracts = mock_data_contracts_class.return_value
        mock_data_contracts.days_until_price_expiry.return_value = 33
        mock_data_contracts.get_labelled_dict_of_current_contracts.return_value = {
            "contracts": ["20260500", "20260600", "20260700"],
            "labels": ["20260500c", "20260600p", "20260700f"],
        }

        active_contract = MagicMock()
        active_contract.expired.return_value = False
        mock_data_contracts.get_contract_from_db.return_value = active_contract

        assert (
            include_instrument_in_auto_cycle(
                data=MagicMock(), instrument_code="TEST", days_ahead=30
            )
            is False
        )

    @patch("sysproduction.interactive_update_roll_status.dataContracts")
    def test_key_contract_helper_detects_expired_contract(
        self, mock_data_contracts_class
    ):
        mock_data_contracts = mock_data_contracts_class.return_value
        mock_data_contracts.get_labelled_dict_of_current_contracts.return_value = {
            "contracts": ["20260400", "20260500"],
            "labels": ["20260400c", "20260500p"],
        }
        expired_contract = MagicMock()
        expired_contract.expired.return_value = True
        active_contract = MagicMock()
        active_contract.expired.return_value = False
        mock_data_contracts.get_contract_from_db.side_effect = [
            active_contract,
            expired_contract,
        ]

        assert (
            check_if_any_key_contract_has_expired(
                data=MagicMock(), instrument_code="CHEESE"
            )
            is True
        )

    @patch("sysproduction.interactive_update_roll_status.dataContracts")
    def test_missing_forward_contract_is_tolerated(self, mock_data_contracts_class):
        # Regression: immediately after a Roll_Adjusted the forward slot of the
        # multiple-prices chain points to a contract that update_sampled_contracts
        # has not yet written to the contracts DB. The helper must treat that as
        # not-expired rather than crashing on ContractNotFound.
        from syscore.exceptions import ContractNotFound

        mock_data_contracts = mock_data_contracts_class.return_value
        mock_data_contracts.get_labelled_dict_of_current_contracts.return_value = {
            "contracts": ["20260600", "20260700", "20260900"],
            "labels": ["20260600c", "20260700p", "20260900f"],
        }
        active_contract = MagicMock()
        active_contract.expired.return_value = False
        mock_data_contracts.get_contract_from_db.side_effect = [
            active_contract,
            active_contract,
            ContractNotFound("missing"),
        ]

        assert (
            check_if_any_key_contract_has_expired(
                data=MagicMock(), instrument_code="NIKKEI"
            )
            is False
        )

    @patch("sysproduction.interactive_update_roll_status.dataContracts")
    def test_missing_priced_or_carry_contract_alerts_and_skips(
        self, mock_data_contracts_class
    ):
        # A missing carry or priced contract is never expected — it implies the
        # multiple-prices chain references a delisted or mistyped contract.
        # The helper must emit a critical log and skip that leg without crashing.
        from syscore.exceptions import ContractNotFound

        mock_data_contracts = mock_data_contracts_class.return_value
        mock_data_contracts.get_labelled_dict_of_current_contracts.return_value = {
            "contracts": ["20260600", "20260700", "20260900"],
            "labels": ["20260600c", "20260700p", "20260900f"],
        }
        active_contract = MagicMock()
        active_contract.expired.return_value = False
        mock_data_contracts.get_contract_from_db.side_effect = [
            ContractNotFound("missing carry"),
            active_contract,
            active_contract,
        ]

        mock_data = MagicMock()
        assert (
            check_if_any_key_contract_has_expired(
                data=mock_data, instrument_code="WIDGET"
            )
            is False
        )
        mock_data.log.critical.assert_called_once()


# ============================================================================
# 5. EXPIRY ESCALATION
# ============================================================================


class TestExpiryEscalation:
    """
    process_instrument_roll_status escalates to Force when the priced contract
    is expiring within near_expiry_days and a position is still held.

    This closes the gap where suggest_roll_state_for_instrument would return
    No_Roll (or the current state) for expired+position, leaving the instrument
    in Passive until the stack handler detected a break and locked it.

    The condition is: days_until_expiry < near_expiry_days AND position != 0
    Using near_expiry_days (default 10) rather than <= 0 gives the stack handler
    time to execute the Force roll before the contract disappears.
    """


# ============================================================================
# 13. EXPIRY ESCALATION IN process_instrument_roll_status
# ============================================================================


class TestLateRollEscalation:
    """Late-roll behaviour: when the desired roll date has passed and a
    position is still held, the system must never downgrade urgency.

    Scenarios cover Force/Force_Outright/Close holding their state, and lower-
    urgency states (No_Roll, Passive) escalating to Force.
    """

    def test_gas_us_mini_force_not_downgraded_to_passive(self):
        """GAS_US_mini: Force + position + days_until_roll=-8 should NOT become Passive."""
        roll_data = make_roll_data(
            instrument_code="GAS_US_mini",
            original_roll_status=RollState.Force,
            position_priced_contract=-1,
            days_until_roll=-8,
            relative_volume=0.0828,
            absolute_forward_volume=94,
            days_until_expiry=27,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        # Should stay in Force, NOT downgrade to Passive
        assert result == RollState.Force

    def test_gas_us_mini_no_roll_escalates_to_force(self):
        """GAS_US_mini: No_Roll + position + days_until_roll=-8 should escalate to Force."""
        roll_data = make_roll_data(
            instrument_code="GAS_US_mini",
            original_roll_status=RollState.No_Roll,
            position_priced_contract=-1,
            days_until_roll=-8,
            relative_volume=0.0828,
            absolute_forward_volume=94,
            days_until_expiry=27,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        # Should escalate to Force
        assert result == RollState.Force

    def test_gas_us_mini_passive_not_downgraded_when_past_roll_date(self):
        """GAS_US_mini: Passive + position + days_until_roll=-8 should escalate to Force."""
        roll_data = make_roll_data(
            instrument_code="GAS_US_mini",
            original_roll_status=RollState.Passive,
            position_priced_contract=-1,
            days_until_roll=-8,
            relative_volume=0.0828,
            absolute_forward_volume=94,
            days_until_expiry=27,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        # Should escalate to Force, not stay Passive
        assert result == RollState.Force

    def test_force_outright_kept_when_past_roll_date(self):
        """Force_Outright + position + days_until_roll=-8 should stay Force_Outright."""
        roll_data = make_roll_data(
            instrument_code="TEST",
            original_roll_status=RollState.Force_Outright,
            position_priced_contract=5,
            days_until_roll=-5,
            relative_volume=0.1,
            absolute_forward_volume=50,
            days_until_expiry=20,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Force_Outright

    def test_close_kept_when_past_roll_date(self):
        """Close + position + days_until_roll=-5 should stay Close."""
        roll_data = make_roll_data(
            instrument_code="TEST",
            original_roll_status=RollState.Close,
            position_priced_contract=5,
            days_until_roll=-5,
            relative_volume=0.1,
            absolute_forward_volume=50,
            days_until_expiry=20,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Close


class TestGasPenNoPositionNoOpen:
    """No-position + past-roll-date + illiquid forward should remain No_Open.

    With no position there is nothing to escalate; the right action is to keep
    the instrument flagged for no opens until the forward becomes liquid.
    """

    def test_gas_pen_no_position_past_roll_date_no_open(self):
        """GAS-PEN: No_Roll + no position + days_until_roll=-8 + no volume -> No_Open."""
        roll_data = make_roll_data(
            instrument_code="GAS-PEN",
            original_roll_status=RollState.No_Roll,
            position_priced_contract=0,
            days_until_roll=-8,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_expiry=27,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        # Should be No_Open (forward illiquid, close to roll date)
        assert result == RollState.No_Open

    def test_gas_pen_no_position_no_escalation_to_force(self):
        """GAS-PEN: No position should NOT escalate to Force even past roll date."""
        roll_data = make_roll_data(
            instrument_code="GAS-PEN",
            original_roll_status=RollState.No_Roll,
            position_priced_contract=0,
            days_until_roll=-8,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_expiry=27,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        # Should NOT be Force - no position means no trading emergency
        assert result != RollState.Force


class TestBoundedPassiveWindow:
    """The passive window is bounded: 0 <= days_until_roll < passive_start_days.

    Negative values (past the desired roll date) must not count as "early
    passive" — they are handled by late-roll escalation instead.
    """

    def test_negative_days_not_in_passive_window(self):
        """days_until_roll=-8 should NOT be within passive window."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            days_until_roll=-8,
            relative_volume=0.005,
            absolute_forward_volume=20,
        )
        from sysproduction.interactive_update_roll_status import (
            check_if_within_passive_start_window,
        )

        result = check_if_within_passive_start_window(roll_data, DEFAULT_PARAMS)
        assert result is False

    def test_zero_days_in_passive_window(self):
        """days_until_roll=0 should be within passive window."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            days_until_roll=0,
            relative_volume=0.005,
            absolute_forward_volume=20,
        )
        from sysproduction.interactive_update_roll_status import (
            check_if_within_passive_start_window,
        )

        result = check_if_within_passive_start_window(roll_data, DEFAULT_PARAMS)
        assert result is True

    def test_early_passive_still_works_for_positive_days(self):
        """days_until_roll=20 should still trigger early passive."""
        roll_data = make_roll_data(
            position_priced_contract=5,
            days_until_roll=20,
            relative_volume=0.005,
            absolute_forward_volume=20,
            days_until_expiry=30,
        )
        result = suggest_roll_state_for_instrument(roll_data, DEFAULT_PARAMS)
        assert result == RollState.Passive


class TestExpiryEscalationInProcess:
    """Test the expiry escalation logic in process_instrument_roll_status.

    The current implementation uses days_until_expiry from roll_data directly
    to determine if escalation to Force is needed.
    """

    @patch("sysproduction.run_auto_roll_status.setup_roll_data_with_state_reporting")
    @patch("sysproduction.run_auto_roll_status.suggest_roll_state_for_instrument")
    @patch("sysproduction.run_auto_roll_status.modify_roll_state")
    def test_expiry_escalation_to_force(self, mock_modify, mock_suggest, mock_setup):
        """When priced contract is expiring soon with position, escalate to Force."""
        from sysproduction.run_auto_roll_status import process_instrument_roll_status
        from sysproduction.interactive_update_roll_status import (
            RollDataWithStateReporting,
        )

        # Setup roll_data with expiring contract and position
        # Allowable states must include Force for position > 0
        roll_data = RollDataWithStateReporting(
            instrument_code="VIX",
            original_roll_status=RollState.Passive,
            position_priced_contract=5,  # Has position
            allowable_roll_states_as_list_of_str=[
                "Roll_Adjusted",
                "Passive",
                "No_Roll",
                "No_Open",
                "Force",
                "Force_Outright",
                "Close",
            ],
            days_until_roll=5,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_expiry=3,  # Expiring soon (< near_expiry_days=10)
        )
        mock_setup.return_value = roll_data

        data = MagicMock()
        auto_params = DEFAULT_PARAMS

        process_instrument_roll_status(
            data=data,
            api=MagicMock(),
            instrument_code="VIX",
            auto_parameters=auto_params,
        )

        # Should escalate to Force and call modify_roll_state
        mock_modify.assert_called_once()
        assert mock_modify.call_args[1]["roll_state_required"] == RollState.Force

        # Should log EXPIRY ESCALATION
        escalation_logs = [
            c for c in data.log.critical.call_args_list if "EXPIRY ESCALATION" in str(c)
        ]
        assert len(escalation_logs) == 1

    @patch("sysproduction.run_auto_roll_status.setup_roll_data_with_state_reporting")
    @patch("sysproduction.run_auto_roll_status.suggest_roll_state_for_instrument")
    @patch("sysproduction.run_auto_roll_status.modify_roll_state")
    def test_no_escalation_when_no_position(
        self, mock_modify, mock_suggest, mock_setup
    ):
        """No escalation when contract is expiring but no position held."""
        from sysproduction.run_auto_roll_status import process_instrument_roll_status
        from sysproduction.interactive_update_roll_status import (
            RollDataWithStateReporting,
        )

        roll_data = RollDataWithStateReporting(
            instrument_code="VIX",
            original_roll_status=RollState.Passive,
            position_priced_contract=0,  # No position
            allowable_roll_states_as_list_of_str=[
                "Roll_Adjusted",
                "Passive",
                "No_Roll",
                "No_Open",
            ],
            days_until_roll=5,
            relative_volume=0.0,
            absolute_forward_volume=0,
            days_until_expiry=3,  # Expiring soon but no position
        )
        mock_setup.return_value = roll_data
        mock_suggest.return_value = RollState.Roll_Adjusted

        data = MagicMock()
        auto_params = DEFAULT_PARAMS

        process_instrument_roll_status(
            data=data,
            api=MagicMock(),
            instrument_code="VIX",
            auto_parameters=auto_params,
        )

        # Should NOT escalate - should use suggest result
        assert mock_suggest.called
        # Should NOT log EXPIRY ESCALATION
        escalation_logs = [
            c for c in data.log.critical.call_args_list if "EXPIRY ESCALATION" in str(c)
        ]
        assert len(escalation_logs) == 0

    @patch("sysproduction.run_auto_roll_status.setup_roll_data_with_state_reporting")
    @patch("sysproduction.run_auto_roll_status.suggest_roll_state_for_instrument")
    @patch("sysproduction.run_auto_roll_status.modify_roll_state")
    def test_no_escalation_when_not_expiring_soon(
        self, mock_modify, mock_suggest, mock_setup
    ):
        """No escalation when position held but contract not expiring soon."""
        from sysproduction.run_auto_roll_status import process_instrument_roll_status
        from sysproduction.interactive_update_roll_status import (
            RollDataWithStateReporting,
        )

        roll_data = RollDataWithStateReporting(
            instrument_code="ES",
            original_roll_status=RollState.Passive,
            position_priced_contract=5,  # Has position
            allowable_roll_states_as_list_of_str=[
                "Roll_Adjusted",
                "Passive",
                "No_Roll",
                "No_Open",
            ],
            days_until_roll=50,
            relative_volume=2.0,
            absolute_forward_volume=500,
            days_until_expiry=60,  # Not expiring soon
        )
        mock_setup.return_value = roll_data
        mock_suggest.return_value = RollState.Passive  # Same as current

        data = MagicMock()
        auto_params = DEFAULT_PARAMS

        process_instrument_roll_status(
            data=data,
            api=MagicMock(),
            instrument_code="ES",
            auto_parameters=auto_params,
        )

        # Should NOT log EXPIRY ESCALATION
        escalation_logs = [
            c for c in data.log.critical.call_args_list if "EXPIRY ESCALATION" in str(c)
        ]
        assert len(escalation_logs) == 0

    @patch("sysproduction.run_auto_roll_status.setup_roll_data_with_state_reporting")
    @patch(
        "sysproduction.run_auto_roll_status._roll_adjusted_blocked_by_expiring_positions"
    )
    @patch("sysproduction.run_auto_roll_status._log_auto_roll_position_diagnostics")
    @patch("sysproduction.run_auto_roll_status.suggest_roll_state_for_instrument")
    @patch("sysproduction.run_auto_roll_status.modify_roll_state")
    def test_roll_adjusted_blocked_by_expiring_non_priced_position(
        self, mock_modify, mock_suggest, mock_diag_log, mock_blocked, mock_setup
    ):
        """A zero priced-contract position must not hide an expiring non-priced DB leg."""
        from sysproduction.run_auto_roll_status import process_instrument_roll_status
        from sysproduction.interactive_update_roll_status import (
            RollDataWithStateReporting,
        )

        roll_data = RollDataWithStateReporting(
            instrument_code="GASOILINE",
            original_roll_status=RollState.Passive,
            position_priced_contract=0,
            allowable_roll_states_as_list_of_str=[
                "Roll_Adjusted",
                "Passive",
                "No_Roll",
                "No_Open",
            ],
            days_until_roll=-30,
            relative_volume=0.3661,
            absolute_forward_volume=6204,
            days_until_expiry=30,
        )
        mock_setup.return_value = roll_data
        mock_suggest.return_value = RollState.Roll_Adjusted
        mock_blocked.return_value = (
            True,
            "expiring DB contract positions exist despite zero priced-contract position",
        )

        data = MagicMock()

        process_instrument_roll_status(
            data=data,
            api=MagicMock(),
            instrument_code="GASOILINE",
            auto_parameters=DEFAULT_PARAMS,
        )

        mock_modify.assert_not_called()
        blocked_logs = [
            c
            for c in data.log.critical.call_args_list
            if "ROLL_ADJUSTED BLOCKED" in str(c)
        ]
        assert len(blocked_logs) == 1
