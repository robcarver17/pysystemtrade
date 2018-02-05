from syscore.fileutils import get_filename_for_package
from sysdata.futures.instruments import futuresInstrumentData, futuresInstrument
import pandas as pd

INSTRUMENT_CONFIG_FILE = "sysinit.futures.config.instrumentconfig.csv"

class initCsvFuturesInstrumentData(futuresInstrumentData):
    """
    Get data about instruments from a special configuration used for initialising the system

    """
    def __init__(self, config_file=INSTRUMENT_CONFIG_FILE):

        super().__init__()

        self._config_file = get_filename_for_package(config_file)
        self.name = "Instruments data for initialising system config"

    def _get_config_information(self):
        """
        Get configuration information

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
        return list(self._get_config_information().index)

    def _get_instrument_data_without_checking(self, instrument_code):
        config_for_this_instrument = self._get_config_information().loc[instrument_code]

        instrument_object = futuresInstrument(instrument_code,
                                              description = config_for_this_instrument.Description,
                                                  exchange = config_for_this_instrument.Exchange,
                                                  point_size = config_for_this_instrument.Pointsize,
                                                  currency = config_for_this_instrument.Currency,
                                                  asset_class = config_for_this_instrument.Assetclass)
        print(instrument_object)

        return instrument_object

