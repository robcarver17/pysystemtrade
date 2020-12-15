import pandas as pd
from sysdata.production.historic_positions import strategyPositionData
from syscore.fileutils import get_filename_for_package
from syscore.objects import arg_not_supplied
from syslogdiag.log import logtoscreen
from sysobjects.production.strategy import instrumentStrategy

DATE_INDEX_NAME = "DATETIME"


class csvStrategyPositionData(strategyPositionData):
    """

    Class for contract_positions write to / read from csv
    """

    def __init__(self, datapath=arg_not_supplied,
                 log=logtoscreen("csvStrategyPositionData")):

        super().__init__(log=log)

        if datapath is None:
            raise Exception("Need to provide datapath")

        self._datapath = datapath

    def __repr__(self):
        return "csvStrategyPositionData accessing %s" % self._datapath

    def write_position_df_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy, position_df: pd.DataFrame
    ):
        filename = self._filename_given_instrument_strategy(
            instrument_strategy
        )
        position_df.to_csv(filename, index_label=DATE_INDEX_NAME)


    def _filename_given_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ):
        return get_filename_for_package(
            self._datapath, "%s_%s.csv" % (instrument_strategy.strategy_name, instrument_strategy.instrument_code)
        )