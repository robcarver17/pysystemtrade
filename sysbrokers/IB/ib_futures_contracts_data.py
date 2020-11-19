
from sysdata.futures.contracts import futuresContractData
from sysobjects.contract_dates_and_expiries import expiryDate
from sysobjects.contracts import  contract_from_code_and_id
from sysdata.futures.trading_hours import manyTradingStartAndEnd

from syslogdiag.log import logtoscreen
from syscore.objects import missing_contract, missing_instrument
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData


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

    ## WHY ISN'T THIS A PARENT METHOD?
    def has_data_for_contract(self, contract_object):
        """
        Does IB have data for a given contract?

        Overriden because we will have a problem matching expiry dates to nominal yyyymm dates
        :param contract_object:
        :return: bool
        """

        expiry_date = self.get_actual_expiry_date_for_contract(contract_object)
        if expiry_date is missing_contract:
            return False
        else:
            return True


    def get_all_contract_objects_for_instrument_code(self, *args, **kwargs):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def get_contract_object(self, *args, **kwargs):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def delete_contract_data(self, *args, **kwargs):
        raise NotImplementedError("IB is ready only")

    def is_contract_in_data(self, *args, **kwargs):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def add_contract_data(self, *args, **kwargs):
        raise NotImplementedError("IB is ready only")


    def get_min_tick_size_for_contract(self, contract_object):
        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date_str,
        )

        contract_object_with_ib_data = self.get_contract_object_with_IB_metadata(
            contract_object)
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

    def is_instrument_code_and_contract_date_okay_to_trade(
        self, instrument_code, contract_date
    ):
        ## WANT TO REMOVE ONCE HAVE INSTALLED FUTURESCONTRACT AS UNIVERSAL TRADEABLE OBJECT...
        ## ... INSTEAD HAVE CALL WITH CONTRACT OBJECT PULLED FROM TRADE
        contract_object = contract_from_code_and_id(instrument_code, contract_date)
        result = self.is_contract_okay_to_trade(contract_object)

        return result


    def less_than_one_hour_of_trading_leg_for_instrument_code_and_contract_date(
            self, instrument_code, contract_date):
        ## WANT TO REMOVE ONCE HAVE INSTALLED FUTURESCONTRACT AS UNIVERSAL TRADEABLE OBJECT...
        ## ... INSTEAD HAVE CALL WITH CONTRACT OBJECT PULLED FROM TRADE
        contract_object = contract_from_code_and_id(instrument_code, contract_date)
        result = self.less_than_one_hour_of_trading_leg_for_contract(
            contract_object)

        return result

    def is_contract_okay_to_trade(self, contract_object):
        trading_hours = self.get_trading_hours_for_contract(contract_object)
        trading_hours_checker = manyTradingStartAndEnd(trading_hours)

        return trading_hours_checker.okay_to_trade_now()



    def less_than_one_hour_of_trading_leg_for_contract(self, contract_object):
        trading_hours = self.get_trading_hours_for_contract(contract_object)
        trading_hours_checker = manyTradingStartAndEnd(trading_hours)

        return trading_hours_checker.less_than_one_hour_left()



    def get_trading_hours_for_instrument_code_and_contract_date(
        self, instrument_code, contract_date
    ):
        contract_object = contract_from_code_and_id(instrument_code, contract_date)
        result = self.get_trading_hours_for_contract(contract_object)

        return result


    def get_min_tick_size_for_instrument_code_and_contract_date(self, instrument_code, contract_date):
        contract_object = contract_from_code_and_id(instrument_code, contract_date)
        result = self.get_min_tick_size_for_contract(contract_object)

        return result

    def get_trading_hours_for_contract(self, contract_object):
        """

        :param contract_object:
        :return: list of paired date times
        """
        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date_str,
        )

        contract_object_with_ib_data = self.get_contract_object_with_IB_metadata(
            contract_object)
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

    def get_actual_expiry_date_for_contract(self, contract_object):
        """
        Get the actual expiry date of a contract from IB

        :param contract_object: type futuresContract
        :return: YYYYMMDD or None
        """
        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date_str,
        )

        contract_object_with_ib_data = self.get_contract_object_with_IB_metadata(
            contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.msg("Can't resolve contract so can't find expiry date")
            return missing_contract

        expiry_date = self.ibconnection.broker_get_contract_expiry_date(
            contract_object_with_ib_data
        )

        if expiry_date is missing_contract:
            new_log.msg("No IB expiry date found")
            return missing_contract
        else:
            expiry_date = expiryDate.from_str(
                expiry_date)

        return expiry_date

    def get_contract_object_with_IB_metadata(self, contract_object):

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

