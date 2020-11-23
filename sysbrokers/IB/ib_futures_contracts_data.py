
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData

from syscore.objects import missing_contract, missing_instrument

from sysdata.futures.contracts import futuresContractData
from syscore.dateutils import manyTradingStartAndEnd

from sysobjects.contract_dates_and_expiries import expiryDate
from sysobjects.contracts import  contract_from_code_and_id, futuresContract

from syslogdiag.log import logtoscreen


class ibFuturesContractData(futuresContractData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This gets HISTORIC data from interactive brokers. It is blocking code
    In a live production system it is suitable for running on a daily basis to get end of day prices

    """

    def __init__(self, ibconnection, log=logtoscreen("ibFuturesContractData")):
        super().__init__(log=log)
        self._ibconnection = ibconnection

    def __repr__(self):
        return "IB Futures per contract data %s" % str(self.ibconnection)

    @property
    def ibconnection(self):
        return self._ibconnection

    @property
    def ib_futures_instrument_data(self):
        return ibFuturesInstrumentData(self.ibconnection, log = self.log)

    def get_list_of_contract_dates_for_instrument_code(self, instrument_code: str):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def get_all_contract_objects_for_instrument_code(self, *args, **kwargs):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def _get_contract_data_without_checking(
            self, instrument_code: str, contract_date: str) -> futuresContract:
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def is_contract_in_data(self, *args, **kwargs):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def _delete_contract_data_without_any_warning_be_careful(
        self, instrument_code: str, contract_date: str
    ):
        raise NotImplementedError("IB is ready only")

    def _add_contract_object_without_checking_for_existing_entry(
            self, contract_object: futuresContract):
        raise NotImplementedError("IB is ready only")

    def get_contract_object_with_IB_data(self, original_contract_object: futuresContract) ->futuresContract:
        """
        Return contract_object with IB instrument meta data and correct expiry date added

        :param contract_object:
        :return: modified contract_object
        """

        contract_object = self._get_contract_object_with_IB_metadata(original_contract_object)
        if contract_object is missing_contract:
            return missing_contract

        new_expiry = self._get_actual_expiry_date_given_contract_with_ib_metadata(contract_object)

        if new_expiry is missing_contract:
            return missing_contract

        contract_object.update_expiry_date(new_expiry)

        return contract_object



    def get_actual_expiry_date_for_contract(self, contract_object: futuresContract) -> expiryDate:
        """
        FIXME CONSIDER USE OF get_contract_object_with_IB_data INSTEAD
        Get the actual expiry date of a contract from IB

        :param contract_object: type futuresContract
        :return: YYYYMMDD or None
        """

        log = contract_object.log(self.log)
        contract_object_with_ib_data = self._get_contract_object_with_IB_metadata(
            contract_object)
        if contract_object_with_ib_data is missing_contract:
            log.msg("Can't resolve contract so can't find expiry date")
            return missing_contract

        expiry_date = self._get_actual_expiry_date_given_contract_with_ib_metadata(contract_object_with_ib_data)

        return expiry_date


    def _get_actual_expiry_date_given_contract_with_ib_metadata(self, contract_object_with_ib_data: futuresContract) -> expiryDate:
        expiry_date = self.ibconnection.broker_get_contract_expiry_date(
            contract_object_with_ib_data
        )

        if expiry_date is missing_contract:
            log = contract_object_with_ib_data.log(self.log)
            log.msg("No IB expiry date found")
            return missing_contract
        else:
            expiry_date = expiryDate.from_str(
                expiry_date)

        return expiry_date

    def get_contract_object_with_IB_metadata(self, contract_object: futuresContract) -> futuresContract:
        #FIXME CONSIDER USE OF get_contract_object_with_IB_data INSTEAD as public method
        return self._get_contract_object_with_IB_metadata(contract_object)


    def _get_contract_object_with_IB_metadata(self, contract_object: futuresContract) -> futuresContract:
        # keep this method delete the public method

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

        min_tick_size = self.ibconnection.ib_get_min_tick_size(
            contract_object_with_ib_data
        )

        if min_tick_size is missing_contract:
            new_log.msg("No tick size found")
            return missing_contract

        return min_tick_size


    def is_contract_okay_to_trade(self, contract_object: futuresContract) -> bool:
        trading_hours = self.get_trading_hours_for_contract(contract_object)
        trading_hours_checker = manyTradingStartAndEnd(trading_hours)

        return trading_hours_checker.okay_to_trade_now()



    def less_than_one_hour_of_trading_leg_for_contract(self, contract_object: futuresContract) -> bool:
        trading_hours = self.get_trading_hours_for_contract(contract_object)
        trading_hours_checker = manyTradingStartAndEnd(trading_hours)

        return trading_hours_checker.less_than_one_hour_left()


    def get_trading_hours_for_contract(self, contract_object: futuresContract) :
        """

        :param contract_object:
        :return: list of paired date times
        """
        new_log = contract_object.log(self.log)

        contract_object_with_ib_data = self.get_contract_object_with_IB_data(contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.msg("Can't resolve contract so can't find expiry date")
            return missing_contract

        trading_hours = self.ibconnection.ib_get_trading_hours(
            contract_object_with_ib_data
        )

        if trading_hours is missing_contract:
            new_log.msg("No IB expiry date found")
            trading_hours = []

        return trading_hours
