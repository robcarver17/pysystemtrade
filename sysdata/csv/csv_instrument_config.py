from syscore.fileutils import get_filename_for_package
from sysdata.futures.instruments import futuresInstrumentData, futuresInstrument
import pandas as pd

INSTRUMENT_CONFIG_PATH = "data.futures.csvconfig"
CONFIG_FILE_NAME = "instrumentconfig.csv"

class csvFuturesInstrumentData(futuresInstrumentData):
    """
    Get data about instruments from a special configuration used for initialising the system

    """
    def __init__(self, config_path = INSTRUMENT_CONFIG_PATH):

        super().__init__()

        if config_path is None:
            config_path = INSTRUMENT_CONFIG_PATH

        self._config_file = get_filename_for_package(config_path, CONFIG_FILE_NAME)
        self.name = "Instruments data from %s" % self._config_file

    def get_all_instrument_data(self):
        """
        Get configuration information as a dataframe

        :return: dict of config information
        """

        try:
            config_data = pd.read_csv(self._config_file)
        except:
            raise Exception("Can't read file %s" % self._config_file)

        try:
            config_data.index = config_data.Instrument
            config_data.drop("Instrument", 1, inplace=True)

        except:
            raise Exception("Badly configured file %s" %
                            (self._config_file))

        return config_data

    def __repr__(self):
        return self.name

    def get_list_of_instruments(self):
        return list(self.get_all_instrument_data().index)

    def _get_instrument_data_without_checking(self, instrument_code):
        all_instrument_data = self.get_all_instrument_data()
        config_for_this_instrument = all_instrument_data.loc[instrument_code]
        config_items = all_instrument_data.columns

        meta_data = dict([(item_name, getattr(config_for_this_instrument, item_name)) for item_name in config_items])
        instrument_object = futuresInstrument(instrument_code, **meta_data)
        print(instrument_object)

        return instrument_object

