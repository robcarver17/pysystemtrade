import datetime
from typing import List

import pandas as pd

from syscore.constants import arg_not_supplied
from syscore.exceptions import missingData
from sysdata.base_data import baseData
from sysobjects.contracts import futuresContract, listOfFuturesContracts
from sysobjects.production.positions import listOfContractPositions, contractPosition


class contractPositionData(baseData):
    """
    Store and retrieve the instrument positions held in a particular instrument and contract
    These are *not* strategy specific. Strategies only know about instruments and don't care how their
       position is implemented.

    """

    def __repr__(self):
        return "contractPositionData object"

    def get_current_position_for_contract_object(
        self, contract_object: futuresContract
    ):
        try:
            position_series = self.get_position_as_series_for_contract_object(
                contract_object
            )
        except missingData:
            return 0.0

        if len(position_series) == 0:
            return 0.0

        return position_series[-1]

    def update_position_for_contract_object(
        self,
        contract_object: futuresContract,
        position: int,
        date: datetime.datetime = arg_not_supplied,
    ):
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        self._update_position_for_contract_object_with_date_supplied(
            contract_object=contract_object, position=position, date_index=date
        )

    def delete_last_position_for_contract_object(
        self, contract_object: futuresContract, are_you_sure=False
    ):
        if are_you_sure:
            self._delete_last_position_for_contract_object_without_checking(
                contract_object=contract_object
            )

    def get_list_of_instruments_with_any_position(self):
        list_of_contracts = self.get_list_of_contracts()
        return list_of_contracts.unique_list_of_instrument_codes()

    def get_list_of_instruments_with_current_positions(self) -> list:
        list_of_current_positions = (
            self.get_all_current_positions_as_list_with_contract_objects()
        )
        instrument_list = list_of_current_positions.unique_list_of_instruments()

        return instrument_list

    def get_list_of_contract_date_str_with_any_position_for_instrument(
        self, instrument_code: str
    ) -> List[str]:
        ## doesn't exclude zeros
        list_of_contracts = self.get_list_of_contracts_for_instrument_code(
            instrument_code
        )
        list_of_date_str = list_of_contracts.list_of_dates()

        return list_of_date_str

    def get_list_of_contract_date_str_with_any_position_for_instrument_in_date_range(
        self,
        instrument_code,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> List[str]:

        list_of_contracts = self.get_list_of_contracts_for_instrument_code(
            instrument_code
        )
        list_of_contracts_with_position = [
            contract
            for contract in list_of_contracts
            if self.any_positions_for_contract_in_date_range(
                contract, start_date, end_date
            )
        ]

        list_of_date_str_with_position = [
            contract.date_str for contract in list_of_contracts_with_position
        ]

        return list_of_date_str_with_position

    def get_all_current_positions_as_df(self) -> pd.DataFrame:
        # excludes zeros
        return self.get_all_current_positions_as_list_with_contract_objects().as_pd_df()

    def get_all_current_positions_as_list_with_contract_objects(
        self,
    ) -> listOfContractPositions:
        # excludes zeros

        list_of_contracts = self.get_list_of_contracts()  ## includes zeros
        current_positions = []
        for contract in list_of_contracts:
            position = self.get_current_position_for_contract_object(contract)
            if position == 0:
                continue

            position_object = contractPosition(position, contract)
            current_positions.append(position_object)

        list_of_current_positions = listOfContractPositions(current_positions)

        return list_of_current_positions

    def get_list_of_contracts_for_instrument_code(
        self, instrument_code: str
    ) -> listOfFuturesContracts:
        ## doesn't remove zero positions
        list_of_contracts = self.get_list_of_contracts()
        list_of_contracts_for_code = (
            list_of_contracts.contracts_in_list_for_instrument_code(instrument_code)
        )

        return list_of_contracts_for_code

    def any_positions_for_contract_in_date_range(
        self,
        contract: futuresContract,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> bool:

        try:
            series_of_positions = self.get_position_as_series_for_contract_object(
                contract
            )
        except missingData:
            return False
        any_positions = any_positions_since_start_date(
            series_of_positions, start_date, end_date
        )

        return any_positions

    def any_current_position_for_contract(self, contract: futuresContract) -> bool:
        position = self.get_current_position_for_contract_object(contract)
        if position == 0:
            return False
        else:
            return True

    def _update_position_for_contract_object_with_date_supplied(
        self,
        contract_object: futuresContract,
        position: int,
        date_index: datetime.datetime,
    ):
        raise NotImplementedError

    def get_position_as_series_for_contract_object(
        self, contract_object: futuresContract
    ) -> pd.Series:
        raise NotImplementedError

    def _delete_last_position_for_contract_object_without_checking(
        self, contract_object: futuresContract
    ):
        raise NotImplementedError

    def get_list_of_contracts(self) -> listOfFuturesContracts:
        ## doesn't remove zero positions
        raise NotImplementedError


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
