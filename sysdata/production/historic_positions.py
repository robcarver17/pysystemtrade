from syscore.objects import success, arg_not_supplied
from sysobjects.contracts import futuresContract

from sysdata.production.generic_timed_storage import (
    timedEntry,
    listOfEntries,
    listOfEntriesData,
)
from sysdata.production.current_positions import (
    contractPosition,
    listOfContractPositions,
    instrumentStrategyPosition,
    listOfInstrumentStrategyPositions,
)
from syscore.objects import failure
import datetime


class historicPosition(timedEntry):
    """
    Position, could be for an instrument or a contract

    """

    def _setup_args_data(self):
        self._star_args = ["position"]  # compulsory args

    def _name_(self):
        return "Position"

    def _containing_data_class_name(self):
        return "sysdata.production.historic_positions.listPositions"


class listPositions(listOfEntries):
    """
    A list of positions
    """

    def _entry_class(self):
        return historicPosition


def any_positions_since_start_date(position_series, start_date, end_date):
    """
     Any positions held in a given date range

     Either:
     - position at start was non zero, and we didn't trade (return True)
     - position at start was zero and we did change our position (return True)
    - position at start was zero and we didn't trade (return False)

     :param position_series: pd.DataFrame with one column, position
     :param start_date: datetime
     :param end_date: datetime
     :return: bool
    """
    if len(position_series) == 0:
        return False
    positions_before_start = position_series[:start_date]
    if len(positions_before_start) == 0:
        position_at_start = 0
    else:
        position_at_start = positions_before_start.position.iloc[-1]
    positions_during = position_series[start_date:end_date]

    if position_at_start == 0 and len(positions_during) == 0:
        return False
    else:
        return True


class instrumentPositionData(listOfEntriesData):
    """
    Store and retrieve the instrument positions assigned to a particular strategy

    We store the type of list in the data
    """

    def _name(self):
        return "instrumentPositionData"

    def _data_class_name(self):
        return "sysdata.production.historic_positions.listPositions"

    def get_position_as_df_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        position_series = self._get_series_for_args_dict(
            dict(strategy_name=strategy_name, instrument_code=instrument_code)
        )
        df_object = position_series.as_pd_df()
        return df_object

    def get_current_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        current_position_entry = self._get_current_entry_for_args_dict(
            dict(strategy_name=strategy_name, instrument_code=instrument_code)
        )

        return current_position_entry

    def update_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code, position, date=arg_not_supplied
    ):
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        position_entry = historicPosition(position, date=date)
        try:
            self._update_entry_for_args_dict(
                position_entry,
                dict(
                    strategy_name=strategy_name,
                    instrument_code=instrument_code),
            )
        except Exception as e:
            self.log.warn(
                "Error %s when updating position for %s/%s with %s"
                % (str(e), strategy_name, instrument_code, str(position_entry))
            )
            return failure

    def get_list_of_strategies_and_instruments_with_positions(
        self, ignore_zero_positions=True
    ):
        list_of_args_dict = self._get_list_of_args_dict()
        strat_instr_tuples = []
        for arg_entry in list_of_args_dict:
            position = self.get_current_position_for_strategy_and_instrument(
                arg_entry["strategy_name"], arg_entry["instrument_code"]
            )
            if position == 0 and ignore_zero_positions:
                continue
            strat_instr_tuples.append(
                (arg_entry["strategy_name"], arg_entry["instrument_code"])
            )

        return strat_instr_tuples

    def get_list_of_instruments_for_strategy_with_position(
        self, strategy_name, ignore_zero_positions=True
    ):
        list_of_all_positions = (
            self.get_list_of_strategies_and_instruments_with_positions(
                ignore_zero_positions=ignore_zero_positions
            )
        )
        list_of_instruments = [
            position[1]
            for position in list_of_all_positions
            if position[0] == strategy_name
        ]

        return list_of_instruments

    def delete_last_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code, are_you_sure=False
    ):
        self._delete_last_entry_for_args_dict(
            dict(strategy_name=strategy_name, instrument_code=instrument_code),
            are_you_sure=are_you_sure,
        )

    def get_all_current_positions_as_list_with_instrument_objects(self):
        """
        Current positions are returned in a different class

        :return: listOfInstrumentStrategyPositions
        """

        all_positions_dict = self._get_list_of_args_dict()
        current_positions = []
        for dict_entry in all_positions_dict:
            instrument_code = dict_entry["instrument_code"]
            strategy_name = dict_entry["strategy_name"]
            position = self.get_current_position_for_strategy_and_instrument(
                strategy_name, instrument_code
            ).position
            if position == 0:
                continue
            position_object = instrumentStrategyPosition(
                position, strategy_name, instrument_code
            )
            current_positions.append(position_object)

        list_of_current_position_objects = listOfInstrumentStrategyPositions(
            current_positions
        )

        return list_of_current_position_objects

    def get_all_current_positions_as_df(self):
        return (
            self.get_all_current_positions_as_list_with_instrument_objects().as_pd_df())


class contractPositionData(listOfEntriesData):
    """
    Store and retrieve the instrument positions held in a particular instrument and contract
    These are *not* strategy specific. Strategies only know about instruments and don't care how their
       position is implemented.

    We store the type of list in the data
    """

    def _name(self):
        return "contractPositionData"

    def _data_class_name(self):
        return "sysdata.production.historic_positions.listPositions"

    def _keyname_given_contract_object(self, futures_contract_object):
        """
        We could do this using the .ident() method of the contract object, but this way we keep control inside this class

        This will also allow us to deal with intramarket 'contracts'

        :param futures_contract_object: futuresContract
        :return: str
        """

        return (futures_contract_object.instrument_code +
                "." + futures_contract_object.date_str)

    def _contract_tuple_given_keyname(self, keyname):
        """
        Extract the two parts of a keyname

        We keep control of how we represent stuff inside the class

        :param keyname: str
        :return: tuple instrument_code, contract_date
        """
        keyname_as_list = keyname.split(".")
        instrument_code, contract_date = tuple(keyname_as_list)

        return instrument_code, contract_date

    def get_position_as_df_for_instrument_and_contract_date(
        self, instrument_code, contract_date
    ):
        df_object = self._perform_method_for_instrument_and_contract_date(
            "get_position_as_df_for_contract_object", instrument_code, contract_date)

        return df_object

    def get_current_position_for_instrument_and_contract_date(
        self, instrument_code, contract_date
    ):
        position = self._perform_method_for_instrument_and_contract_date(
            "get_current_position_for_contract_object", instrument_code, contract_date)

        return position

    def update_position_for_instrument_and_contract_date(
        self, instrument_code, contract_date, position, date=arg_not_supplied
    ):
        ans = self._perform_method_for_instrument_and_contract_date(
            "update_position_for_contract_object",
            instrument_code,
            contract_date,
            position,
            date=date,
        )
        return ans

    def delete_last_position_for_instrument_and_contract_date(
        self, instrument_code, contract_date, are_you_sure=False
    ):
        ans = self._perform_method_for_instrument_and_contract_date(
            "delete_last_position_for_contract_object",
            instrument_code,
            contract_date,
            are_you_sure=are_you_sure,
        )
        return ans

    def _perform_method_for_instrument_and_contract_date(
        self, method_name, instrument_code, contract_date, *args, **kwargs
    ):
        contract_object = futuresContract(instrument_code, contract_date)
        method = getattr(self, method_name)
        return method(contract_object, *args, **kwargs)

    def get_position_as_df_for_contract_object(self, contract_object):
        contractid = self._keyname_given_contract_object(contract_object)
        position_series = self._get_series_for_args_dict(
            dict(contractid=contractid))
        df_object = position_series.as_pd_df()

        return df_object

    def get_current_position_for_contract_object(self, contract_object):
        contractid = self._keyname_given_contract_object(contract_object)
        current_position_entry = self._get_current_entry_for_args_dict(
            dict(contractid=contractid)
        )
        return current_position_entry

    def update_position_for_contract_object(
        self, contract_object, position, date=arg_not_supplied
    ):
        contractid = self._keyname_given_contract_object(contract_object)
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        position_entry = historicPosition(position, date=date)
        try:
            self._update_entry_for_args_dict(
                position_entry, dict(contractid=contractid)
            )
        except Exception as e:
            self.log.warn(
                "Error %s when updating position for %s with %s"
                % (str(e), contractid, str(position_entry))
            )
            return failure
        return success

    def delete_last_position_for_contract_object(
        self, contract_object, are_you_sure=False
    ):
        contractid = self._keyname_given_contract_object(contract_object)
        self._delete_last_entry_for_args_dict(
            dict(contractid=contractid), are_you_sure=are_you_sure
        )
        return success

    def get_list_of_instruments_with_current_positions(self):
        all_current_positions = self.get_all_current_positions_as_list_with_contract_objects()
        instrument_list = [position.instrument_code for position in all_current_positions]
        instrument_list = list(set(instrument_list))

        return instrument_list

    def get_list_of_instruments_with_any_position(self):
        all_positions_dict = self._get_list_of_args_dict()
        instrument_list = [
            self._contract_tuple_given_keyname(entry["contractid"])[0]
            for entry in all_positions_dict
        ]

        return list(set(instrument_list))

    def get_list_of_contracts_with_any_position_for_instrument(
            self, instrument_code):
        all_positions_dict = self._get_list_of_args_dict()
        contract_list = [
            self._contract_tuple_given_keyname(entry["contractid"])[1]
            for entry in all_positions_dict
            if self._contract_tuple_given_keyname(entry["contractid"])[0]
            == instrument_code
        ]

        return list(set(contract_list))

    def get_list_of_contracts_with_any_position_for_instrument_in_date_range(
        self, instrument_code, start_date, end_date
    ):
        list_of_contracts = self.get_list_of_contracts_with_any_position_for_instrument(
            instrument_code)

        contract_positions_dict = dict(
            [
                (
                    contract_date,
                    self.get_position_as_df_for_instrument_and_contract_date(
                        instrument_code, contract_date
                    ),
                )
                for contract_date in list_of_contracts
            ]
        )

        list_of_contracts = [
            contract_date
            for contract_date in list_of_contracts
            if any_positions_since_start_date(
                contract_positions_dict[contract_date], start_date, end_date
            )
        ]

        return list_of_contracts

    def get_all_current_positions_as_list_with_contract_objects(self):
        all_positions_dict = self._get_list_of_args_dict()
        current_positions = []
        for dict_entry in all_positions_dict:
            contractid = self._contract_tuple_given_keyname(
                dict_entry["contractid"])
            instrument_code = contractid[0]
            contract_date = contractid[1]
            position = self.get_current_position_for_instrument_and_contract_date(
                instrument_code, contract_date).position
            if position == 0:
                continue
            position_object = contractPosition(
                position, instrument_code, contract_date)
            current_positions.append(position_object)

        list_of_current_positions = listOfContractPositions(current_positions)

        return list_of_current_positions

    def get_all_current_positions_as_df(self):
        return self.get_all_current_positions_as_list_with_contract_objects().as_pd_df()
