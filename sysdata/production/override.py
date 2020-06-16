"""
An override is something that affects our normal trading behaviour
"""

from syscore.objects import _named_object
from sysdata.futures.contracts import futuresContract
from syslogdiag.log import logtoscreen

override_close = _named_object("Close")
override_no_trading = _named_object("No trading")
override_reduce_only = _named_object("Reduce only")
override_none = _named_object("No override")

override_dict = {override_close:0.0, override_none: 1.0, override_no_trading:-1.0, override_reduce_only:-2.0}

class Override():
    def __init__(self, value):
        try:
            if value in override_dict.keys():
                self._override = value
            elif type(value) is float or type(value) is int:
                assert value>=0.0
                assert value<=1.0
                self._override = float(value)
            else:
                raise Exception()
        except:
            raise Exception("Override must be between 0.0 and 1.0, or one of the following objects %s" % override_dict)

    def __repr__(self):
        return "Override %s" % str(self._override)

    def as_float(self):
        value = self._override
        if value in override_dict.keys():
            return override_dict[value]
        else:
            return value

    @classmethod
    def from_float(Override, value):
        if type(value) is float:
            return Override(value)

        value_object = list(override_dict.keys())[list(override_dict.values()).index(value)]

        return Override(value_object)

    def __mul__(self, another_override):
        self_value = self._override
        another_value = another_override._override
        if another_value is override_no_trading or self_value is override_no_trading:
            return override_no_trading
        if another_value is override_close or self_value is override_close:
            return override_close
        if another_value is override_reduce_only or self_value is override_reduce_only:
            return override_reduce_only

        assert type(another_value) is float
        assert type(self_value) is float

        return another_value * self_value

DEFAULT_OVERRIDE = Override(1.0)

class overrideData(object):
    def __init__(self, log=logtoscreen("Overrides")):
        self.log = log
        self._strategy_overrides={}
        self._instrument_overrides = {}
        self._strategy_instrument_overrides = {}
        self._contract_overrides = {}

    def default_override(self):
        return DEFAULT_OVERRIDE

    def get_cumulative_override_for_strategy_and_instrument(self, strategy_name, instrument_code):
        strategy_override = self.get_override_for_strategy(strategy_name)
        instrument_override = self.get_override_for_instrument(instrument_code)
        strategy_instrument_override = self.get_override_for_strategy_instrument(strategy_name, instrument_code)

        return Override(strategy_override * instrument_override)*strategy_instrument_override

    def get_cumulative_override_for_instrument_and_contract_id(self, instrument_code, contract_id):
        contract_object = futuresContract(instrument_code, contract_id)

        return self.get_cumulative_override_for_contract_object(contract_object)

    def get_cumulative_override_for_contract_object(self, contract_object):
        instrument_override = self.get_override_for_instrument(contract_object.instrument_code)
        contract_id_override = self.get_override_for_contract_object(contract_object)

        return instrument_override * contract_id_override

    def get_override_for_strategy(self, strategy_name):
        return self._strategy_overrides.get(strategy_name, self.default_override())


    def get_override_for_strategy_instrument(self, strategy_name, instrument_code):
        key = strategy_name+"/"+instrument_code
        return self._strategy_instrument_overrides.get(key, self.default_override())

    def get_override_for_instrument(self, instrument_code):
        return self._instrument_overrides.get(instrument_code, self.default_override())

    def get_override_for_contract_object(self, contract_object):
        key = contract_object.instrument_code + "/" + contract_object.date
        return self._contract_overrides.get(key, self.default_override())

    def update_override_for_strategy(self, strategy_name, new_override):
        self._strategy_overrides[strategy_name] = new_override

    def update_override_for_strategy_instrument(self, strategy_name, instrument_code,  new_override):
        key = strategy_name + "/" + instrument_code
        self._strategy_instrument_overrides[key] = new_override

    def update_override_for_instrument(self, instrument_code, new_override):
        self._instrument_overrides[instrument_code] = new_override

    def update_override_for_instrument_and_contractid(self, instrument_code, contract_id, new_override):
        contract_object = futuresContract(instrument_code, contract_id)
        return self.update_override_for_contract_object(contract_object, new_override)

    def update_override_for_contract_object(self, contract_object, new_override):
        key = contract_object.instrument_code + "/" + contract_object.date
        self._contract_overrides[key] = new_override

    def get_dict_of_strategies_with_overrides(self):
        return self._strategy_overrides

    def get_dict_of_strategy_instrument_with_overrides(self):
        return self._strategy_instrument_overrides

    def get_dict_of_contracts_with_overrides(self):
        return self._contract_overrides

    def get_dict_of_instruments_with_overrides(self):
        return self._instrument_overrides


