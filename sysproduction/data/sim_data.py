from syscore.objects import arg_not_supplied
from syscore.genutils import get_and_convert
from sysproduction.data.get_data import dataBlob
from sysdata.private_config import get_private_then_default_key_value

class dataSimData(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("arcticFuturesSimData")
        self.data = data

    def sim_data(self):
        return self.data.db_futures_sim

def get_list_of_strategies():
    strategy_dict = get_private_then_default_key_value('strategy_list')
    return list(strategy_dict.keys())


def get_valid_strategy_name_from_user():
    all_strategies = get_list_of_strategies()
    invalid_input = True
    while invalid_input:
        print("Strategies: %s" % all_strategies)
        default_strategy = all_strategies[0]
        strategy_name = get_and_convert("Strategy?", type_expected=str, default_value=default_strategy)
        if strategy_name in all_strategies:
            return strategy_name

        print("%s is not in list %s" % (strategy_name, all_strategies))
