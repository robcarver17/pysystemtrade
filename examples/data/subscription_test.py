import asyncio
import logging
from typing import Dict
from typing import List

import ib_insync
from ib_insync import ContractDetails
from ib_insync import Future
from ib_insync import IB

from sysbrokers.IB.ib_instruments_data import IBconfig
from sysbrokers.IB.ib_instruments_data import read_ib_config_from_file

HOSTNAME = "localhost"


async def subscription_test(ib_config: IBconfig) -> Dict[str, List[ContractDetails]]:
    ib_insync.util.logToConsole(logging.INFO)
    ib = IB()
    failed = []
    exceptions = []
    ib_symbols: List[str] = ib_config.IBSymbol.tolist()
    instruments: List[str] = ib_config.Instrument.tolist()
    try:
        await ib.connectAsync(host=HOSTNAME, port=4001, clientId=1)
        coros = []
        for i, ib_symbol in enumerate(ib_symbols):
            try:
                ib_exchange = ib_config[
                    ib_config.IBSymbol == ib_symbol
                ].IBExchange.item()
                f = Future(symbol=ib_symbol, exchange=ib_exchange, includeExpired=True)
                coros.append(ib.reqContractDetailsAsync(f))
            except Exception as e:
                failed.append(instruments[i])
                exceptions.append(str(e))
        results = await asyncio.gather(*coros)
        data = {ib: sorted_ContractDetails(cd) for ib, cd in zip(ib_symbols, results)}
    finally:
        ib.disconnect()
    return data, failed, exceptions


def sorted_ContractDetails(contract_details: List[ContractDetails]):
    return sorted(contract_details, key=lambda x: x.realExpirationDate)


def main():
    ib_config: IBconfig = read_ib_config_from_file()
    return asyncio.run(subscription_test(ib_config))


if __name__ == "__main__":
    main()
