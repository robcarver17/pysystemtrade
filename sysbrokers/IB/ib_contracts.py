from dataclasses import  dataclass

from ib_insync import Future
import re


from sysobjects.instruments import futuresInstrument

def ib_futures_instrument_just_symbol(symbol):
    ibcontract = Future(symbol=symbol)
    return ibcontract

NOT_REQUIRED_FOR_IB = ""

@dataclass
class ibInstrumentData:
    symbol: str
    exchange: str
    currency: str = NOT_REQUIRED_FOR_IB
    ibMultiplier: float = NOT_REQUIRED_FOR_IB
    myMultiplier: float = 1.0
    ignoreWeekly: bool = False

    # NOTE: is myMultiplier actually used?

@dataclass
class futuresInstrumentWithIBData(object):
    instrument: futuresInstrument
    ib_data: ibInstrumentData

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    @property
    def broker_symbol(self):
        return self.ib_data.symbol

def ib_futures_instrument(futures_instrument_with_ib_data: futuresInstrumentWithIBData):
    """
    Get an IB contract which is NOT specific to a contract date
    Used for getting expiry chains

    :param futures_instrument_with_ib_data: instrument with .metadata suitable for IB
    :return: IBcontract
    """

    ib_data = futures_instrument_with_ib_data.ib_data

    ibcontract = Future(ib_data.symbol, exchange=ib_data.exchange)

    if ib_data.ibMultiplier is NOT_REQUIRED_FOR_IB:
        pass
    else:
        ibcontract.multiplier = int(ib_data.ibMultiplier)

    if ib_data.currency is NOT_REQUIRED_FOR_IB:
        pass
    else:
        ibcontract.currency = ib_data.currency

    return ibcontract


def resolve_multiple_expiries(
        ibcontract_list,
        futures_instrument_with_ib_data: futuresInstrumentWithIBData):
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
