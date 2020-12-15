import pandas as pd
from syscore.objects import arg_not_supplied, missing_data
from sysobjects.contracts import futuresContract

from sysdata.production.timed_storage import (
    listOfEntriesData,
)
from sysobjects.production.timed_storage import timedEntry, listOfEntries
from sysobjects.production.positions import instrumentStrategyPosition, contractPosition, \
    listOfInstrumentStrategyPositions, listOfContractPositions
from sysobjects.production.strategy import instrumentStrategy, listOfInstrumentStrategies
import datetime

class historicPosition(timedEntry):
    """
    Position, could be for an instrument or a contract

    """

    @property
    def required_argument_names(self) -> list:
        return ["position"]  # compulsory args

    @property
    def _name_(self):
        return "Position"

    @property
    def containing_data_class_name(self):
        return "sysdata.production.historic_positions.listPositions"


class listPositions(listOfEntries):
    """
    A list of positions
    """

    def _entry_class(self):
        return historicPosition



class strategyPositionData(listOfEntriesData):
    """
    Store and retrieve the instrument positions assigned to a particular strategy

    We store the type of list in the data
    """

    def _data_class_name(self):
        return "sysdata.production.historic_positions.listPositions"

    def get_position_as_df_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy
           ) -> pd.DataFrame:

        position_series = self._get_series_for_args_dict(
            instrument_strategy.as_dict()
        )
        df_object = position_series.as_pd_df()
        return df_object

    def get_current_position_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy
         ) -> int:

        position_entry = self.get_current_position_entry_for_instrument_strategy_object(instrument_strategy)
        if position_entry is missing_data:
            return 0
        else:
            # ignore warning it's because we dynamically assign attributes
            return position_entry.position

    def get_current_position_entry_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy
         ) -> historicPosition:

        current_position_entry = self._get_current_entry_for_args_dict(
            instrument_strategy.as_dict()
        )

        return current_position_entry

    def update_position_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy, position: int,
            date: datetime.datetime=arg_not_supplied
    ):
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        position_entry = historicPosition(position, date=date)
        args_dict = instrument_strategy.as_dict()
        try:
            self._update_entry_for_args_dict(
                position_entry,
                args_dict
            )
        except Exception as e:
            self.log.critical(
                "Error %s when updating position for %s with %s"
                % (str(e), str(instrument_strategy), str(position_entry))
            )


    def get_list_of_strategies_and_instruments_with_positions(
        self, ignore_zero_positions: bool=True
    ) -> listOfInstrumentStrategies:

        list_of_instrument_strategies = self.get_list_of_instrument_strategies()

        if ignore_zero_positions:
            list_of_instrument_strategies = [instrument_strategy for
                                             instrument_strategy in list_of_instrument_strategies
                if self.get_current_position_for_instrument_strategy_object(instrument_strategy)!=0]

            list_of_instrument_strategies = listOfInstrumentStrategies(list_of_instrument_strategies)

        return list_of_instrument_strategies

    def get_list_of_instruments_for_strategy_with_position(
        self, strategy_name, ignore_zero_positions=True
    ) -> list:

        list_of_instrument_strategies = (
            self.get_list_of_strategies_and_instruments_with_positions(
                ignore_zero_positions=ignore_zero_positions
            )
        )
        list_of_instruments = list_of_instrument_strategies.get_list_of_instruments_for_strategy(strategy_name)

        return list_of_instruments

    def get_list_of_strategies_with_positions(self) -> list:
        list_of_instrument_strategies = \
            self.get_list_of_strategies_and_instruments_with_positions(
                ignore_zero_positions=True
            )
        list_of_strategies = list_of_instrument_strategies.get_list_of_strategies()

        return list_of_strategies


    def delete_last_position_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy, are_you_sure: bool=False
    ):
        args_dict = instrument_strategy.as_dict()
        self._delete_last_entry_for_args_dict(
            args_dict,
            are_you_sure=are_you_sure
        )

    def get_all_current_positions_as_list_with_instrument_objects(self) -> listOfInstrumentStrategyPositions:
        """
        Current positions are returned in a different class

        :return: listOfInstrumentStrategyPositions
        """

        list_of_instrument_strategies = self.get_list_of_instrument_strategies()
        current_positions = []
        for instrument_strategy in list_of_instrument_strategies:
            position = self.get_current_position_for_instrument_strategy_object(instrument_strategy)
            if position==0:
                continue
            position_object = instrumentStrategyPosition(
                position, instrument_strategy
            )
            current_positions.append(position_object)

        list_of_current_position_objects = listOfInstrumentStrategyPositions(
            current_positions
        )

        return list_of_current_position_objects

    def get_all_current_positions_as_df(self):
        return (
            self.get_all_current_positions_as_list_with_instrument_objects().as_pd_df())

    def get_list_of_instrument_strategies(self) -> listOfInstrumentStrategies:
        all_positions_dict = self._get_list_of_args_dict()
        list_of_instrument_strategies = []
        for dict_entry in all_positions_dict:
            instrument_strategy = instrumentStrategy.from_dict(dict_entry)
            list_of_instrument_strategies.append(instrument_strategy)

        list_of_instrument_strategies = listOfInstrumentStrategies(list_of_instrument_strategies)

        return list_of_instrument_strategies

CONTRACTID_KEY = 'contractid'

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

    def _keyname_given_contract_object(self, futures_contract_object: futuresContract):
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

    # FIXME STILL USE?
    def get_position_as_df_for_instrument_and_contract_date(
        self, instrument_code, contract_date
    ):
        df_object = self._perform_method_for_instrument_and_contract_date(
            "get_position_as_df_for_contract_object", instrument_code, contract_date)

        return df_object

    # FIXME STILL USE?
    def get_current_position_for_instrument_and_contract_date(
        self, instrument_code, contract_date
    ):
        position = self._perform_method_for_instrument_and_contract_date(
            "get_current_position_for_contract_object", instrument_code, contract_date)


        return position

    # FIXME STILL USE?
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

    # FIXME STILL USE?
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
            {CONTRACTID_KEY: contractid})
        df_object = position_series.as_pd_df()

        return df_object

    def get_current_position_for_contract_object(self, contract_object):
        position_entry = self.get_current_position_entry_for_contract_object(contract_object)
        if position_entry is missing_data:
            return 0.0

        return position_entry.position

    def get_current_position_entry_for_contract_object(self, contract_object):
        contractid = self._keyname_given_contract_object(contract_object)
        current_position_entry = self._get_current_entry_for_args_dict(
            {CONTRACTID_KEY: contractid}
        )
        return current_position_entry

    def update_position_for_contract_object(
        self, contract_object, position, date=arg_not_supplied
    ):
        contractid = self._keyname_given_contract_object(contract_object)
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        position_entry = historicPosition(position, date=date)
        self._update_entry_for_args_dict(
            position_entry, {CONTRACTID_KEY: contractid}
        )

    def delete_last_position_for_contract_object(
        self, contract_object, are_you_sure=False
    ):
        contractid = self._keyname_given_contract_object(contract_object)
        self._delete_last_entry_for_args_dict(
            {CONTRACTID_KEY: contractid}, are_you_sure=are_you_sure
        )

    def get_list_of_instruments_with_current_positions(self):
        all_current_positions = self.get_all_current_positions_as_list_with_contract_objects()
        instrument_list = [position.instrument_code for position in all_current_positions]
        instrument_list = list(set(instrument_list))

        return instrument_list

    def get_list_of_instruments_with_any_position(self):
        all_positions_dict = self._get_list_of_args_dict()
        instrument_list = [
            self._contract_tuple_given_keyname(entry[CONTRACTID_KEY])[0]
            for entry in all_positions_dict
        ]

        return list(set(instrument_list))

    def get_list_of_contracts_with_any_position_for_instrument(
            self, instrument_code):
        all_positions_dict = self._get_list_of_args_dict()
        contract_list = [
            self._contract_tuple_given_keyname(entry[CONTRACTID_KEY])[1]
            for entry in all_positions_dict
            if self._contract_tuple_given_keyname(entry[CONTRACTID_KEY])[0]
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
                dict_entry[CONTRACTID_KEY])
            instrument_code = contractid[0]
            contract_date = contractid[1]
            position = self.get_current_position_for_instrument_and_contract_date(
                instrument_code, contract_date)
            if position == 0:
                continue
            position_object = contractPosition(
                position, instrument_code, contract_date)
            current_positions.append(position_object)

        list_of_current_positions = listOfContractPositions(current_positions)

        return list_of_current_positions

    def get_all_current_positions_as_df(self):
        return self.get_all_current_positions_as_list_with_contract_objects().as_pd_df()


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

