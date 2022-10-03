from sysdata.base_data import baseData
from sysobjects.spreads import spreadsForInstrument

USE_CHILD_CLASS_ERROR = "You need to use a child class of spreadsForInstrumentData"


class spreadsForInstrumentData(baseData):
    """
    Read and write data class to get spreads

    We'd inherit from this class for a specific implementation

    """

    def __repr__(self):
        return USE_CHILD_CLASS_ERROR

    def keys(self):
        return self.get_list_of_instruments()

    def add_spread_entry(self, instrument_code: str, spread: float):
        existing_spreads = self.get_spreads(instrument_code)
        new_spreads = existing_spreads.add_spread(spread)
        self.add_spreads(instrument_code, spreads=new_spreads, ignore_duplication=True)

    def get_spreads(self, instrument_code: str) -> spreadsForInstrument:
        if self.is_code_in_data(instrument_code):
            spreads = self._get_spreads_without_checking(instrument_code)
        else:
            spreads = spreadsForInstrument()

        return spreads

    def __getitem__(self, instrument_code: str) -> spreadsForInstrument:
        return self.get_spreads(instrument_code)

    def delete_spreads(self, instrument_code: str, are_you_sure: bool = False):
        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_spreads_without_any_warning_be_careful(instrument_code)
                self.log.terse(
                    "Deleted spread data for %s" % instrument_code,
                    instrument_code=instrument_code,
                )

            else:
                # doesn't exist anyway
                self.log.warn(
                    "Tried to delete non existent spreads for %s" % instrument_code,
                    instrument_code=instrument_code,
                )
        else:
            self.log.error(
                "You need to call delete_spreads with a flag to be sure",
                instrument_code=instrument_code,
            )

    def is_code_in_data(self, instrument_code: str) -> bool:
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_spreads(
        self,
        instrument_code: str,
        spreads: spreadsForInstrument,
        ignore_duplication: bool = False,
    ):
        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                self.log.error(
                    "There is already %s in the data, you have to delete it first"
                    % instrument_code,
                    instrument_code=instrument_code,
                )

        self._add_spreads_without_checking_for_existing_entry(instrument_code, spreads)

        self.log.terse(
            "Added data for instrument %s" % instrument_code,
            instrument_code=instrument_code,
        )

    def _add_spreads_without_checking_for_existing_entry(
        self, instrument_code: str, spreads: spreadsForInstrument
    ):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_list_of_instruments(self) -> list:
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def _delete_spreads_without_any_warning_be_careful(self, instrument_code: str):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def _get_spreads_without_checking(
        self, instrument_code: str
    ) -> spreadsForInstrument:
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)
