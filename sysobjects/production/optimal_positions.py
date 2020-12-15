import pandas as pd

from sysobjects.production.positions import instrumentStrategyPosition, instrumentStrategy, listOfInstrumentStrategyPositions
from sysobjects.production.timed_storage import timedEntry


class simpleOptimalPosition(timedEntry):
    """
    This is the simplest possible optimal positions object

    """

    @property
    def required_argument_names(self) -> list:
        return ["position"]  # compulsory args

    @property
    def _name_(self):
        return "simpleOptimalPosition"

    @property
    def containing_data_class_name(self):
        return "sysdata.production.optimal_positions.simpleOptimalPositionForInstrument"

    def check_position_break(self, position: float):
        return self.position == position


class bufferedOptimalPositions(timedEntry):
    """
    Here is one with buffers

    """

    @property
    def required_argument_names(self) -> list:
        return [
            "lower_position",
            "upper_position",
            "reference_price",
            "reference_contract",
        ]  # compulsory args

    @property
    def _name_(self):
        return "bufferedOptimalPosition"

    @property
    def containing_data_class_name(self):
        return (
            "sysdata.production.optimal_positions.bufferedOptimalPositionForInstrument"
        )

    def _argument_checks(self, kwargs):
        # run on __init__ by parent class
        try:
            assert kwargs["upper_position"] >= kwargs["lower_position"]
        except BaseException:
            raise Exception(
                "Upper position has to be higher than lower position")

    def check_position_break(self, position: int):
        # ignore warnings set dynamically
        return position < round(self.lower_position) or position > round(
            self.upper_position
        )

    def __repr__(self):
        return "%.3f/%.3f" % (self.lower_position, self.upper_position)


class instrumentStrategyAndOptimalPosition(object):
    def __init__(self, instrument_strategy: instrumentStrategy,
                 optimal_position_object: simpleOptimalPosition):

        self.instrument_strategy = instrument_strategy
        self.optimal_position = optimal_position_object

    def check_instrument_strategies_match(self, instrument_strategy_and_position: instrumentStrategyPosition):
        return self.instrument_strategy == instrument_strategy_and_position.instrument_strategy

    def key(self):
        return self.instrument_strategy.key

class instrumentStrategyWithOptimalAndCurrentPosition(object):
    def __init__(
            self,
            instrument_strategy_and_optimal_position: instrumentStrategyAndOptimalPosition,
            instrument_strategy_and_position: instrumentStrategyPosition):
        # this is contains a instrumentStrategyPosition type thing, and a tradeableObjectAndOptimalPosition
        # type thing

        # same tradeable object, so that is stored plus Position, and
        # OptimalPosition
        assert (
                instrument_strategy_and_optimal_position.check_instrument_strategies_match(
                instrument_strategy_and_position
            )
                is True
        )
        self.instrument_strategy = instrument_strategy_and_optimal_position.instrument_strategy
        self.position = instrument_strategy_and_position.position
        self.optimal_position = instrument_strategy_and_optimal_position.optimal_position

    @property
    def key(self) -> str:
        return self.instrument_strategy.key

    def check_break(self) -> bool:
        # checks to see if current position is outslide the limits defined by the optimal position
        return self.optimal_position.check_position_break(self.position)


class listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies(list):
    # list of instrumentStrategyWithOptimalAndCurrentPosition


    def check_breaks(self) -> list:
        # return a list of bool
        list_of_breaks = [pos.check_break() for pos in self]

        return list_of_breaks

    def as_pd_with_breaks(self) -> pd.DataFrame:
        instrument_strategies = [pos.key for pos in self]
        optimal_positions = [pos.optimal_position for pos in self]
        current_positions = [pos.position for pos in self]
        breaks = self.check_breaks()

        ans = pd.DataFrame(
            dict(
                current=current_positions,
                optimal=optimal_positions,
                breaks=breaks),
            index=instrument_strategies,
        )

        return ans

class listOfOptimalPositionsAcrossInstrumentStrategies(list):
    # list of instrumentStrategyAndOptimalPosition
    def as_pd(self) -> pd.DataFrame:
        list_of_keys = [pos.key for pos in self]
        list_of_optimal = [pos.optimal_position for pos in self]

        return pd.DataFrame(dict(key=list_of_keys, optimal=list_of_optimal))

    def add_positions(self, position_list:  listOfInstrumentStrategyPositions)  \
            -> listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies:

        list_of_optimal_and_current = []
        for opt_pos_object in self:
            instrument_strategy = opt_pos_object.instrument_strategy
            relevant_position_item = position_list.position_object_for_instrument_strategy(instrument_strategy)
            new_object = instrumentStrategyWithOptimalAndCurrentPosition(
                opt_pos_object, relevant_position_item
            )
            list_of_optimal_and_current.append(new_object)

        list_of_optimal_and_current = (
            listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies(
                list_of_optimal_and_current
            )
        )
        return list_of_optimal_and_current

