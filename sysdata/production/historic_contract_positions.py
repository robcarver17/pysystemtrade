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

    def _update_position_for_contract_object_with_date_supplied(
        self,
        contract_object: futuresContract,
        position: int,
        date_index: datetime.datetime,
    ):
        new_position_series = pd.Series([position], index=[date_index])

        try:
            current_series = self.get_position_as_series_for_contract_object(
                contract_object
            )
            self._update_position_for_contract_object_with_date_and_existing_data(
                contract_object=contract_object,
                current_series=current_series,
                new_position_series=new_position_series,
            )
        except missingData:
            ## no existing data
            ## no need to update, just write the new series
            self._write_updated_position_series_for_contract_object(
                contract_object=contract_object,
                updated_series=new_position_series,
            )

    def _update_position_for_contract_object_with_date_and_existing_data(
        self,
        contract_object: futuresContract,
        current_series: pd.Series,
        new_position_series: pd.Series,
    ):

        try:
            assert new_position_series.index[0] > current_series.index[-1]
        except:
            error_msg = "Adding a position which is older than the last position!"
            self.log.critical(error_msg)
            raise Exception(error_msg)

        updated_series = current_series.append(new_position_series)
        self._write_updated_position_series_for_contract_object(
            contract_object=contract_object, updated_series=updated_series
        )

    def _delete_last_position_for_contract_object_without_checking(
        self, contract_object: futuresContract
    ):
        try:
            current_series = self.get_position_as_series_for_contract_object(
                contract_object
            )
            self._delete_last_position_for_contract_object_without_checking_with_current_data(
                contract_object=contract_object, current_series=current_series
            )
        except missingData:
            ## no existing data can't delete
            self.log.warn(
                "Can't delete last position for %s, as none present"
                % str(contract_object)
            )

    def _delete_last_position_for_contract_object_without_checking_with_current_data(
        self, contract_object: futuresContract, current_series: pd.Series
    ):
        updated_series = current_series.drop(current_series.index[-1])
        if len(updated_series) == 0:
            self._delete_position_series_for_contract_object_without_checking(
                contract_object
            )
        else:
            self._write_updated_position_series_for_contract_object(
                contract_object=contract_object, updated_series=updated_series
            )

    def any_current_position_for_contract(self, contract: futuresContract) -> bool:
        position = self.get_current_position_for_contract_object(contract)
        if position == 0:
            return False
        else:
            return True

    def overwrite_position_series_for_contract_object_without_checking(
        self, contract_object: futuresContract, updated_series: pd.Series
    ):
        self._write_updated_position_series_for_contract_object(
            contract_object=contract_object, updated_series=updated_series
        )

    def _write_updated_position_series_for_contract_object(
        self, contract_object: futuresContract, updated_series: pd.Series
    ):
        raise NotImplementedError

    def _delete_position_series_for_contract_object_without_checking(
        self, contract_object: futuresContract
    ):
        raise NotImplementedError

    def get_position_as_series_for_contract_object(
        self, contract_object: futuresContract
    ) -> pd.Series:
        raise NotImplementedError

    def get_list_of_contracts(self) -> listOfFuturesContracts:
        ## doesn't remove zero positions
        raise NotImplementedError


def any_positions_since_start_date(
    position_series: pd.Series,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
) -> bool:
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
    no_positions_in_series = len(position_series) == 0
    if no_positions_in_series:
        return False

    positions_during = position_series[start_date:end_date]
    position_at_start = _infer_position_at_start(
        position_series=position_series, start_date=start_date
    )
    no_initial_position = position_at_start == 0
    no_trading_done_in_period = len(positions_during) == 0

    if no_trading_done_in_period and no_initial_position:
        return False

    return True


def _infer_position_at_start(
    position_series: pd.Series, start_date: datetime.datetime
) -> int:
    positions_before_start = position_series[:start_date]
    no_positions_before_start = len(positions_before_start) == 0

    if no_positions_before_start:
        position_at_start = 0
    else:
        last_position_before_start = positions_before_start[-1]
        position_at_start = last_position_before_start

    return position_at_start
