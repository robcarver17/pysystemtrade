from sysobjects.instruments import futuresInstrument

class listOfInstrumentStrategies(list):
    def unique_join_with_other_list(self, other):
        return listOfInstrumentStrategies(set(list(self+other)))

    def get_list_of_strategies(self) -> list:
        list_of_strategies = list(set([instrument_strategy.strategy_name for
                                       instrument_strategy in self]))

        return list_of_strategies

    def get_list_of_instruments_for_strategy(self, strategy_name: str) -> list:
        list_of_instrument_strategies = self.get_list_of_instrument_strategies_for_strategy(strategy_name)
        list_of_instruments = [
            instrument_strategy.instrument_code
            for instrument_strategy in list_of_instrument_strategies
        ]

        return list_of_instruments

    def get_list_of_instrument_strategies_for_strategy(self, strategy_name: str):
        list_of_instrument_strategies = [
            instrument_strategy
            for instrument_strategy in self
            if instrument_strategy.strategy_name == strategy_name
        ]

        return list_of_instrument_strategies


STRATEGY_NAME_KEY = 'strategy_name'
INSTRUMENT_CODE_KEY = 'instrument_code'

class instrumentStrategy(object):
    def __init__(self, strategy_name: str, instrument_code:str):
        instrument_object = futuresInstrument(instrument_code)
        self._instrument = instrument_object
        self._strategy_name = strategy_name

    def __hash__(self):
        return self.instrument_code.__hash__()+self.strategy_name.__hash__()

    def __repr__(self):
        return self.key

    @property
    def key(self):
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

    def as_dict(self):
        return {STRATEGY_NAME_KEY: self.strategy_name, INSTRUMENT_CODE_KEY: self.instrument_code}

    @classmethod
    def from_dict(instrumentStrategy, attr_dict):
        return instrumentStrategy(attr_dict[STRATEGY_NAME_KEY], attr_dict[INSTRUMENT_CODE_KEY])