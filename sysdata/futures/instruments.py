"""
Read / write and represent instrument data
"""

class futuresInstrument(object):
    """
    Define a generic instrument
    """

    def __init__(self, instrument_code,  **ignored_kwargs):
        """
        Create a new instrument

        :param instrument_code: The name of the contract
        :param rollcycle:  The roll cycle
        :param ignored_kwargs: Stuff that might be passed by accident
        """
        assert type(instrument_code) is str

        self.instrument_code = instrument_code

    def __repr__(self):
        return self.instrument_code

