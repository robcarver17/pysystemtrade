import pandas as pd
from sysdata.production.historic_orders import (
    strategyHistoricOrdersData,
    contractHistoricOrdersData,
)
from syscore.fileutils import get_filename_for_package
from syscore.objects import arg_not_supplied
from syslogdiag.log import logtoscreen

DATE_INDEX_NAME = "DATETIME"


def from_list_of_orders_to_df(list_of_orders):
    list_as_dict = [order.as_dict() for order in list_of_orders]
    keys = list(list_as_dict[-1].keys())
    key_data = {}
    for key_name in keys:
        key_data[key_name] = [dict_entry[key_name]
                              for dict_entry in list_as_dict]

    index_data = [dict_entry["fill_datetime"] for dict_entry in list_as_dict]
    orders_as_df = pd.DataFrame(key_data, index=index_data)

    return orders_as_df


class csvStrategyHistoricOrdersData(strategyHistoricOrdersData):
    def __init__(self, datapath=arg_not_supplied,
                 log=logtoscreen("csvStrategyPositionData")):

        super().__init__(log=log)

        if datapath is None:
            raise Exception("Need to provide datapath")

        self._datapath = datapath

    def write_orders(self, list_of_orders):
        filename = get_filename_for_package(
            self._datapath, "%s.csv" % ("strategy_orders")
        )
        df = from_list_of_orders_to_df(list_of_orders)
        df.to_csv(filename, index_label=DATE_INDEX_NAME)


class csvContractHistoricOrdersData(contractHistoricOrdersData):
    def __init__(self, datapath=arg_not_supplied,
                 log=logtoscreen("csvContractPositionData")):

        super().__init__(log=log)

        if datapath is None:
            raise Exception("Need to provide datapath")

        self._datapath = datapath

    def write_orders(self, list_of_orders):
        filename = get_filename_for_package(
            self._datapath, "%s.csv" % ("contract_orders")
        )
        df = from_list_of_orders_to_df(list_of_orders)
        df.to_csv(filename, index_label=DATE_INDEX_NAME)


class csvBrokerHistoricOrdersData(contractHistoricOrdersData):
    def __init__(self, datapath=arg_not_supplied,
                 log=logtoscreen("csvBrokerHistoricOrdersData")):

        super().__init__(log=log)

        if datapath is None:
            raise Exception("Need to provide datapath")

        self._datapath = datapath

    def write_orders(self, list_of_orders):
        filename = get_filename_for_package(
            self._datapath, "%s.csv" % ("broker_orders")
        )
        df = from_list_of_orders_to_df(list_of_orders)
        df.to_csv(filename, index_label=DATE_INDEX_NAME)
