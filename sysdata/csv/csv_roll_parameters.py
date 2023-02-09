from syscore.constants import arg_not_supplied
from syscore.fileutils import resolve_path_and_filename_for_package
from sysdata.futures.rolls_parameters import rollParametersData
from sysobjects.rolls import rollParameters
from syslogdiag.log_to_screen import logtoscreen

import pandas as pd

ROLLS_DATAPATH = "data.futures.csvconfig"
ROLLS_CONFIG_FILE = "rollconfig.csv"


class csvRollParametersData(rollParametersData):
    """
    Get data about instruments from a special configuration used for initialising the system

    """

    def __init__(
        self, log=logtoscreen("csvRollParametersData"), datapath=arg_not_supplied
    ):

        super().__init__(log=log)
        if datapath is arg_not_supplied:
            datapath = ROLLS_DATAPATH
        config_file = resolve_path_and_filename_for_package(datapath, ROLLS_CONFIG_FILE)

        self._config_file = config_file

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
            config_data.drop(labels="Instrument", axis=1, inplace=True)

        except BaseException:
            raise Exception("Badly configured file %s" % (self._config_file))

        return config_data

    @property
    def config_file(self):
        return self._config_file

    def __repr__(self):
        return "Roll data for initialising system config"

    def get_list_of_instruments(self) -> list:
        return list(self._get_config_information().index)

    def _get_roll_parameters_without_checking(
        self, instrument_code: str
    ) -> rollParameters:
        config_for_this_instrument = self._get_config_information().loc[instrument_code]
        roll_parameters_object = rollParameters(
            hold_rollcycle=config_for_this_instrument.HoldRollCycle,
            roll_offset_day=config_for_this_instrument.RollOffsetDays,
            carry_offset=config_for_this_instrument.CarryOffset,
            priced_rollcycle=config_for_this_instrument.PricedRollCycle,
            approx_expiry_offset=config_for_this_instrument.ExpiryOffset,
        )

        return roll_parameters_object

    def _delete_roll_parameters_data_without_any_warning_be_careful(
        self, instrument_code: str
    ):
        raise NotImplementedError("csv is read only")

    def _add_roll_parameters_without_checking_for_existing_entry(
        self, instrument_code: str, roll_parameters: rollParameters
    ):
        raise NotImplementedError("csv is read only")

    def write_all_roll_parameters_data(self, roll_parameters_df: pd.DataFrame):
        roll_parameters_df_to_write = pd.DataFrame(
            dict(
                HoldRollCycle=roll_parameters_df.hold_rollcycle,
                RollOffsetDays=roll_parameters_df.roll_offset_day,
                CarryOffset=roll_parameters_df.carry_offset,
                PricedRollCycle=roll_parameters_df.priced_rollcycle,
                ExpiryOffset=roll_parameters_df.approx_expiry_offset,
            )
        )

        roll_parameters_df_to_write.to_csv(self._config_file, index_label="Instrument")
