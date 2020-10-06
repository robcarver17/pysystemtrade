from syscore.genutils import NOT_REQUIRED
from ib_insync import Future
import re


def ib_futures_instrument_just_symbol(symbol):
    ibcontract = Future(symbol=symbol)
    return ibcontract


def ib_futures_instrument(futures_instrument_object):
    """
    Get an IB contract which is NOT specific to a contract date
    Used for getting expiry chains

    :param futures_instrument_object: instrument with .metadata suitable for IB
    :return: IBcontract
    """

    meta_data = futures_instrument_object.meta_data

    ibcontract = Future(meta_data["symbol"], exchange=meta_data["exchange"])
    if meta_data["ibMultiplier"] is NOT_REQUIRED:
        pass
    else:
        ibcontract.multiplier = int(meta_data["ibMultiplier"])
    if meta_data["currency"] is NOT_REQUIRED:
        pass
    else:
        ibcontract.currency = meta_data["currency"]

    return ibcontract


def resolve_multiple_expiries(
        ibcontract_list,
        instrument_object_with_metadata):
    code = instrument_object_with_metadata.instrument_code
    ignore_weekly = instrument_object_with_metadata.meta_data["ignoreWeekly"]
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
