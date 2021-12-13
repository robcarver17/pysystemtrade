from ib_insync import Contract as ibContract, Contract, ComboLeg
import re

from sysbrokers.IB.ib_instruments import (
    futuresInstrumentWithIBConfigData,
    ib_futures_instrument,
)
from sysbrokers.IB.ib_positions import resolveBS
from syscore.genutils import list_of_ints_with_highest_common_factor_positive_first
from sysexecution.trade_qty import tradeQuantity
from sysobjects.contract_dates_and_expiries import contractDate


def resolve_multiple_expiries(
    ibcontract_list: list,
    futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData,
) -> ibContract:

    code = futures_instrument_with_ib_data.instrument_code
    ib_data = futures_instrument_with_ib_data.ib_data
    ignore_weekly = ib_data.ignoreWeekly

    if not ignore_weekly:
        # Can't be resolved
        raise Exception(
            "%s has multiple plausible contracts but is not set to ignoreWeekly in IB config file"
            % code
        )

    # It's a contract with weekly expiries (probably VIX)
    # Check it's the VIX
    if not code == "VIX":
        raise Exception(
            "You have specified weekly expiries, but I don't have logic for %s" % code
        )

    # Get the symbols
    contract_symbols = [ibcontract.localSymbol for ibcontract in ibcontract_list]
    try:
        are_monthly = [_is_vix_symbol_monthly(symbol) for symbol in contract_symbols]
    except Exception as exception:
        raise Exception(exception.args[0])

    if are_monthly.count(monthly) == 1:
        index_of_monthly = are_monthly.index(monthly)
        resolved_contract = ibcontract_list[index_of_monthly]
    else:
        # no matches or multiple matches
        raise Exception("Can't find a unique monthly expiry")

    return resolved_contract


monthly = object()
weekly = object()


def _is_vix_symbol_monthly(symbol):
    if re.match("VX[0-9][0-9][A-Z][0-9]", symbol):
        # weekly
        return weekly
    elif re.match("VX[A-Z][0-9]", symbol):
        # monthly
        return monthly
    else:
        raise Exception("IB Local Symbol %s not recognised" % symbol)


NO_LEGS = []


class ibcontractWithLegs(object):
    def __init__(self, ibcontract: ibContract, legs: list = NO_LEGS):
        self.ibcontract = ibcontract
        self.legs = legs

    def __repr__(self):
        return str(self.ibcontract) + " " + str(self.legs)


def get_ib_contract_with_specific_expiry(
    futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData,
    contract_date: contractDate,
) -> Contract:

    ibcontract = ib_futures_instrument(futures_instrument_with_ib_data)
    contract_date_string = str(contract_date.date_str)

    contract_day_was_passed = contract_date.is_day_defined()
    if contract_day_was_passed:
        # Already have the expiry
        pass
    else:
        # Don't have the expiry so lose the days at the end so it's just
        # 'YYYYMM'
        contract_date_string = contract_date_string[:6]

    ibcontract.lastTradeDateOrContractMonth = contract_date_string

    return ibcontract


def resolve_unique_contract_from_ibcontract_list(
    ibcontract_list: list,
    futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData,
) -> Contract:
    if len(ibcontract_list) == 0:
        # No contracts found
        raise Exception("No contracts found matching pattern")

    elif len(ibcontract_list) == 1:
        # OK no hassle, only one contract no confusion
        resolved_contract = ibcontract_list[0]
    else:
        # It might be a contract with weekly expiries (probably VIX)
        # We need to find the right one
        resolved_contract = resolve_multiple_expiries(
            ibcontract_list, futures_instrument_with_ib_data
        )

    return resolved_contract


def _add_legs_to_ib_contract(
    ibcontract: Contract,
    trade_list_for_multiple_legs: tradeQuantity,
    resolved_legs: list,
) -> ibcontractWithLegs:

    ratio_list = list_of_ints_with_highest_common_factor_positive_first(
        trade_list_for_multiple_legs
    )

    ibcontract_legs = [
        _get_ib_combo_leg(ratio, resolved_leg)
        for ratio, resolved_leg in zip(ratio_list, resolved_legs)
    ]
    ibcontract.comboLegs = ibcontract_legs

    ibcontract_with_legs = ibcontractWithLegs(ibcontract, resolved_legs)

    return ibcontract_with_legs


def _get_ib_combo_leg(ratio, resolved_leg):
    leg = ComboLeg()
    leg.conId = int(resolved_leg.conId)
    leg.exchange = str(resolved_leg.exchange)

    action, size = resolveBS(ratio)

    leg.ratio = int(size)
    leg.action = str(action)

    return leg
