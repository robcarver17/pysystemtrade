import pandas as pd

from syscore.genutils import get_unique_list_slow
from sysobjects.contracts import futuresContract, contract_from_key
from sysobjects.instruments import futuresInstrument
from sysobjects.production.tradeable_object import instrumentStrategy


class Position(object):
    def __init__(self, position: int, tradeable_object):
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
    def __init__(self, position: int, instrument_code: str):
        tradeable_object = futuresInstrument(instrument_code)
        super().__init__(position, tradeable_object)

    @property
    def instrument(self) -> futuresInstrument:
        return self.tradeable_object

    @property
    def instrument_code(self) -> str:
        return self.instrument.instrument_code


class instrumentStrategyPosition(Position):
    def __init__(self, position: int, instrument_strategy: instrumentStrategy):

        super().__init__(position, instrument_strategy)

    @property
    def instrument_strategy(self) -> instrumentStrategy:
        return self.tradeable_object

    @property
    def instrument_code(self) -> str:
        return self.instrument_strategy.instrument_code

    @property
    def strategy_name(self) -> str:
        return self.instrument_strategy.strategy_name


class contractPosition(Position):
    def __init__(self, position: int, contract: futuresContract):
        super().__init__(position, contract)

    @property
    def contract(self) -> futuresContract:
        return self.tradeable_object

    @property
    def instrument_code(self) -> str:
        return self.contract.instrument_code

    @property
    def date_str(self) -> str:
        return self.contract.date_str

    @property
    def expiry_date(self):
        return self.contract.expiry_date


KEY_POSITION = "position"
KEY_TRADEABLE_OBJECT = "name"


class listOfPositions(list):
    def __repr__(self):
        return str(self.as_pd_df())

    def return_list_of_breaks(self, other_list_of_positions):
        """
        Return list of tradeable objects where there is a break between self and other

        Does this by making both elements unique, then comparing item by item

        :return:
        """

        list_of_my_tradeable_objects = [position.tradeable_object for position in self]
        list_of_other_tradeable_objects = [
            position.tradeable_object for position in other_list_of_positions
        ]
        joint_list_of_tradeable_objects = get_unique_list_slow(
            list_of_my_tradeable_objects + list_of_other_tradeable_objects
        )
        list_of_breaks = []
        for tradeable_object in joint_list_of_tradeable_objects:
            break_here = self.is_break_for_tradeable_object(
                other_list_of_positions, tradeable_object
            )
            if break_here:
                list_of_breaks.append(tradeable_object)

        return list_of_breaks

    def is_break_for_tradeable_object(self, other_list_of_positions, tradeable_object):
        """
        Return True if there is a break between self and other for given tradeable object

        :return: bool
        """

        my_position = self.position_for_object(tradeable_object)
        other_position = other_list_of_positions.position_for_object(tradeable_object)
        if my_position == other_position:
            return False
        else:
            return True

    def position_for_object(self, tradeable_object):
        try:
            position_object_idx = self.index(tradeable_object)
        except IndexError:
            return 0

        position_object = self[position_object_idx]
        return position_object.position

    def index(self, tradeable_object, start=0, stop=None) -> int:
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

        raise IndexError()

    @classmethod
    def from_pd_df(listOfPositions, pd_df: pd.DataFrame):
        """

        :param pd_df: a pd.DataFrame that has two columns, position and name. Name contains tradeable objects
        :return:
        """

        def _position_object_from_row(dfrow):
            return Position(dfrow[KEY_POSITION], dfrow.name[KEY_TRADEABLE_OBJECT])

        list_of_positions = listOfPositions()
        for df_row in pd_df.itertuples():
            list_of_positions.append(_position_object_from_row(df_row))

        return list_of_positions

    def as_pd_df(self) -> pd.DataFrame:
        return pd.DataFrame(self._as_set_of_dicts())

    def _as_set_of_dicts(self) -> dict:
        # start with
        output_dict = self._id_column_dict()
        positions_column = [position.position for position in self]

        output_dict[KEY_POSITION] = positions_column

        return output_dict

    def _id_column_dict(self) -> dict:
        id_column_list = [str(position.tradeable_object) for position in self]
        id_column_dict = {KEY_TRADEABLE_OBJECT: id_column_list}
        return id_column_dict


KEY_INSTRUMENT_CODE = "instrument_code"


class listOfInstrumentPositions(listOfPositions):
    @classmethod
    def from_pd_df(listOfInstrumentPositions, pd_df: pd.DataFrame):
        def _element_object_from_row(dfrow):
            return instrumentPosition(dfrow[KEY_POSITION], dfrow[KEY_INSTRUMENT_CODE])

        list_of_positions = listOfInstrumentPositions()
        for df_row in pd_df.itertuples():
            list_of_positions.append(_element_object_from_row(df_row))

        return list_of_positions

    def _id_column_dict(self) -> dict:
        id_column_list = [str(position.instrument_code) for position in self]
        id_column_dict = {KEY_INSTRUMENT_CODE: id_column_list}
        return id_column_dict

    def position_for_instrument(self, instrument_code: str):
        tradeable_object = futuresInstrument(instrument_code)
        position = self.position_for_object(tradeable_object)
        return position


KEY_STRATEGY_NAME = "strategy_name"


class listOfPositionsWithInstruments(listOfPositions):
    def sum_for_instrument(self):
        return sum_for_instrument(self)

    def unique_list_of_instruments(self):
        list_of_instruments = self.instrument_code_list()
        unique_list_of_instruments = list(set(list_of_instruments))
        return unique_list_of_instruments

    def instrument_code_list(self) -> list:
        instrument_code_list = [str(position.instrument_code) for position in self]

        return instrument_code_list


class listOfInstrumentStrategyPositions(listOfPositionsWithInstruments):
    @classmethod
    def from_pd_df(listOfInstrumentStrategyPositions, pd_df: pd.DataFrame):
        def _element_object_from_row(dfrow):
            instrument_strategy = instrumentStrategy(
                strategy_name=dfrow[KEY_STRATEGY_NAME],
                instrument_code=dfrow[KEY_INSTRUMENT_CODE],
            )
            return instrumentStrategyPosition(dfrow[KEY_POSITION], instrument_strategy)

        list_of_positions = listOfInstrumentStrategyPositions()
        for df_row in pd_df.itertuples():
            list_of_positions.append(_element_object_from_row(df_row))

        return list_of_positions

    def _id_column_dict(self) -> dict:
        instrument_code_list = [str(position.instrument_code) for position in self]
        strategy_name_list = [str(position.strategy_name) for position in self]
        id_column_dict = {
            KEY_STRATEGY_NAME: strategy_name_list,
            KEY_INSTRUMENT_CODE: instrument_code_list,
        }

        return id_column_dict

    def position_object_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ):

        result = list(
            filter(
                lambda position: position.instrument_strategy == instrument_strategy,
                self,
            )
        )
        if len(result) == 0:
            return instrumentStrategyPosition(0, instrument_strategy)
        elif len(result) == 1:
            return result[0]
        else:
            raise Exception(
                "Multiple instances of %s found in list of positions!"
                % str(instrument_strategy)
            )


class listOfContractPositions(listOfPositionsWithInstruments):
    @classmethod
    def from_pd_df(listOfInstrumentContractPositions, pd_df):
        def _element_object_from_row(dfrow):
            contract = futuresContract(dfrow.instrument_code, dfrow.contract_id)

            return contractPosition(dfrow.position, contract)

        list_of_positions = listOfInstrumentContractPositions()
        for df_row in pd_df.itertuples():
            list_of_positions.append(_element_object_from_row(df_row))

        return list_of_positions

    def _element_class(self):
        return contractPosition

    def _id_column_dict(self):
        instrument_code_list = [str(position.instrument_code) for position in self]
        contract_id_list = [str(position.date_str) for position in self]
        expiry_date_list = [str(position.expiry_date) for position in self]
        id_column_dict = dict(
            instrument_code=instrument_code_list,
            contract_date=contract_id_list,
            expiry_date=expiry_date_list,
        )

        return id_column_dict

    def unique_list_of_contract_codes(self) -> list:
        list_of_contracts = self.contract_code_list()
        unique_list_of_contracts = list(set(list_of_contracts))
        return unique_list_of_contracts

    def contract_code_list(self) -> list:
        contract_code_list = [position.contract.key for position in self]

        return contract_code_list

    def sum_for_contract(self):
        return sum_for_contract(self)


def sum_for_instrument(list_of_positions) -> listOfInstrumentPositions:
    """
    Sum up positions for same instrument across strategies or contracts

    :return: listOfInstrumentPositions
    """

    unique_list_of_instruments = list_of_positions.unique_list_of_instruments()
    summed_positions = []
    for instrument_code in unique_list_of_instruments:
        position_object = _position_for_code_in_list(list_of_positions, instrument_code)
        summed_positions.append(position_object)

    list_of_instrument_position_object = listOfInstrumentPositions(summed_positions)

    return list_of_instrument_position_object


def sum_for_contract(
    list_of_positions: listOfContractPositions,
) -> listOfContractPositions:
    """
    Sum up positions for same instrument across strategies or contracts

    :return: listOfInstrumentPositions
    """

    unique_list_of_contract_codes = list_of_positions.unique_list_of_contract_codes()
    summed_positions = []
    for contract_key in unique_list_of_contract_codes:
        position_object = _position_for_contract_in_list(
            list_of_positions, contract_from_key(contract_key)
        )
        summed_positions.append(position_object)

    list_of_contract_position_object = listOfContractPositions(summed_positions)

    return list_of_contract_position_object


def _position_for_code_in_list(
    list_of_positions, instrument_code: str
) -> instrumentPosition:
    positions_this_code = [
        position.position
        for position in list_of_positions
        if position.instrument_code == instrument_code
    ]
    position_object = instrumentPosition(sum(positions_this_code), instrument_code)

    return position_object


def _position_for_contract_in_list(
    list_of_positions: listOfContractPositions, contract: futuresContract
) -> contractPosition:
    positions_this_contract = [
        position.position
        for position in list_of_positions
        if position.contract == contract
    ]
    position_object = contractPosition(sum(positions_this_contract), contract)

    return position_object
