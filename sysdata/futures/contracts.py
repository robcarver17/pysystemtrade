USE_CHILD_CLASS_ERROR = "You need to use a child class of futuresContractData"

class ContractNotFound(Exception):
    pass

from sysdata.data import baseData
from sysobjects.contracts import listOfFuturesContracts, contract_from_code_and_id
from sysdata.futures.trading_hours import manyTradingStartAndEnd

class futuresContractData(baseData):
    """
    Read and write data class to get futures contract data

    We'd inherit from this class for a specific implementation

    We store instrument code, and contract date data (date, expiry, roll cycle)

    If you want more information about a given instrument you have to read it in using futuresInstrumentData
    """

    def __repr__(self):
        return "Individual futures contract data - DO NOT USE"

    def get_list_of_contract_dates_for_instrument_code(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_all_contract_objects_for_instrument_code(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_contract_object(self, instrument_code, contract_id):
        if self.is_contract_in_data(instrument_code, contract_id):
            return self._get_contract_data_without_checking(
                instrument_code, contract_id
            )
        else:
            raise ContractNotFound("Contract %s/%s not found" % (instrument_code, contract_id))

    def _get_contract_data_without_checking(
            self, instrument_code, contract_date):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def __getitem__(self, key_tuple):
        (instrument_code, contract_date) = key_tuple
        return self.get_contract_object(instrument_code, contract_date)

    def delete_contract_data(
            self,
            instrument_code,
            contract_date,
            are_you_sure=False):
        self.log.label(
            instrument_code=instrument_code,
            contract_date=contract_date)
        if are_you_sure:
            if self.is_contract_in_data(instrument_code, contract_date):
                self._delete_contract_data_without_any_warning_be_careful(
                    instrument_code, contract_date
                )
                self.log.terse(
                    "Deleted contract %s/%s" % (instrument_code, contract_date)
                )
            else:
                # doesn't exist anyway
                self.log.warn("Tried to delete non existent contract")
        else:
            self.log.error(
                "You need to call delete_contract_data with a flag to be sure"
            )

    def _delete_contract_data_without_any_warning_be_careful(
        self, instrument_code, contract_date
    ):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def delete_all_contracts_for_instrument(
        self, instrument_code, areyoureallysure=False
    ):
        if not areyoureallysure:
            raise Exception(
                "You have to be sure to delete all contracts for an instrument!"
            )

        list_of_dates = self.get_list_of_contract_dates_for_instrument_code(
            instrument_code
        )
        for contract_date in list_of_dates:
            self.delete_contract_data(
                instrument_code, contract_date, are_you_sure=True)

    def is_contract_in_data(self, instrument_code, contract_date):
        raise NotImplementedError

    def add_contract_data(self, contract_object, ignore_duplication=False):

        instrument_code = contract_object.instrument_code
        contract_date = contract_object.date

        self.log.label(
            instrument_code=instrument_code,
            contract_date=contract_date)

        if self.is_contract_in_data(instrument_code, contract_date):
            if ignore_duplication:
                pass
            else:
                self.log.warn(
                    "There is already %s/%s in the data, you have to delete it first" %
                    (instrument_code, contract_date))
                return None

        self._add_contract_object_without_checking_for_existing_entry(
            contract_object)
        self.log.terse(
            "Added contract %s %s" %
            (instrument_code, contract_date))

    def _add_contract_object_without_checking_for_existing_entry(
            self, contract_object):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_actual_expiry_date_for_contract(self, contract_object):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

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
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_min_tick_size_for_contract(self, contract_object):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)