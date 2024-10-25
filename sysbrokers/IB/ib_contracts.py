from typing import Callable

from ib_insync import Contract as ibContract, Contract, ComboLeg
from ib_insync import ContractDetails as ibContractDetails
import re

from sysbrokers.IB.ib_instruments import (
    futuresInstrumentWithIBConfigData,
    ib_futures_instrument,
)
from sysbrokers.IB.ib_positions import resolveBS
from syscore.genutils import list_of_ints_with_highest_common_factor_positive_first
from sysexecution.trade_qty import tradeQuantity
from sysobjects.contract_dates_and_expiries import contractDate

## Yes it's awful. What are you gonna do? At least it's buried in a nice abstraction

VIX_CODE = "VIX"
EUREX_CODES_WITH_DAILYS = ["MSCIWORLD", "MSCIASIA"]
EUREX_DAY_FLAG = "D"

LME_CODES = [
    "ALUMINIUM_LME",
    "COPPER_LME",
    "LEAD_LME",
    "NICKEL_LME",
    "TIN_LME",
    "ZINC_LME",
]

# The day of the month that the third Wednesday must fall between
# Same for any other day of the week, but I couldn't think of a
# good generic variable name
EARLIEST_THIRD_WEDNESDAY = 15
LATEST_THIRD_WEDNESDAY = 21


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

    # It's a contract with weekly expiries - we know two different cases of these
    if code == VIX_CODE:
        resolved_contract = resolve_multiple_expiries_for_VIX(ibcontract_list)
    elif code in EUREX_CODES_WITH_DAILYS:
        resolved_contract = resolve_multiple_expiries_for_EUREX(ibcontract_list)
    elif code in LME_CODES:
        resolved_contract = resolve_multiple_expiries_for_LME(ibcontract_list)
    else:
        raise Exception(
            "You have specified weekly expiries, but I don't have logic for %s" % code
        )

    return resolved_contract


def resolve_multiple_expiries_for_EUREX(ibcontract_list: list) -> ibContract:
    resolved_contract = resolve_multiple_expiries_for_generic_futures(
        ibcontract_list=ibcontract_list, is_monthly_function=_is_eurex_symbol_monthly
    )

    return resolved_contract


def resolve_multiple_expiries_for_LME(ibcontract_list: list) -> ibContract:
    resolved_contract = resolve_multiple_expiries_for_generic_futures(
        ibcontract_list=ibcontract_list, is_monthly_function=_is_lme_symbol_monthly
    )

    return resolved_contract


def resolve_multiple_expiries_for_VIX(ibcontract_list: list) -> ibContract:
    # Get the symbols
    resolved_contract = resolve_multiple_expiries_for_generic_futures(
        ibcontract_list=ibcontract_list, is_monthly_function=_is_vix_symbol_monthly
    )

    return resolved_contract


def resolve_multiple_expiries_for_generic_futures(
    ibcontract_list: list, is_monthly_function: Callable
) -> ibContract:
    # Get the symbols
    contract_symbols = [ibcontract.localSymbol for ibcontract in ibcontract_list]

    try:
        are_monthly = [is_monthly_function(symbol) for symbol in contract_symbols]
    except Exception as exception:
        raise Exception(exception.args[0])

    if are_monthly.count(True) == 1:
        index_of_monthly = are_monthly.index(True)
        resolved_contract = ibcontract_list[index_of_monthly]
    else:
        # no matches or multiple matches
        raise Exception("Can't find a unique monthly expiry")

    return resolved_contract


def _is_vix_symbol_monthly(symbol):
    if re.match("VX[0-9][0-9][A-Z][0-9]", symbol):
        # weekly
        return False
    elif re.match("VX[A-Z][0-9]", symbol):
        # monthly
        return True
    else:
        raise Exception("IB Local Symbol %s not recognised" % symbol)


def _is_eurex_symbol_monthly(symbol: str):
    ## only two possibilties
    is_daily = _is_eurex_symbol_daily(symbol)
    is_monthly = not is_daily

    return is_monthly


def _is_lme_symbol_monthly(symbol: str):
    # 3rd Wednesday of the month is most liquid
    try:
        day = int(symbol[-2:])
    except:
        raise Exception("IB Local Symbol %s not recognised" % symbol)
    return EARLIEST_THIRD_WEDNESDAY <= day <= LATEST_THIRD_WEDNESDAY


def _is_eurex_symbol_daily(symbol: str):
    return symbol[-1] == EUREX_DAY_FLAG


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
