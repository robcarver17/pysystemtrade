

from sysdata.futures.instruments import futuresInstrumentData
from sysobjects.instruments import  futuresInstrumentWithMetaData
from sysdata.mongodb.mongo_generic import mongoData, missing_data
from syslogdiag.log import logtoscreen

INSTRUMENT_COLLECTION = "futures_instruments"


class mongoFuturesInstrumentData(futuresInstrumentData):
    """
    Read and write data class to get instrument data

    We'd inherit from this class for a specific implementation

    """

    def __init__(self, mongo_db=None, log=logtoscreen(
            "mongoFuturesInstrumentData")):

        super().__init__(log=log)
        self._mongo_data = mongoData(INSTRUMENT_COLLECTION, "instrument_code", mongo_db = mongo_db)

    def __repr__(self):
        return "mongoFuturesInstrumentData %s" % str(self.mongo_data)

    @property
    def mongo_data(self):
        return self._mongo_data

    def get_list_of_instruments(self):
        return self.mongo_data.get_list_of_keys()

    def _get_instrument_data_without_checking(self, instrument_code):

        result_dict = self.mongo_data.get_result_dict_for_key(instrument_code)
        if result_dict is missing_data:
            # shouldn't happen...
            raise Exception("Data for %s gone AWOL" % instrument_code)

        instrument_object = futuresInstrumentWithMetaData.from_dict(result_dict)

        return instrument_object

    def _delete_instrument_data_without_any_warning_be_careful(
            self, instrument_code):
        self.mongo_data.delete_data_without_any_warning(instrument_code)

    def _add_instrument_data_without_checking_for_existing_entry(
        self, instrument_object
    ):
        instrument_object_dict = instrument_object.as_dict()
        instrument_code = instrument_object_dict.pop("instrument_code")
        self.mongo_data.add_data(instrument_code, instrument_object_dict)
