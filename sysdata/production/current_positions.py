"""
Stores single position state rather than history

Any time we get the current position from DB or the broker, it's useful to store it in this type of object
"""
import pandas as pd
from syscore.genutils import get_unique_list
from sysobjects.instruments import futuresInstrument
from sysobjects.contracts import futuresContract


class Position(object):
    def __init__(self, position, tradeable_object):
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

    def __eq__(self, other):
        if self.position != other.position:
            return False

        if self._tradeable_object != other._tradeable_object:
            return False

        return True


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

    def __eq__(self, other):
        if self.instrument_object != other.instrument_object:
            return False

        if self.strategy_name != other.strategy_name:
            return False

        return True

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
    def date(self):
        return self._tradeable_object.date

    @property
    def contract_object(self):
        return self._tradeable_object

    @property
    def expiry_date(self):
        return self._tradeable_object.expiry_date

class listOfPositions(list):
    def __repr__(self):
        return str(self.as_pd_df())

    def __eq__(self, other):
        """
        Checks for equality


        :param other:
        :return:
        """
        pass

    def return_list_of_breaks(self, other):
        """
        Return list of tradeable objects where there is a break between self and other

        Does this by making both elements unique, then comparing item by item

        :return:
        """

        list_of_my_objects = [position.tradeable_object for position in self]
        list_of_other_objects = [
            position.tradeable_object for position in other]
        joint_list = get_unique_list(
            list_of_my_objects + list_of_other_objects)
        breaks = []
        for tradeable_object in joint_list:
            break_here = self.is_break_for_tradeable_object(
                other, tradeable_object)
            if break_here:
                breaks.append(tradeable_object)

        return breaks

    def is_break_for_tradeable_object(self, other, tradeable_object):
        """
        Return True if there is a break between self and other for given tradeable object

        :return: bool
        """

        my_position = self.position_for_object(tradeable_object)
        other_position = other.position_for_object(tradeable_object)
        if my_position == other_position:
            return False
        else:
            return True

    def position_for_object(self, tradeable_object):
        position_object_idx = self.index(tradeable_object)
        if position_object_idx is None:
            return 0

        position_object = self[position_object_idx]
        return position_object.position

    def index(self, tradeable_object, start=0, stop=None):
        """
        Return the first location index of tradeable_instrument after start

        :param tradeable_instrument: any tradeable instrument
        :param start: int, where we start looking
        :return: int, or None
        """
        if stop is None:
            stop = len(self) - 1

        idx = start
        while idx <= stop:
            position_to_check = self[idx]
            if position_to_check.tradeable_object == tradeable_object:
                return idx

            idx = idx + 1

        return None

    @classmethod
    def from_pd_df(listOfPositions, pd_df):
        def _element_object_from_row(dfrow):
            return Position(dfrow.position, dfrow.name)

        list_of_positions = listOfPositions()
        for df_row in pd_df.itertuples():
            list_of_positions.append(_element_object_from_row(df_row))

        return list_of_positions

    def as_pd_df(self):
        return pd.DataFrame(self._as_set_of_dicts())

    def _as_set_of_dicts(self):
        id_column_dict = self._id_column_dict()
        just_positions_list = [position.position for position in self]
        with_position_dict = id_column_dict
        with_position_dict["position"] = just_positions_list

        return with_position_dict

    def _id_column_dict(self):
        id_column_list = [str(position.tradeable_object) for position in self]
        id_column_dict = dict(name=id_column_list)
        return id_column_dict


class listOfInstrumentPositions(listOfPositions):
    @classmethod
    def from_pd_df(listOfInstrumentPositions, pd_df):
        def _element_object_from_row(dfrow):
            return instrumentPosition(dfrow.position, dfrow.instrument_code)

        list_of_positions = listOfInstrumentPositions()
        for df_row in pd_df.itertuples():
            list_of_positions.append(_element_object_from_row(df_row))

        return list_of_positions

    def _id_column_dict(self):
        id_column_list = [str(position.instrument_code) for position in self]
        id_column_dict = dict(instrument_code=id_column_list)
        return id_column_dict

    def position_for_instrument(self, instrument_code):
        tradeable_object = futuresInstrument(instrument_code)
        position = self.position_for_object(tradeable_object)
        return position

class listOfInstrumentStrategyPositions(listOfPositions):
    @classmethod
    def from_pd_df(listOfInstrumentStrategyPositions, pd_df):
        def _element_object_from_row(dfrow):
            return instrumentStrategyPosition(
                dfrow.position, dfrow.strategy_name, dfrow.instrument_code
            )

        list_of_positions = listOfInstrumentStrategyPositions()
        for df_row in pd_df.itertuples():
            list_of_positions.append(_element_object_from_row(df_row))

        return list_of_positions

    def _id_column_dict(self):
        instrument_code_list = [str(position.instrument_code)
                                for position in self]
        strategy_name_list = [str(position.strategy_name) for position in self]
        id_column_dict = dict(
            strategy_name=strategy_name_list,
            instrument_code=instrument_code_list)
        return id_column_dict

    def sum_for_instrument(self):
        return sum_for_instrument(self)


class listOfContractPositions(listOfPositions):
    @classmethod
    def from_pd_df(listOfInstrumentContractPositions, pd_df):
        def _element_object_from_row(dfrow):
            return instrumentStrategyPosition(
                dfrow.position, dfrow.contract_id, dfrow.instrument_code
            )

        list_of_positions = listOfInstrumentContractPositions()
        for df_row in pd_df.itertuples():
            list_of_positions.append(_element_object_from_row(df_row))

        return list_of_positions

    def _element_class(self):
        return contractPosition

    def _id_column_dict(self):
        instrument_code_list = [str(position.instrument_code)
                                for position in self]
        contract_id_list = [str(position.date) for position in self]
        expiry_date_list = [str(position.expiry_date) for position in self]
        id_column_dict = dict(
            instrument_code=instrument_code_list,
            contract_date=contract_id_list,
            expiry_date = expiry_date_list)

        return id_column_dict

    def sum_for_instrument(self):
        """
        Sum up positions for same instrument

        :return: listOfInstrumentPositions
        """

        return sum_for_instrument(self)




def sum_for_instrument(list_of_positions):
    """
    Sum up positions for same instrument across strategies

    :return: listOfInstrumentPositions
    """

    list_of_instruments = list(
        set([position.instrument_code for position in list_of_positions])
    )
    summed_positions = []
    for instrument_code in list_of_instruments:
        positions_this_code = [
            position.position
            for position in list_of_positions
            if position.instrument_code == instrument_code
        ]
        position_object = instrumentPosition(
            sum(positions_this_code), instrument_code)
        summed_positions.append(position_object)
    list_of_instrument_position_object = listOfInstrumentPositions(
        summed_positions)

    return list_of_instrument_position_object
