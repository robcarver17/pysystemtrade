import pandas as pd

from syscore.genutils import flatten_list
from sysobjects.production.positions import (
    instrumentStrategyPosition,
    listOfInstrumentStrategyPositions,
)
from sysobjects.production.tradeable_object import instrumentStrategy
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
        try:
            found_break = self.position == position
        except:
            raise Exception(
                "Can't check break for simpleOptimalPosition: most likely problem is data was stored incorrectly"
            )
        return found_break


class bufferedOptimalPositions(simpleOptimalPosition):
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
        upper_position = kwargs["upper_position"]
        lower_position = kwargs["lower_position"]
        try:
            assert upper_position >= lower_position
        except BaseException:
            raise Exception(
                "Upper position %f  has to be >= than lower position %f"
                % (upper_position, lower_position)
            )

    def check_position_break(self, position: int):
        # ignore warnings set dynamically
        return position < round(self.lower_position) or position > round(
            self.upper_position
        )

    def __repr__(self):
        return "%.3f/%.3f" % (self.lower_position, self.upper_position)


class optimalPositionWithReference(simpleOptimalPosition):
    @property
    def required_argument_names(self) -> list:
        return [
            "optimal_position",
            "reference_price",
            "reference_contract",
            "reference_date",
        ]  # compulsory args

    @property
    def _name_(self):
        return "optimalPositionWithReference"

    @property
    def containing_data_class_name(self):
        return (
            "sysdata.production.optimal_positions.optimalPositionWithReferenceForAsset"
        )

    def _argument_checks(self, kwargs):
        pass

    def check_position_break(self, position: int):
        return False

    def __repr__(self):
        return "%.3f" % (self.optimal_position)


class optimalPositionWithDynamicCalculations(simpleOptimalPosition):
    @property
    def required_argument_names(self) -> list:
        return [
            "reference_price",
            "reference_contract",
            "reference_date",
            "optimal_position",
            "weight_per_contract",
            "previous_position",
            "previous_weight",
            "reduce_only",
            "dont_trade",
            "position_limit_contracts",
            "position_limit_weight",
            "optimum_weight",
            "minimum_weight",
            "maximum_weight",
            "start_weight",
            "optimised_weight",
            "optimised_position",
        ]  # compulsory args

    @property
    def _name_(self):
        return "optimalPositionWithDynamicCalculations"

    def verbose_repr(self):
        ref_str = "Reference %s/%f@%s " % (
            self.reference_contract,
            self.reference_price,
            str(self.reference_date),
        )

        pos_str = "Positions: Optimal %f Previous %d Limit %d Optimised %d, " % (
            self.optimal_position,
            self.previous_position,
            self.position_limit_contracts,
            self.optimised_position,
        )

        weight_str = (
            "Weights: Per contract %.3f Previous %.3f Optimum %.3f Limit %.3f Minimum %.3f Maximum %.3f Start %.3f Optimised %.3f"
            % (
                self.weight_per_contract,
                self.previous_weight,
                self.optimum_weight,
                self.position_limit_weight,
                self.minimum_weight,
                self.maximum_weight,
                self.start_weight,
                self.optimised_weight,
            )
        )

        logic_str = ""
        if self.dont_trade:
            logic_str = "(NoTrading) "
        elif self.reduce_only:
            logic_str = "(ReduceOnly) "
        else:
            logic_str = ""

        return ref_str + logic_str + pos_str + weight_str

    @property
    def containing_data_class_name(self):
        ## FIX ME WHAT DOES THIS ACTUALLY DO??
        return (
            "sysdata.production.optimal_positions.dynamicOptimalPositionForInstrument"
        )

    def _argument_checks(self, kwargs):
        assert type(kwargs["optimised_position"]) is int

    def check_position_break(self, position: int):
        optimised_position = self.optimised_position
        if position != optimised_position:
            return True
        else:
            return False

    def __repr__(self):
        return "%.3f" % (self.optimised_position)


class instrumentStrategyAndOptimalPosition(object):
    def __init__(
        self,
        instrument_strategy: instrumentStrategy,
        optimal_position_object: simpleOptimalPosition,
    ):

        self.instrument_strategy = instrument_strategy
        self.optimal_position = optimal_position_object

    def check_instrument_strategies_match(
        self, instrument_strategy_and_position: instrumentStrategyPosition
    ):
        return (
            self.instrument_strategy
            == instrument_strategy_and_position.instrument_strategy
        )

    def key(self):
        return self.instrument_strategy.key

    def is_for_strategy(self, strategy_name: str):
        return self.instrument_strategy.strategy_name == strategy_name


class instrumentStrategyWithOptimalAndCurrentPosition(object):
    def __init__(
        self,
        instrument_strategy_and_optimal_position: instrumentStrategyAndOptimalPosition,
        instrument_strategy_and_position: instrumentStrategyPosition,
    ):
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
        self.instrument_strategy = (
            instrument_strategy_and_optimal_position.instrument_strategy
        )
        self.position = instrument_strategy_and_position.position
        self.optimal_position = (
            instrument_strategy_and_optimal_position.optimal_position
        )

    @property
    def key(self) -> str:
        return self.instrument_strategy.key

    def check_break(self) -> bool:
        # checks to see if current position is outside the limits defined by the optimal position
        return self.optimal_position.check_position_break(self.position)

    def is_for_strategy(self, strategy_name: str):
        return self.instrument_strategy.strategy_name == strategy_name


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
            dict(current=current_positions, optimal=optimal_positions, breaks=breaks),
            index=instrument_strategies,
        )

        return ans


class listOfOptimalPositionsAcrossInstrumentStrategies(list):
    # list of instrumentStrategyAndOptimalPosition
    def filter_by_strategy(self, strategy_name: str):
        filtered_list = [
            instrument_strategy_with_optimal_and_current_position
            for instrument_strategy_with_optimal_and_current_position in self
            if instrument_strategy_with_optimal_and_current_position.is_for_strategy(
                strategy_name
            )
        ]

        return listOfOptimalPositionsAcrossInstrumentStrategies(filtered_list)

    def as_verbose_pd(self) -> pd.DataFrame:
        list_of_optimal = [pos.optimal_position for pos in self]
        list_of_optimal_as_dict = [
            optimal_position.as_dict() for optimal_position in list_of_optimal
        ]
        as_pd = pd.DataFrame(list_of_optimal_as_dict)
        list_of_keys = [pos.key() for pos in self]
        as_pd.index = list_of_keys

        return as_pd

    def as_pd(self) -> pd.DataFrame:
        list_of_keys = [pos.key() for pos in self]
        list_of_optimal = [pos.optimal_position for pos in self]

        return pd.DataFrame(dict(key=list_of_keys, optimal=list_of_optimal))

    def add_positions(
        self, position_list: listOfInstrumentStrategyPositions
    ) -> listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies:

        list_of_optimal_and_current = []
        for opt_pos_object in self:
            instrument_strategy = opt_pos_object.instrument_strategy
            relevant_position_item = (
                position_list.position_object_for_instrument_strategy(
                    instrument_strategy
                )
            )
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
