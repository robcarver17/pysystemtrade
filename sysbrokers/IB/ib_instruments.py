from dataclasses import dataclass
from ib_insync import Future

from sysobjects.instruments import futuresInstrument


def ib_futures_instrument_just_symbol(symbol):
    ibcontract = Future(symbol=symbol)
    return ibcontract


NOT_REQUIRED_FOR_IB = ""


@dataclass
class ibInstrumentConfigData:
    symbol: str
    exchange: str
    currency: str = NOT_REQUIRED_FOR_IB
    ibMultiplier: float = NOT_REQUIRED_FOR_IB
    myMultiplier: float = 1.0
    ignoreWeekly: bool = False

    # NOTE: is myMultiplier actually used?


@dataclass
class futuresInstrumentWithIBConfigData(object):
    instrument: futuresInstrument
    ib_data: ibInstrumentConfigData

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    @property
    def broker_symbol(self):
        return self.ib_data.symbol


def ib_futures_instrument(futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData):
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