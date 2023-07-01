from sysdata.base_data import baseData

from sysobjects.production.override import Override
from syslogging.logger import get_logger


class temporaryOverrideData(baseData):
    """
    Temporary close is a way of temporarily setting position limits to
     zero

    We use this table to store the old position limits

    """

    def __init__(self, log=get_logger("temporaryOverrideData")):
        super().__init__(log=log)

    def add_stored_override(
        self, instrument_code: str, override_for_instrument: Override
    ):
        if self.does_instrument_have_override_stored(instrument_code):
            raise Exception(
                "Need to clear_stored_override_for_instrument before adding a new one for %s"
                % instrument_code
            )

        self._add_stored_override_without_checking(
            instrument_code=instrument_code,
            override_for_instrument=override_for_instrument,
        )

    def get_stored_override_for_instrument(self, instrument_code: str) -> Override:
        raise NotImplementedError("Need to use inheriting class")

    def clear_stored_override_for_instrument(self, instrument_code: str):
        if self.does_instrument_have_override_stored(instrument_code):
            self._delete_stored_override_without_checking(instrument_code)

    def _add_stored_override_without_checking(
        self, instrument_code: str, override_for_instrument: Override
    ):
        raise NotImplementedError("Need to use inheriting class")

    def does_instrument_have_override_stored(self, instrument_code) -> bool:
        raise NotImplementedError("Need to use inheriting class")

    def _delete_stored_override_without_checking(self, instrument_code: str):
        raise NotImplementedError("Need to use inheriting class")
