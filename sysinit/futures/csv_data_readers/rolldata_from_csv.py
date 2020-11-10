from syscore.fileutils import get_filename_for_package
from sysdata.futures.rolls import rollParametersData
from sysobjects.rolls import rollParameters

import pandas as pd

ROLLS_CONFIG_FILE = "sysinit.futures.config.rollconfig.csv"


class initCsvFuturesRollData(rollParametersData):
    """
    Get data about instruments from a special configuration used for initialising the system

    """

    def __init__(self, config_file=ROLLS_CONFIG_FILE):

        super().__init__()

        self._config_file = get_filename_for_package(config_file)
        self.name = "Roll data for initialising system config"

    def _get_config_information(self):
        """
        Get configuration information

        :return: dict of config information
        """

        try:
            config_data = pd.read_csv(self._config_file)
        except BaseException:
            raise Exception("Can't read file %s" % self._config_file)

        try:
            config_data.index = config_data.Instrument
            config_data.drop("Instrument", 1, inplace=True)

        except BaseException:
            raise Exception("Badly configured file %s" % (self._config_file))

        return config_data

    def __repr__(self):
        return self.name

    def get_list_of_instruments(self):
        return list(self._get_config_information().index)

    def _get_roll_parameters_without_checking(self, instrument_code):
        config_for_this_instrument = self._get_config_information(
        ).loc[instrument_code]
        roll_parameters_object = rollParameters(
            hold_rollcycle=config_for_this_instrument.HoldRollCycle,
            roll_offset_day=config_for_this_instrument.RollOffsetDays,
            carry_offset=config_for_this_instrument.CarryOffset,
            priced_rollcycle=config_for_this_instrument.PricedRollCycle,
            approx_expiry_offset=config_for_this_instrument.ExpiryOffset,
        )

        return roll_parameters_object
