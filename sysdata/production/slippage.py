## Expected slippage eg half bid-ask spread
## Used to be in instrument config, now seperate

from sysdata.base_data import baseData
from syslogdiag.log_to_screen import logtoscreen


class spreadCostData(baseData):
    def __init__(self, log=logtoscreen("SpreadCosts")):
        super().__init__(log=log)

    def update_spread_cost(self, instrument_code: str, spread_cost: float):
        raise NotImplementedError

    def get_spread_cost(self, instrument_code: str) -> float:
        raise NotImplementedError
