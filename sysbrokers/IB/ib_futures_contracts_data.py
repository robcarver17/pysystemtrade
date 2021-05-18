
from sysbrokers.IB.client.ib_contracts_client import ibContractsClient
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
from sysbrokers.IB.ib_connection import connectionIB

from sysbrokers.broker_futures_contract_data import brokerFuturesContractData

from syscore.objects import missing_contract, missing_instrument


from syscore.dateutils import manyTradingStartAndEndDateTimes

from sysobjects.contract_dates_and_expiries import expiryDate
from sysobjects.contracts import futuresContract

from syslogdiag.log_to_screen import logtoscreen


class ibFuturesContractData(brokerFuturesContractData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This gets HISTORIC data from interactive brokers. It is blocking code
    In a live production system it is suitable for running on a daily basis to get end of day prices

    """

    def __init__(self, ibconnection: connectionIB, log=logtoscreen("ibFuturesContractData")):
        super().__init__(log=log)
        self._ibconnection = ibconnection

    def __repr__(self):
        return "IB Futures per contract data %s" % str(self.ib_client)

    @property
    def ibconnection(self) -> connectionIB:
        return self._ibconnection

    @property
    def ib_client(self) -> ibContractsClient:
        client = getattr(self, "_ib_client", None)
        if client is None:
             client = self._ib_client = ibContractsClient(ibconnection=self.ibconnection,
                                        log = self.log)

        return client

    @property
    def ib_futures_instrument_data(self) -> ibFuturesInstrumentData:
        return ibFuturesInstrumentData(self.ibconnection, log = self.log)

    def get_contract_object_with_IB_data(self,
                                         futures_contract: futuresContract,
                                         allow_expired: bool= False) ->futuresContract:
        """
        Return contract_object with IB instrument meta data and correct expiry date added

        :param contract_object:
        :return: modified contract_object
        """

        futures_contract_with_ib_data = self._get_contract_object_with_IB_metadata(futures_contract)
        if futures_contract_with_ib_data is missing_contract:
            return missing_contract

        futures_contract_with_ib_data = futures_contract_with_ib_data.update_expiry_dates_one_at_a_time_with_method(
            self._get_actual_expiry_date_given_single_contract_with_ib_metadata,
            allow_expired=allow_expired)

        return futures_contract_with_ib_data



    def get_actual_expiry_date_for_single_contract(self, futures_contract: futuresContract) -> expiryDate:
        """
        Get the actual expiry date of a contract from IB

        :param futures_contract: type futuresContract
        :return: YYYYMMDD or None
        """
        log = futures_contract.specific_log(self.log)
        if futures_contract.is_spread_contract():
            log.warn("Can't find expiry for multiple leg contract here")
            return missing_contract

        contract_object_with_ib_data = self.get_contract_object_with_IB_data(futures_contract)
        if contract_object_with_ib_data is missing_contract:
            return missing_contract

        expiry_date = contract_object_with_ib_data.expiry_date

        return expiry_date


    def _get_actual_expiry_date_given_single_contract_with_ib_metadata(self,
                                                futures_contract_with_ib_data: futuresContract,
                                                                       allow_expired = False
                                                                       ) -> expiryDate:
        log = futures_contract_with_ib_data.specific_log(self.log)
        if futures_contract_with_ib_data.is_spread_contract():
            log.warn("Can't find expiry for multiple leg contract here")
            return missing_contract

        expiry_date = self.ib_client.broker_get_single_contract_expiry_date(
            futures_contract_with_ib_data,
            allow_expired = allow_expired
        )

        if expiry_date is missing_contract:
            return missing_contract
        else:
            expiry_date = expiryDate.from_str(
                expiry_date)

        return expiry_date

    def _get_contract_object_with_IB_metadata(self, contract_object: futuresContract) -> futuresContract:

        futures_instrument_with_ib_data = self.ib_futures_instrument_data.get_futures_instrument_object_with_IB_data(
            contract_object.instrument_code
        )
        if futures_instrument_with_ib_data is missing_instrument:
            return missing_contract

        contract_object_with_ib_data = (
            contract_object.new_contract_with_replaced_instrument_object(
                futures_instrument_with_ib_data
            )
        )

        return contract_object_with_ib_data


    def get_min_tick_size_for_contract(self, contract_object: futuresContract) -> float:
        new_log = contract_object.log(self.log)
        contract_object_with_ib_data = self.get_contract_object_with_IB_data(contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.msg("Can't resolve contract so can't find tick size")
            return missing_contract

        min_tick_size = self.ib_client.ib_get_min_tick_size(
            contract_object_with_ib_data
        )

        if min_tick_size is missing_contract:
            new_log.msg("No tick size found")
            return missing_contract

        return min_tick_size


    def is_contract_okay_to_trade(self, futures_contract: futuresContract) -> bool:
        trading_hours = self.get_trading_hours_for_contract(futures_contract)
        trading_hours_checker = manyTradingStartAndEndDateTimes(trading_hours)

        return trading_hours_checker.okay_to_trade_now()


    def less_than_N_hours_of_trading_left_for_contract(self, contract_object: futuresContract,
                                                       N_hours: float = 1.0) -> bool:
        trading_hours = self.get_trading_hours_for_contract(contract_object)
        trading_hours_checker = manyTradingStartAndEndDateTimes(trading_hours)

        return trading_hours_checker.less_than_N_hours_left(N_hours=N_hours)


    def get_trading_hours_for_contract(self, futures_contract: futuresContract) -> list :
        """

        :param futures_contract:
        :return: list of paired date times
        """
        new_log = futures_contract.log(self.log)

        contract_object_with_ib_data = self.get_contract_object_with_IB_data(futures_contract)
        if contract_object_with_ib_data is missing_contract:
            new_log.msg("Can't resolve contract")
            return missing_contract

        trading_hours = self.ib_client.ib_get_trading_hours(
            contract_object_with_ib_data
        )

        if trading_hours is missing_contract:
            new_log.msg("No IB expiry date found")
            trading_hours = []

        return trading_hours
