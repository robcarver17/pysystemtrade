import re

from sysbrokers.IB.ib_instruments import futuresInstrumentWithIBConfigData


def resolve_multiple_expiries(
        ibcontract_list,
        futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData):
    code = futures_instrument_with_ib_data.instrument_code
    ib_data = futures_instrument_with_ib_data.ib_data
    ignore_weekly = ib_data.ignoreWeekly
    if not ignore_weekly:
        # Can't be resolved
        raise Exception(
            "%s has multiple plausible contracts but is not set to ignoreWeekly in IB config file" %
            code)

    # It's a contract with weekly expiries (probably VIX)
    # Check it's the VIX
    if not code == "VIX":
        raise Exception(
            "You have specified weekly expiries, but I don't have logic for %s" %
            code)

    # Get the symbols
    contract_symbols = [
        ibcontract.localSymbol for ibcontract in ibcontract_list]
    try:
        are_monthly = [_is_vix_symbol_monthly(
            symbol) for symbol in contract_symbols]
    except Exception as exception:
        raise Exception(exception.args[0])

    if are_monthly.count(monthly):
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
