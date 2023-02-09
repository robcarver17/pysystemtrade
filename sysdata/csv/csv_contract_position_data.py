import pandas as pd
from sysdata.production.historic_positions import contractPositionData
from sysobjects.contracts import futuresContract
from syscore.fileutils import resolve_path_and_filename_for_package
from syscore.constants import arg_not_supplied
from syslogdiag.log_to_screen import logtoscreen

DATE_INDEX_NAME = "DATETIME"


class csvContractPositionData(contractPositionData):
    """

    Class for contract_positions write to / read from csv
    """

    def __init__(
        self, datapath=arg_not_supplied, log=logtoscreen("csvContractPositionData")
    ):

        super().__init__(log=log)

        if datapath is None:
            raise Exception("Need to provide datapath")

        self._datapath = datapath

    def __repr__(self):
        return "csvContractPositionData accessing %s" % self._datapath

    def write_position_df_for_contract(
        self, contract: futuresContract, position_df: pd.DataFrame
    ):
        filename = self._filename_given_contract(contract)
        position_df.to_csv(filename, index_label=DATE_INDEX_NAME)

    def _filename_given_contract(self, contract: futuresContract):
        return resolve_path_and_filename_for_package(
            self._datapath, "%s_%s.csv" % (contract.instrument_code, contract.date_str)
        )
