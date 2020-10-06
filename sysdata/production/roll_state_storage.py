from syscore.objects import _named_object
from sysdata.data import baseData
from syslogdiag.log import logtoscreen

roll_states = [
    "No_Roll",
    "Passive",
    "Force",
    "Force_Outright",
    "Roll_Adjusted"]

default_state = roll_states[0]
roll_adj_state = roll_states[4]

roll_explanations = dict(
    No_Roll="No rolling happens. Will only trade priced contract.",
    Passive="Allow the contract to roll naturally (closing trades in priced contract, opening trades in forward contract)",
    Force="Force the contract to roll ASAP using spread order",
    Force_Outright="Force the contract to roll ASAP using two outright orders",
    Roll_Adjusted="Roll adjusted prices from existing priced to new forward contract (after adjusted prices have been changed, will automatically move state to no roll",
)


def explain_roll_state(roll_state):
    return roll_explanations[roll_state]


def complete_roll_state(roll_state, priced_position):
    if priced_position == 0:
        position_in_priced = 0
    else:
        position_in_priced = 1

    return "%s%s" % (roll_state, position_in_priced)


def allowable_roll_state_from_current_and_position(
        current_roll_state, priced_position):
    try:
        assert current_roll_state in roll_states
    except BaseException:
        raise Exception(
            "Current roll state %s not in allowable list %s"
            % (current_roll_state, str(roll_states))
        )
    # Transition matrix: First option is recommended
    allowed_transition = dict(
        No_Roll0=["Roll_Adjusted", "Passive", "No_Roll"],
        No_Roll1=["Passive", "Force", "Force_Outright", "No_Roll"],
        Passive0=["Roll_Adjusted", "Passive", "No_Roll"],
        Passive1=["Force", "Force_Outright", "Passive", "No_Roll"],
        Force0=["Roll_Adjusted", "Passive"],
        Force1=["Force", "Force_Outright", "Passive", "No_Roll"],
        Force_Outright0=["Roll_Adjusted", "Passive"],
        Force_Outright1=["Force", "Force_Outright", "Passive", "No_Roll"],
        Roll_Adjusted0=["No_Roll"],
        Roll_Adjusted1=["Roll_Adjusted"],
    )

    status_plus_position = complete_roll_state(
        current_roll_state, priced_position)
    try:
        allowable_states = allowed_transition[status_plus_position]
    except KeyError:
        raise Exception(
            "State plus position %s not recognised" %
            status_plus_position)

    return allowable_states


no_state_available = _named_object("No state")


class rollStateData(baseData):
    """
    Store and retrieve the roll state of a particular instrument
    """

    def __init__(self, log=logtoscreen("rollStateData")):

        super().__init__(log=log)

        self.name = "rollStateData"

    def get_roll_state(self, instrument_code):
        state = self._get_roll_state_no_default(instrument_code)
        if state is no_state_available:
            state = default_state
            self.set_roll_state(instrument_code, state)

        return state

    def _get_roll_state_no_default(self, instrument_code):
        raise NotImplementedError("Need to use inheriting class")

    @property
    def roll_states(self):
        return roll_states

    def set_roll_state(self, instrument_code, new_roll_state):
        try:
            assert new_roll_state in roll_states
        except BaseException:
            raise Exception(
                "New roll state %s not in %s" %
                (new_roll_state, str(roll_states)))

        self._set_roll_state_without_checking(instrument_code, new_roll_state)

    def _set_roll_state_without_checking(
            self, instrument_code, new_roll_state):
        raise NotImplementedError("Need to use inheriting class")
