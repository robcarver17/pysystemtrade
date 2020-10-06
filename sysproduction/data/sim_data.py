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
