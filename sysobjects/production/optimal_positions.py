from dataclasses import dataclass
import pandas as pd
import datetime

from sysobjects.production.positions import (
    instrumentStrategyPosition,
    listOfInstrumentStrategyPositions,
)
from sysobjects.production.tradeable_object import instrumentStrategy


## ALWAYS INHERIT FROM THIS: See important note below for why
@dataclass
class baseOptimalPosition:
    ## Don't actually use
    date: datetime.datetime

    def check_position_break(self, position: float):
        raise NotImplementedError

    @classmethod
    def from_dict(cls, inputs_as_dict: dict):
        return cls(**inputs_as_dict)

    def as_df_row(self):
        return pd.DataFrame(self.as_dict(), index=[self.date])

    def as_dict(self) -> dict:
        return dict([(key, getattr(self, key)) for key in self.fields])

    @property
    def fields(self) -> list:
        return optimal_position_fields(self)


def optimal_position_fields(optimal_position_class) -> list:
    fields = list(optimal_position_class.__dataclass_fields__.keys())
    fields.remove("date")

    return fields


# DO NOT INHERIT FROM ME, ONLY FROM baseOptimalPosition
@dataclass
class simpleOptimalPosition(baseOptimalPosition):
    """
    This is the simplest possible optimal positions object

    """

    date: datetime.datetime
    position: float

    def check_position_break(self, position: float):
        return position == self.position


# DO NOT INHERIT FROM ME, ONLY FROM baseOptimalPosition
@dataclass
class bufferedOptimalPositions(baseOptimalPosition):
    """
    Here is one with buffers

    """

    date: datetime.datetime
    lower_position: float
    upper_position: float
    reference_price: float
    reference_contract: str

    def _argument_checks(self):
        # run on __init__ by parent class
        upper_position = self.upper_position
        lower_position = self.lower_position

        try:
            assert upper_position >= lower_position
        except BaseException:
            raise Exception(
                "Upper position %f  has to be >= than lower position %f"
                % (upper_position, lower_position)
            )

    def check_position_break(self, position: int):
        self._argument_checks()
        # ignore warnings set dynamically
        return position < round(self.lower_position) or position > round(
            self.upper_position
        )

    def __repr__(self):
        return "%.3f/%.3f" % (self.lower_position, self.upper_position)


# DO NOT INHERIT FROM ME, ONLY FROM baseOptimalPosition
@dataclass
class optimalPositionWithReference(baseOptimalPosition):
    date: datetime.datetime
    optimal_position: float
    reference_price: float
    reference_contract: str
    reference_date: datetime.datetime

    def check_position_break(self, position: int):
        return False

    def __repr__(self):
        return "%.3f" % (self.optimal_position)


# DO NOT INHERIT FROM ME, ONLY FROM baseOptimalPosition
@dataclass
class optimalPositionWithDynamicCalculations(baseOptimalPosition):
    date: datetime.datetime
    reference_price: float
    reference_contract: str
    reference_date: datetime.datetime
    optimal_position: float
    weight_per_contract: float
    previous_position: float
    previous_weight: float
    reduce_only: bool
    dont_trade: bool
    position_limit_contracts: float
    position_limit_weight: float
    optimum_weight: float
    minimum_weight: float
    maximum_weight: float
    start_weight: float
    optimised_weight: float
    optimised_position: int

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

        if self.dont_trade:
            logic_str = "(NoTrading) "
        elif self.reduce_only:
            logic_str = "(ReduceOnly) "
        else:
            logic_str = ""

        return ref_str + logic_str + pos_str + weight_str

    def check_position_break(self, position: int):
        optimised_position = self.optimised_position
        if position != optimised_position:
            return True
        else:
            return False

    def __repr__(self):
        return "%d" % (self.optimised_position)


def from_df_row_to_optimal_position(df_row: pd.Series) -> baseOptimalPosition:
    df_row_as_dict = dict(df_row.to_dict())  ## avoid stupid pd warnings
    list_of_fields = list(df_row_as_dict.keys())
    appropriate_class = infer_class_of_optimal_position_from_field_list(list_of_fields)
    df_row_as_dict["date"] = df_row.name

    return appropriate_class.from_dict(df_row_as_dict)


def add_optimal_position_entry_row_to_positions_as_df(
    existing_optimal_positions_as_df: pd.DataFrame,
    position_entry: simpleOptimalPosition,
) -> pd.DataFrame:
    _check_append_positions_okay(
        existing_optimal_positions_as_df=existing_optimal_positions_as_df,
        position_entry=position_entry,
    )

    position_entry_as_df_row = position_entry.as_df_row()
    updated_optimal_df = pd.concat(
        [existing_optimal_positions_as_df, position_entry_as_df_row]
    )

    return updated_optimal_df


def _check_append_positions_okay(
    existing_optimal_positions_as_df: pd.DataFrame,
    position_entry: simpleOptimalPosition,
):
    list_of_fields_for_existing_position_entries = list(
        existing_optimal_positions_as_df.columns
    )
    class_of_existing_position_entries = (
        infer_class_of_optimal_position_from_field_list(
            list_of_fields_for_existing_position_entries
        )
    )

    try:
        assert class_of_existing_position_entries is type(position_entry)
    except:
        raise Exception(
            "Class of existing optimal positions is %s, new position entry is type %s"
            % (str(class_of_existing_position_entries), str(type(position_entry)))
        )

    final_date_index = existing_optimal_positions_as_df.index[-1]

    try:
        assert final_date_index < position_entry.date
    except:
        raise Exception(
            "Can't add a position entry which is younger than the last position entry"
        )


## IMPORTANT NOTE: if you create a new kind of optimal position which does not inherit from
##    baseOptimalPosition directly, need to manually add it here

MASTER_LIST_OF_OPTIMAL_POSITION_CLASSES = baseOptimalPosition.__subclasses__()


def _class_matches_field_list(position_class, sorted_set_of_fields: set):
    dataclass_fields = optimal_position_fields(position_class)
    dataclass_fields.sort()
    dataclass_fields_as_set = set(dataclass_fields)

    return dataclass_fields_as_set == sorted_set_of_fields


def infer_class_of_optimal_position_from_field_list(list_of_fields: list):
    list_of_fields.sort()
    sorted_set_of_fields = set(list_of_fields)
    matching_classes = [
        position_class
        for position_class in MASTER_LIST_OF_OPTIMAL_POSITION_CLASSES
        if _class_matches_field_list(position_class, sorted_set_of_fields)
    ]
    if len(matching_classes) == 0:
        raise Exception(
            "Data fields %s do not match any optimal position class"
            % str(list_of_fields)
        )
    if len(matching_classes) > 1:
        raise Exception(
            "Data fields %s match multiple optimal position classes"
            % str(list_of_fields)
        )

    return matching_classes[0]


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
        return self.strategy_name == strategy_name

    @property
    def strategy_name(self) -> str:
        return self.instrument_strategy.strategy_name

    @property
    def instrument_code(self) -> str:
        return self.instrument_strategy.instrument_code


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
    def filter_removing_strategies(self, list_of_strategies_to_remove):
        filtered_list = [
            instrument_strategy_with_optimal_and_current_position
            for instrument_strategy_with_optimal_and_current_position in self
            if instrument_strategy_with_optimal_and_current_position.strategy_name
            not in list_of_strategies_to_remove
        ]

        return listOfOptimalPositionsAcrossInstrumentStrategies(filtered_list)

    def filter_removing_instruments(self, list_of_instruments_to_remove):
        filtered_list = [
            instrument_strategy_with_optimal_and_current_position
            for instrument_strategy_with_optimal_and_current_position in self
            if instrument_strategy_with_optimal_and_current_position.instrument_code
            not in list_of_instruments_to_remove
        ]

        return listOfOptimalPositionsAcrossInstrumentStrategies(filtered_list)

    def list_of_strategies(self) -> list:
        list_of_strategies = [position.strategy_name for position in self]

        return list_of_strategies

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
