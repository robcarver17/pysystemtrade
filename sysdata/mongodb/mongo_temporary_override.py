from syscore.exceptions import missingData
from syscore.constants import arg_not_supplied

from sysdata.production.temporary_override import temporaryOverrideData
from sysdata.mongodb.mongo_override import from_dict_to_override, from_override_to_dict
from sysobjects.production.override import Override
from sysdata.mongodb.mongo_generic import mongoDataWithSingleKey
from syslogging.logger import get_logger
from sysobjects.production.override import DEFAULT_OVERRIDE


TEMPORARY_OVERRIDE_COLLECTION = "temporary_override_collection"
KEY = "instrument_code"


class mongoTemporaryOverrideData(temporaryOverrideData):
    def __init__(
        self, mongo_db=arg_not_supplied, log=get_logger("mongoTemporaryOverrideData")
    ):
        super().__init__(log=log)
        self._mongo_data = mongoDataWithSingleKey(
            TEMPORARY_OVERRIDE_COLLECTION, KEY, mongo_db=mongo_db
        )

    def __repr__(self):
        return "mongoTemporaryOverrideData %s" % str(self.mongo_data)

    @property
    def mongo_data(self):
        return self._mongo_data

    def get_stored_override_for_instrument(self, instrument_code: str) -> Override:
        try:
            override_as_dict = self.mongo_data.get_result_dict_for_key(instrument_code)
        except missingData:
            return DEFAULT_OVERRIDE

        return from_dict_to_override(override_as_dict)

    def _add_stored_override_without_checking(
        self, instrument_code: str, override_for_instrument: Override
    ):
        override_as_dict = from_override_to_dict(override_for_instrument)
        self.mongo_data.add_data(
            key=instrument_code, data_dict=override_as_dict, allow_overwrite=True
        )

    def _delete_stored_override_without_checking(self, instrument_code: str):
        self.mongo_data.delete_data_without_any_warning(instrument_code)

    def does_instrument_have_override_stored(self, instrument_code) -> bool:
        return self.mongo_data.key_is_in_data(instrument_code)
