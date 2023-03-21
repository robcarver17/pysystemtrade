import datetime
import pandas as pd

from sysobjects.contracts import futuresContract, listOfFuturesContracts
from sysdata.arctic.arctic_connection import arcticData
from sysdata.production.historic_contract_positions import contractPositionData

from syscore.exceptions import missingData

from syslogdiag.log_to_screen import logtoscreen

CONTRACT_POSITION_COLLECTION = "contract_positions"


class arcticContractPositionData(contractPositionData):
    def __init__(self, mongo_db=None, log=logtoscreen("arcticContractPositionData")):

        super().__init__(log=log)

        self._arctic = arcticData(CONTRACT_POSITION_COLLECTION, mongo_db=mongo_db)

    def __repr__(self):
        return repr(self._arctic)

    @property
    def arctic(self):
        return self._arctic

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

    def _write_updated_position_series_for_contract_object(
        self, contract_object: futuresContract, updated_series: pd.Series
    ):
        ## overwrites what is there without checking
        ident = contract_object.key
        updated_data_as_df = pd.DataFrame(updated_series)
        updated_data_as_df.columns = ["position"]

        self.arctic.write(ident=ident, data=updated_data_as_df)

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

    def _delete_position_series_for_contract_object_without_checking(
        self, contract_object: futuresContract
    ):
        ident = contract_object.key
        self.arctic.delete(ident)

    def get_position_as_series_for_contract_object(
        self, contract_object: futuresContract
    ) -> pd.Series:
        keyname = contract_object.key
        try:
            pd_df = self.arctic.read(keyname)
        except:
            raise missingData

        return pd_df.iloc[:, 0]

    def get_list_of_contracts(self) -> listOfFuturesContracts:
        ## doesn't remove zero positions
        list_of_keys = self.arctic.get_keynames()
        list_of_futures_contract = [
            futuresContract.from_key(key) for key in list_of_keys
        ]

        return listOfFuturesContracts(list_of_futures_contract)
