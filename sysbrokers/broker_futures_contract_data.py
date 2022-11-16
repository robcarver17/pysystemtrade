from sysobjects.production.trading_hours import listOfOpeningTimes
from syscore.exceptions import missingContract
from sysdata.futures.contracts import futuresContractData

from sysobjects.contract_dates_and_expiries import expiryDate
from sysobjects.contracts import futuresContract

from syslogdiag.log_to_screen import logtoscreen


class brokerFuturesContractData(futuresContractData):
    def __init__(self, log=logtoscreen("brokerFuturesContractData")):
        super().__init__(log=log)

    def get_actual_expiry_date_for_single_contract(
        self, futures_contract: futuresContract
    ) -> expiryDate:
        raise NotImplementedError

    def get_min_tick_size_for_contract(self, contract_object: futuresContract) -> float:
        raise NotImplementedError

    def is_contract_okay_to_trade(self, futures_contract: futuresContract) -> bool:
        new_log = futures_contract.log(self.log)

        try:
            trading_hours = self.get_trading_hours_for_contract(futures_contract)
        except missingContract:
            new_log.critical(
                "Error! Cannot find active contract! Expired? interactive_update_roll_status.py not executed?"
            )
            return False

        return trading_hours.okay_to_trade_now()


    def less_than_N_hours_of_trading_left_for_contract(
        self, contract_object: futuresContract, N_hours: float = 1.0
    ) -> bool:
        try:
            trading_hours = self.get_trading_hours_for_contract(contract_object)
        except missingContract:
            return False
        else:
            return trading_hours.less_than_N_hours_left(N_hours=N_hours)

    def get_trading_hours_for_contract(self, futures_contract: futuresContract) -> \
            listOfOpeningTimes:
        raise NotImplementedError


    def get_list_of_contract_dates_for_instrument_code(self, instrument_code: str):
        raise NotImplementedError("Consider implementing for consistent interface")

    def get_all_contract_objects_for_instrument_code(self, *args, **kwargs):
        raise NotImplementedError("Consider implementing for consistent interface")

    def _get_contract_data_without_checking(
        self, instrument_code: str, contract_date: str
    ) -> futuresContract:
        raise NotImplementedError("Consider implementing for consistent interface")

    def is_contract_in_data(self, *args, **kwargs):
        raise NotImplementedError("Consider implementing for consistent interface")

    def _delete_contract_data_without_any_warning_be_careful(
        self, instrument_code: str, contract_date: str
    ):
        raise NotImplementedError("Broker is read only")

    def _add_contract_object_without_checking_for_existing_entry(
        self, contract_object: futuresContract
    ):
        raise NotImplementedError("Broker is read only")
