from syscore.objects import _named_object
from sysdata.data import baseData
from syslogdiag.log import logtoscreen

roll_states = ['No roll', 'Passive', 'Force']
default_state = roll_states[0]
no_state_available = _named_object("No state")

class rollStateData(baseData):
    """
    Store and retrieve the roll state of a particular instrument
    """
    def __init__(self, log=logtoscreen("rollStateData")):

        super().__init__(log=log)

        self._roll_dict={}
        self.name = "rollStateData"


    def get_roll_state(self, instrument_code):
        state = self._get_roll_state_no_default(instrument_code)
        if state is no_state_available:
            state = default_state
            self.set_roll_state(instrument_code, state)

        return state

    def _get_roll_state_no_default(self, instrument_code):
        state = self._roll_dict.get(instrument_code, no_state_available)

        return state

    def set_roll_state(self, instrument_code, new_roll_state):
        try:
            assert new_roll_state in roll_states
        except:
            raise Exception("New roll state %s not in %s" % (new_roll_state, str(roll_states)))

        self._set_roll_state_without_checking(instrument_code, new_roll_state)

    def _set_roll_state_without_checking(self, instrument_code, new_roll_state):
        self._roll_dict[instrument_code] = new_roll_state

