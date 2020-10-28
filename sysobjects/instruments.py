class futuresInstrument(object):
    """
    Define a generic instrument
    """

    def __init__(self, instrument_code, **kwargs):

        assert isinstance(instrument_code, str)

        self.instrument_code = instrument_code

        # any remaining data we dump into a meta data dict
        self.meta_data = kwargs

        self._isempty = False

    def __eq__(self, other):
        return self.instrument_code == other.instrument_code

    def __repr__(self):
        return self.instrument_code

    def as_dict(self):

        if self.empty():
            raise Exception("Can't create dict from empty object")

        dict_of_values = self.meta_data
        dict_of_values["instrument_code"] = self.instrument_code
        return dict_of_values

    @classmethod
    def create_from_dict(futuresInstrument, dict_of_values):

        instrument_code = dict_of_values.pop("instrument_code")

        return futuresInstrument(instrument_code, **dict_of_values)

    @classmethod
    def create_empty(futuresInstrument):
        futures_instrument = futuresInstrument("")
        futures_instrument._isempty = True

        return futures_instrument

    def empty(self):
        return self._isempty