from sysdata.production.historic_positions import contractPositionData
from sysobjects.contracts import futuresContract
from syscore.fileutils import get_filename_for_package
from syscore.objects import arg_not_supplied
from syslogdiag.log import logtoscreen

DATE_INDEX_NAME = "DATETIME"


class csvContractPositionData(contractPositionData):
    """

    Class for contract_positions write to / read from csv
    """

    def __init__(self, datapath=arg_not_supplied,
                 log=logtoscreen("csvContractPositionData")):

        super().__init__(log=log)

        if datapath is None:
            raise Exception("Need to provide datapath")

        self._datapath = datapath

    def __repr__(self):
        return "csvContractPositionData accessing %s" % self._datapath

    def write_position_df_for_instrument_and_contract_date(
        self, instrument_code, contract_date, position_df
    ):
        filename = self._filename_given_instrument_code_and_contract_date(
            instrument_code, contract_date
        )
        position_df.to_csv(filename, index_label=DATE_INDEX_NAME)

    def _filename_given_instrument_code_and_contract_date(
        self, instrument_code, contract_date
    ):
        contract_object = futuresContract(instrument_code, contract_date)
        return get_filename_for_package(
            self._datapath, "%s_%s.csv" %
            (instrument_code, contract_object.date_str))
