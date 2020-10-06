from sysdata.production.optimal_positions import optimalPositionData
from syscore.fileutils import get_filename_for_package
from syscore.objects import arg_not_supplied
from syslogdiag.log import logtoscreen

DATE_INDEX_NAME = "DATETIME"


class csvOptimalPositionData(optimalPositionData):
    """

    Class for contract_positions write to / read from csv
    """

    def __init__(self, datapath=arg_not_supplied,
                 log=logtoscreen("csvOptimalPositionData")):

        super().__init__(log=log)

        if datapath is None:
            raise Exception("Need to provide datapath")

        self._datapath = datapath

    def __repr__(self):
        return "csvOptimalPositionData accessing %s" % self._datapath

    def write_position_df_for_instrument_strategy(
        self, instrument_code, strategy_code, position_df
    ):
        filename = self._filename_given_instrument_code_and_strategy(
            instrument_code, strategy_code
        )
        position_df.to_csv(filename, index_label=DATE_INDEX_NAME)

    def _filename_given_instrument_code_and_strategy(
        self, instrument_code, strategy_code
    ):
        return get_filename_for_package(
            self._datapath, "%s_%s.csv" % (strategy_code, instrument_code)
        )
