from syscore.objects import resolve_function, missing_data
from sysdata.data_blob import dataBlob
from sysproduction.data.control_process import get_strategy_class_object_config

def get_strategy_method(data: dataBlob,  strategy_name: str, process_name: str, function_name: str):
    config_this_process = get_strategy_class_object_config(data, process_name, strategy_name)
    strategy_class_object = resolve_function(config_this_process.pop("object"))

    # following are used by run process but not by us
    _ = config_this_process.pop("max_executions", None)
    _ = config_this_process.pop("frequency", None)

    # might be in old config files
    unused_config_function = config_this_process.pop("function", None)
    if unused_config_function is not None:
        #FIXME REMOVE CHECK AT SOME POINT
        data.log.warn("Remove function from strategy run_systems configuration no longer uses!")

    other_args = config_this_process

    strategy_data = dataBlob(log_name=process_name)
    strategy_data.log.label(strategy_name=strategy_name)

    strategy_class_instance = strategy_class_object(
        strategy_data, strategy_name, **other_args
    )
    method = getattr(strategy_class_instance, function_name)

    return method


class strategyRunner():
    ## needs to have method per strategy
    def __init__(self, data: dataBlob, strategy_name: str, process_name: str, function_name: str):
        self.data = data
        self._object_store = missing_data
        self._strategy_name = strategy_name
        self._function_name = function_name
        self._process_name = process_name

    @property
    def strategy_name(self):
        return self._strategy_name

    @property
    def function_name(self):
        return self._function_name

    @property
    def process_name(self):
        return self._process_name

    @property
    def object_store(self):
        return self._object_store

    @object_store.setter
    def object_store(self, new_object):
        self._object_store = new_object

    def run_strategy_method(self):
        method = self.get_strategy_method()
        # no arguments. no return. no explanations
        method()

    def get_strategy_method(self):
        method = self._object_store
        if method is missing_data:
            method = get_strategy_method(self.data, self.strategy_name, self.process_name, self.function_name)
            self.object_store = method

        return method