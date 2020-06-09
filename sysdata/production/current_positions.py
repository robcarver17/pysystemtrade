"""
Stores single position state rather than history

Any time we get the current position from DB or the broker, it's useful to store it in this type of object
"""
import pandas as pd

from sysdata.futures.instruments import futuresInstrument
from sysdata.futures.contracts import futuresContract

class Position(object):
    def __init__(self,  position, tradeable_object):
        self._tradeable_object = tradeable_object
        self._position = position

    def __repr__(self):
        return "%s position %d" % (str(self._tradeable_object), self.position)

    @property
    def tradeable_object(self):
        return self._tradeable_object

    @property
    def position(self):
        return self._position

class instrumentPosition(Position):
    def __init__(self, position, *args, **kwargs):
        tradeable_object = futuresInstrument(*args, **kwargs)
        super().__init__(position, tradeable_object)

    @property
    def instrument_code(self):
        return self._tradeable_object.instrument_code

class instrumentStrategy(object):
    def __init__(self, strategy_name, *args, **kwargs):
        instrument_object = futuresInstrument(*args, **kwargs)
        self._instrument_object = instrument_object
        self._strategy_name = strategy_name

    def __repr__(self):
        return "%s %s" % (self.strategy_name, str(self.instrument_object))

    @property
    def instrument_object(self):
        return self._instrument_object

    @property
    def instrument_code(self):
        return self.instrument_object.instrument_code

    @property
    def strategy_name(self):
        return self._strategy_name

class instrumentStrategyPosition(Position):
    def __init__(self, position, strategy_name, *args, **kwargs):
        tradeable_object = instrumentStrategy(strategy_name, *args, **kwargs)

        super().__init__(position, tradeable_object)

    @property
    def instrument_code(self):
        return self._tradeable_object.instrument_code

    @property
    def strategy_name(self):
        return self._tradeable_object.strategy_name


class contractPosition(Position):
    def __init__(self, position, *args, **kwargs):
        tradeable_object = futuresContract(*args, **kwargs)
        super().__init__(position, tradeable_object)

    @property
    def instrument_code(self):
        return self._tradeable_object.instrument_code

    @property
    def contract_date(self):
        return self._tradeable_object.contract_date

class listOfPositions(list):
    def __repr__(self):
        return str(self.as_pd_df())

    def as_pd_df(self):
        return pd.DataFrame(self._as_set_of_dicts())

    def _as_set_of_dicts(self):
        id_column_dict = self._id_column_dict()
        just_positions_list = [position.position for position in self]
        with_position_dict = id_column_dict
        with_position_dict['position'] = just_positions_list

        return with_position_dict

    def _id_column_dict(self):
        id_column_list = [str(position.tradeable_object) for position in self]
        id_column_dict = dict(name=id_column_list)
        return id_column_dict

class listOfInstrumentPositions(listOfPositions):
    def _id_column_dict(self):
        id_column_list = [str(position.instrument_code) for position in self]
        id_column_dict = dict(instrument_code=id_column_list)
        return id_column_dict

class listOfInstrumentStrategyPositions(listOfPositions):
    def _id_column_dict(self):
        instrument_code_list = [str(position.instrument_code) for position in self]
        strategy_name_list = [str(position.strategy_name) for position in self]
        id_column_dict = dict( strategy_name = strategy_name_list, instrument_code=instrument_code_list)
        return id_column_dict


class listOfContractPositions(listOfPositions):
    def _id_column_dict(self):
        instrument_code_list = [str(position.instrument_code) for position in self]
        contract_id_list = [str(position.contract_date) for position in self]
        id_column_dict = dict(instrument_code=instrument_code_list, contract_date = contract_id_list)
        return id_column_dict

