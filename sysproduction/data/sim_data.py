from syscore.objects import arg_not_supplied

from sysdata.arctic.arctic_and_mongo_sim_futures_data import arcticFuturesSimData
from sysdata.data_blob import dataBlob


class dataSimData(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(arcticFuturesSimData)
        self.data = data

    def sim_data(self):
        return self.data.db_futures_sim
