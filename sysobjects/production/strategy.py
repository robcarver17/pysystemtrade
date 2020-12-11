from sysobjects.instruments import futuresInstrument


class instrumentStrategy(object):
    def __init__(self, strategy_name: str, instrument_code:str):
        instrument_object = futuresInstrument(instrument_code)
        self._instrument = instrument_object
        self._strategy_name = strategy_name

    def __repr__(self):
        return "%s %s" % (self.strategy_name, str(self.instrument))

    def __eq__(self, other):
        if self.instrument != other.instrument:
            return False

        if self.strategy_name != other.strategy_name:
            return False

        return True

    @property
    def instrument(self):
        return self._instrument

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    @property
    def strategy_name(self):
        return self._strategy_name