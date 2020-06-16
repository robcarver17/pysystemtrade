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
_override_lookup = []
for key, value in override_dict.items():
    _override_lookup.append((value, key))

def lookup_value_and_return_float_or_object(value):
    value_list = [entry[1] for entry in _override_lookup if entry[0]==value]
    if len(value_list)==0:
        return value
    else:
        return value_list[0]

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
        value_or_object = lookup_value_and_return_float_or_object(value)

        return Override(value_or_object)

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
        self._overrides = dict(strategy={}, instrument={}, contract={}, strategy_instrument={})

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
        return self._get_override_object_for_key("strategy", strategy_name)

    def get_override_for_strategy_instrument(self, strategy_name, instrument_code):
        key = strategy_name+"/"+instrument_code
        return self._get_override_object_for_key("strategy_instrument", key)

    def get_override_for_instrument(self, instrument_code):
        return self._get_override_object_for_key("instrument", instrument_code)

    def get_override_for_contract_object(self, contract_object):
        key = contract_object.instrument_code + "/" + contract_object.date
        return self._get_override_object_for_key("contracts", key)

    def update_override_for_strategy(self, strategy_name, new_override):
        self._update_override("strategy", strategy_name, new_override)

    def update_override_for_strategy_instrument(self, strategy_name, instrument_code,  new_override):
        key = strategy_name + "/" + instrument_code
        self._update_override("strategy_instrument", key, new_override)

    def update_override_for_instrument(self, instrument_code, new_override):
        self._update_override("instrument", instrument_code, new_override)

    def update_override_for_instrument_and_contractid(self, instrument_code, contract_id, new_override):
        contract_object = futuresContract(instrument_code, contract_id)
        return self.update_override_for_contract_object(contract_object, new_override)

    def update_override_for_contract_object(self, contract_object, new_override):
        key = contract_object.instrument_code + "/" + contract_object.date
        self._update_override("contracts", key, new_override)


    def get_dict_of_all_overrides(self):
        strategy_dict = self.get_dict_of_strategies_with_overrides()
        strategy_instrument_dict = self.get_dict_of_strategy_instrument_with_overrides()
        contract_dict = self.get_dict_of_contracts_with_overrides()
        instrument_dict = self.get_dict_of_instruments_with_overrides()

        all_overrides = {**strategy_dict, **strategy_instrument_dict, **contract_dict, **instrument_dict}

        return all_overrides

    def get_dict_of_strategies_with_overrides(self):
        return self._get_dict_of_items_with_overrides("strategy")

    def get_dict_of_strategy_instrument_with_overrides(self):
        return self._get_dict_of_items_with_overrides("strategy_instrument")

    def get_dict_of_contracts_with_overrides(self):
        return self._get_dict_of_items_with_overrides("contracts")

    def get_dict_of_instruments_with_overrides(self):
        return self._get_dict_of_items_with_overrides("instruments")

    def _update_override(self, dict_name, key, new_override_object):
        self.log.msg("Updating override for %s %s to %s" % (dict_name, key, new_override_object))
        override_dict = self._get_dict_of_items_with_overrides(dict_name)
        override_dict[key] = new_override_object

    def _get_override_object_for_key(self, dict_name, key):
        override_dict = self._get_dict_of_items_with_overrides(dict_name)
        override_object = override_dict.get(key, self.default_override())

        return override_object

    def _get_dict_of_items_with_overrides(self, dict_name):
        return self._overrides[dict_name]

