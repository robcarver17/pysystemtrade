# Copyright 2026 Google LLC
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Unit tests for the auto-cycle selection helpers in interactive_update_roll_status.

Covers:
  * include_instrument_in_auto_cycle - the (carry, roll, price) day-window
    union check, plus the OR-d "any key contract expired" safety net.
  * check_if_any_key_contract_has_expired - iteration over labelled
    carry/priced/forward contracts, ContractNotFound tolerance for the
    forward leg only, critical log for missing carry/priced.
"""
from unittest.mock import MagicMock, patch

import pytest

from syscore.exceptions import ContractNotFound
from sysproduction.interactive_update_roll_status import (
    check_if_any_key_contract_has_expired,
    include_instrument_in_auto_cycle,
)


def _make_data_blob():
    data = MagicMock()
    data.log = MagicMock()
    return data


def _patch_data_contracts(monkeypatch, instance):
    """
    interactive_update_roll_status constructs `dataContracts(data)` inside the
    helpers. Patch that constructor so each call returns our mock.
    """
    monkeypatch.setattr(
        "sysproduction.interactive_update_roll_status.dataContracts",
        lambda _data: instance,
    )


# ---------------------------------------------------------------------------
# include_instrument_in_auto_cycle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "carry_days,roll_days,price_days",
    [
        (5, 50, 50),   # carry alarm
        (50, 5, 50),   # roll alarm
        (50, 50, 5),   # price alarm
    ],
)
def test_include_when_any_window_alarm_fires(monkeypatch, carry_days, roll_days, price_days):
    """Selection should fire for the union of (carry, roll, price) windows."""
    contracts = MagicMock()
    contracts.days_until_carry_expiry.return_value = carry_days
    contracts.days_until_roll.return_value = roll_days
    contracts.days_until_price_expiry.return_value = price_days
    _patch_data_contracts(monkeypatch, contracts)

    assert include_instrument_in_auto_cycle(
        data=_make_data_blob(), instrument_code="X", days_ahead=10
    ) is True


def test_include_when_no_window_alarm_but_key_contract_expired(monkeypatch):
    """Smoke detector fires even when all three day windows are clear."""
    contracts = MagicMock()
    contracts.days_until_carry_expiry.return_value = 50
    contracts.days_until_roll.return_value = 50
    contracts.days_until_price_expiry.return_value = 50

    expired_carry = MagicMock()
    expired_carry.expired.return_value = True
    contracts.get_contract_from_db.return_value = expired_carry

    contracts.get_labelled_dict_of_current_contracts.return_value = {
        "contracts": ["20260100", "20260700", "20260800"],
        "labels": ["20260100c", "20260700p", "20260800f"],
    }
    _patch_data_contracts(monkeypatch, contracts)

    assert include_instrument_in_auto_cycle(
        data=_make_data_blob(), instrument_code="X", days_ahead=10
    ) is True


def test_exclude_when_nothing_fires(monkeypatch):
    """Neither alarm nor smoke detector -> excluded."""
    contracts = MagicMock()
    contracts.days_until_carry_expiry.return_value = 50
    contracts.days_until_roll.return_value = 50
    contracts.days_until_price_expiry.return_value = 50

    healthy = MagicMock()
    healthy.expired.return_value = False
    contracts.get_contract_from_db.return_value = healthy

    contracts.get_labelled_dict_of_current_contracts.return_value = {
        "contracts": ["20260700", "20260800", "20260900"],
        "labels": ["20260700c", "20260800p", "20260900f"],
    }
    _patch_data_contracts(monkeypatch, contracts)

    assert include_instrument_in_auto_cycle(
        data=_make_data_blob(), instrument_code="X", days_ahead=10
    ) is False


def test_window_alarm_short_circuits_smoke_detector(monkeypatch):
    """If the day-window alarm fires we should not bother iterating contracts."""
    contracts = MagicMock()
    contracts.days_until_carry_expiry.return_value = 1
    contracts.days_until_roll.return_value = 50
    contracts.days_until_price_expiry.return_value = 50
    _patch_data_contracts(monkeypatch, contracts)

    assert include_instrument_in_auto_cycle(
        data=_make_data_blob(), instrument_code="X", days_ahead=10
    ) is True
    contracts.get_labelled_dict_of_current_contracts.assert_not_called()


# ---------------------------------------------------------------------------
# check_if_any_key_contract_has_expired
# ---------------------------------------------------------------------------


def test_smoke_detector_true_when_any_leg_expired(monkeypatch):
    contracts = MagicMock()
    contracts.get_labelled_dict_of_current_contracts.return_value = {
        "contracts": ["20260100", "20260700", "20260800"],
        "labels": ["20260100c", "20260700p", "20260800f"],
    }

    fresh = MagicMock(); fresh.expired.return_value = False
    expired = MagicMock(); expired.expired.return_value = True
    contracts.get_contract_from_db.side_effect = [fresh, expired, fresh]
    _patch_data_contracts(monkeypatch, contracts)

    assert check_if_any_key_contract_has_expired(
        data=_make_data_blob(), instrument_code="X"
    ) is True


def test_smoke_detector_false_when_all_legs_fresh(monkeypatch):
    contracts = MagicMock()
    contracts.get_labelled_dict_of_current_contracts.return_value = {
        "contracts": ["20260700", "20260800", "20260900"],
        "labels": ["20260700c", "20260800p", "20260900f"],
    }
    fresh = MagicMock(); fresh.expired.return_value = False
    contracts.get_contract_from_db.return_value = fresh
    _patch_data_contracts(monkeypatch, contracts)

    assert check_if_any_key_contract_has_expired(
        data=_make_data_blob(), instrument_code="X"
    ) is False


def test_smoke_detector_tolerates_unsampled_forward(monkeypatch):
    """ContractNotFound on the forward leg is expected after a fresh Roll_Adjusted."""
    contracts = MagicMock()
    contracts.get_labelled_dict_of_current_contracts.return_value = {
        "contracts": ["20260700", "20260800", "20260900"],
        "labels": ["20260700c", "20260800p", "20260900f"],
    }
    fresh = MagicMock(); fresh.expired.return_value = False

    def side_effect(contract):
        if contract.date_str == "20260900":
            raise ContractNotFound("forward not yet sampled")
        return fresh

    contracts.get_contract_from_db.side_effect = side_effect
    _patch_data_contracts(monkeypatch, contracts)

    data = _make_data_blob()
    assert check_if_any_key_contract_has_expired(
        data=data, instrument_code="X"
    ) is False
    data.log.critical.assert_not_called()
    data.log.debug.assert_called()


def test_smoke_detector_logs_critical_for_missing_priced(monkeypatch):
    """ContractNotFound on the priced leg should not be silently swallowed."""
    contracts = MagicMock()
    contracts.get_labelled_dict_of_current_contracts.return_value = {
        "contracts": ["20260700", "20260800", "20260900"],
        "labels": ["20260700c", "20260800p", "20260900f"],
    }
    fresh = MagicMock(); fresh.expired.return_value = False

    def side_effect(contract):
        if contract.date_str == "20260800":  # priced
            raise ContractNotFound("priced missing from DB")
        return fresh

    contracts.get_contract_from_db.side_effect = side_effect
    _patch_data_contracts(monkeypatch, contracts)

    data = _make_data_blob()
    assert check_if_any_key_contract_has_expired(
        data=data, instrument_code="X"
    ) is False
    data.log.critical.assert_called_once()
