"""
Read / write and represent instrument data
"""

from sysdata.data import baseData

class futuresInstrument(object):
    """
    Define a generic instrument
    """

    def __init__(self, instrument_code,  **kwargs):

        assert type(instrument_code) is str

        self.instrument_code = instrument_code

        ## any remaining data we dump into a meta data dict
        self.meta_data = kwargs

        self._isempty = False

    def __repr__(self):
        return self.instrument_code

    def as_dict(self):

        if self.empty():
            raise Exception("Can't create dict from empty object")

        dict_of_values = self.meta_data
        dict_of_values['instrument_code'] = self.instrument_code
        return dict_of_values


    @classmethod
    def create_from_dict(futuresInstrument, dict_of_values):

        instrument_code = dict_of_values.pop('instrument_code')

        return futuresInstrument(instrument_code, **dict_of_values)

    @classmethod
    def create_empty(futuresInstrument):
        futures_instrument = futuresInstrument("")
        futures_instrument._isempty = True

        return futures_instrument

    def empty(self):
        return self._isempty


USE_CHILD_CLASS_ERROR = "You need to use a child class of futuresInstrumentData"

class futuresInstrumentData(baseData):
    """
    Read and write data class to get instrument data

    We'd inherit from this class for a specific implementation

    """

    def __repr__(self):
        return "futuresInstrumentData base class - DO NOT USE"

    def keys(self):
        return self.get_list_of_instruments()

    def get_all_instrument_data(self):
        # returns all instrument data as a pd.DataFrame
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_list_of_instruments(self):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_instrument_data(self, instrument_code):
        if self.is_code_in_data(instrument_code):
            return self._get_instrument_data_without_checking(instrument_code)
        else:
            return futuresInstrument.create_empty()

    def _get_instrument_data_without_checking(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def __getitem__(self, instrument_code):
        return self.get_instrument_data(instrument_code)

    def delete_instrument_data(self, instrument_code, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_instrument_data_without_any_warning_be_careful(instrument_code)
                self.log.terse("Deleted instrument object %s" % instrument_code)

            else:
                ## doesn't exist anyway
                self.log.warn("Tried to delete non existent instrument")
        else:
            self.log.error("You need to call delete_instrument_data with a flag to be sure")

    def _delete_instrument_data_without_any_warning_be_careful(instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_instrument_data(self, instrument_object, ignore_duplication=False):
        instrument_code = instrument_object.instrument_code

        self.log.label(instrument_code=instrument_code)

        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                self.log.error("There is already %s in the data, you have to delete it first" % instrument_code)

        self._add_instrument_data_without_checking_for_existing_entry(instrument_object)

        self.log.terse("Added instrument object %s" % instrument_object.instrument_code)

    def _add_instrument_data_without_checking_for_existing_entry(self, instrument_object):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

