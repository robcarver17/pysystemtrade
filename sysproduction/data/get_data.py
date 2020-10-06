# Get all the data we need to run production code
# Stick in a standard 'blob', so the names are common

from copy import copy

from sysbrokers.IB.ibFuturesContractPriceData import ibFuturesContractPriceData
from sysbrokers.IB.ibSpotFXData import ibFxPricesData
from sysbrokers.IB.ibConnection import connectionIB
from sysbrokers.IB.ibFuturesContracts import ibFuturesContractData
from sysbrokers.IB.ibPositionData import ibContractPositionData
from sysbrokers.IB.ibOrders import ibOrdersData
from sysbrokers.IB.ibMiscData import ibMiscData

from sysdata.arctic.arctic_futures_per_contract_prices import (
    arcticFuturesContractPriceData,
)
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.arctic.arctic_and_mongo_sim_futures_data import arcticFuturesSimData

from sysdata.csv.csv_futures_contract_prices import csvFuturesContractPriceData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.csv.csv_spot_fx import csvFxPricesData
from sysdata.csv.csv_contract_position_data import csvContractPositionData
from sysdata.csv.csv_strategy_position_data import csvStrategyPositionData
from sysdata.csv.csv_historic_orders import (
    csvBrokerHistoricOrdersData,
    csvContractHistoricOrdersData,
    csvStrategyHistoricOrdersData,
)
from sysdata.csv.csv_capital_data import csvCapitalData
from sysdata.csv.csv_optimal_position import csvOptimalPositionData
from sysdata.csv.csv_instrument_config import csvFuturesInstrumentData
from sysdata.csv.csv_roll_state_storage import csvRollStateData
from sysdata.csv.csv_futures_contracts import csvFuturesContractData

from sysdata.mongodb.mongo_futures_instruments import mongoFuturesInstrumentData
from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData
from sysdata.mongodb.mongo_roll_state_storage import mongoRollStateData
from sysdata.mongodb.mongo_position_by_contract import mongoContractPositionData
from sysdata.mongodb.mongo_capital import mongoCapitalData
from sysdata.mongodb.mongo_optimal_position import mongoOptimalPositionData
from sysdata.mongodb.mongo_positions_by_strategy import mongoStrategyPositionData
from sysdata.mongodb.mongo_order_stack import (
    mongoInstrumentOrderStackData,
    mongoContractOrderStackData,
    mongoBrokerOrderStackData,
)
from sysdata.mongodb.mongo_historic_orders import (
    mongoStrategyHistoricOrdersData,
    mongoContractHistoricOrdersData,
    mongoBrokerHistoricOrdersData,
)
from sysdata.mongodb.mongo_override import mongoOverrideData
from sysdata.mongodb.mongo_trade_limits import mongoTradeLimitData
from sysdata.mongodb.mongo_lock_data import mongoLockData
from sysdata.mongodb.mongo_process_control import mongoControlProcessData
from sysdata.mongodb.mongo_log import mongoLogData
from sysdata.mongodb.mongo_email_control import mongoEmailControlData

from sysdata.mongodb.mongo_connection import mongoDb

from sysdata.mongodb.mongo_connection import mongoDb

from sysdata.mongodb.mongo_log import logToMongod as logger
from syscore.objects import arg_not_supplied, success, failure


class dataBlob(object):
    def __init__(
        self,
        arg_string=arg_not_supplied,
        log_name="",
        csv_data_paths=arg_not_supplied,
        ib_conn=arg_not_supplied,
        mongo_db=arg_not_supplied,
        log=arg_not_supplied,
        keep_original_prefix=False,
    ):
        """
        Set up of a data pipeline with standard attribute names, logging, links to DB etc

        Class names we know how to handle are:
        'ib*', 'mongo*', 'arctic*', 'csv*'

            data = dataBlob("arcticFuturesContractPriceData arcticFuturesContractPriceData mongoFuturesContractData')

        .... sets up the following equivalencies:

            data.broker_contract_price  = ibFuturesContractPriceData(ib_conn, log=log.setup(component="IB-price-data"))
            data.db_futures_contract_price = arcticFuturesContractPriceData(mongo_db=mongo_db,
                                                      log=log.setup(component="arcticFuturesContractPriceData"))
            data.db_futures_contract = mongoFuturesContractData(mongo_db=mongo_db,
                                                   log = log.setup(component="mongoFuturesContractData"))

        This abstracts the precise data source

        :param arg_string: str like a named tuple in the form 'classNameOfData1 classNameOfData2' and so on
        :param log_name: logger type to set
        :param keep_original_prefix: bool. If True then:

            data = dataBlob("arcticFuturesContractPriceData arcticFuturesContractPriceData mongoFuturesContractData')

        .... sets up the following equivalencies. This is useful if you are copying from one source to another

            data.ib_contract_price  = ibFuturesContractPriceData(ib_conn, log=log.setup(component="IB-price-data"))
            data.arctic_futures_contract_price = arcticFuturesContractPriceData(mongo_db=mongo_db,
                                                      log=log.setup(component="arcticFuturesContractPriceData"))
            data.mongo_futures_contract = mongoFuturesContractData(mongo_db=mongo_db,
                                                   log = log.setup(component="mongoFuturesContractData"))



        """

        self._mongo_db = mongo_db
        self._ib_conn = ib_conn
        self._log = log
        self._log_name = log_name
        self._csv_data_paths = csv_data_paths
        self.keep_original_prefix = keep_original_prefix
        self.attr_list = []
        self.class_list = []

        if arg_string is arg_not_supplied:
            # can set up dynamically later
            pass
        else:
            self.add_class_list(arg_string)

        self._original_data = copy(self)

    def __repr__(self):
        return "dataBlob with elements: %s" % ",".join(self.attr_list)

    """
    Following two methods implement context manager
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self._ib_conn is not arg_not_supplied:
            self.ib_conn.close_connection()

        if self._mongo_db is not arg_not_supplied:
            self.mongo_db.close()

    @property
    def ib_conn(self):
        ib_conn = getattr(self, "_ib_conn", arg_not_supplied)
        if ib_conn is arg_not_supplied:
            ib_conn = connectionIB()
            self._ib_conn = ib_conn

        return ib_conn

    @property
    def mongo_db(self):
        mongo_db = getattr(self, "_mongo_db", arg_not_supplied)
        if mongo_db is arg_not_supplied:
            mongo_db = mongoDb()
            self._mongo_db = mongo_db

        return mongo_db

    @property
    def log(self):
        log = getattr(self, "_log", arg_not_supplied)
        if log is arg_not_supplied:
            log = logger(self._log_name, data=self, mongo_db=self.mongo_db)
            log.set_logging_level("on")
            self._log = log

        return log

    @property
    def log_name(self):
        return self.log.attributes["type"]

    def setup_clone(self, **kwargs):
        new_data = self._original_data
        new_data._log = new_data.log.setup(**kwargs)
        new_data._original_data = self._original_data

        return new_data

    @property
    def csv_data_paths(self):
        csv_data_paths = getattr(self, "_csv_data_paths", arg_not_supplied)
        if csv_data_paths is arg_not_supplied:
            raise Exception("No defaults for csv data paths")
        return csv_data_paths

    def add_class_list(self, arg_string):
        list_of_classes = arg_string.split(" ")

        for class_name in list_of_classes:
            self._add_class_element(class_name)
        return success

    def _add_class_element(self, class_name):
        if class_name in self.class_list:
            # Already present
            return success

        if len(class_name) == 0:
            return failure

        attr_name, resolved_instance = self.process_class_id(class_name)
        setattr(self, attr_name, resolved_instance)

        self.attr_list.append(attr_name)
        self.class_list.append(class_name)

        return success

    def process_class_id(self, class_name):
        """

        :param class_name: name of class to add to data

        :return: 2 tuple: identifying attribute name str, instance of class
        """

        split_up_name = camel_case_split(class_name)
        prefix = split_up_name[0]

        # NEED TO DYNAMICALLY SWITCH DB SOURCE AND ADD DEFAULT CSV PATH NAME
        # REMOVE SOURCE_ PREFIX, REPLACE WITH db_ or broker_
        if prefix == "csv":
            csv_data_paths = self.csv_data_paths
            if csv_data_paths is arg_not_supplied:
                raise Exception(
                    "Need csv_data_paths dict for class name %s" % class_name
                )
            datapath = csv_data_paths.get(class_name, "")
            if datapath == "":
                raise Exception(
                    "Need to have key %s in csv_data_paths" %
                    class_name)

        eval_dict = dict(
            ib="%s(self.ib_conn, log=self.log.setup(component='%s'))",
            mongo="%s(mongo_db=self.mongo_db, log=self.log.setup(component='%s'))",
            arctic="%s(mongo_db=self.mongo_db, log=self.log.setup(component='%s'))",
            csv="%s(datapath=datapath, log=self.log.setup(component='%s'))",
        )

        to_eval = eval_dict[prefix] % (
            class_name,
            class_name,
        )  # class_name appears twice as always passed as a log
        # The eval may use ib_conn, mongo_db, datapath and will always use log
        try:
            resolved_instance = eval(to_eval)
        except BaseException:
            msg = (
                "Couldn't evaluate %s This might be because (a) IB gateway not running, or (b) it is missing from sysproduction.data.get_data imports or arguments don't follow pattern" %
                to_eval)
            self.log.critical(msg)
            raise Exception(msg)

        keep_original_prefix = self.keep_original_prefix

        attr_name = identifying_name(
            split_up_name, keep_original_prefix=keep_original_prefix
        )

        return attr_name, resolved_instance


source_dict = dict(arctic="db", mongo="db", csv="db", ib="broker")


def identifying_name(split_up_name, keep_original_prefix=False):
    """
    Turns sourceClassNameData into broker_class_name or db_class_name

    :param split_up_name: list eg source, class,name,data
    :return: str, class_name
    """
    lower_split_up_name = [x.lower() for x in split_up_name]
    data_label = lower_split_up_name.pop(-1)  # always 'data'
    original_source_label = lower_split_up_name.pop(
        0
    )  # always the source, eg csv, ib, mongo or arctic

    try:
        assert data_label == "data"
    except BaseException:
        raise Exception(
            "Get_data strings only work if class name ends in ...Data")

    if keep_original_prefix:
        source_label = original_source_label
    else:
        try:
            source_label = source_dict[original_source_label]
        except BaseException:
            raise Exception(
                "Only works with classes that begin with one of %s"
                % str(source_dict.keys())
            )

    lower_split_up_name = [source_label] + lower_split_up_name

    return "_".join(lower_split_up_name)


def camel_case_split(str):
    words = [[str[0]]]

    for c in str[1:]:
        if words[-1][-1].islower() and c.isupper():
            words.append(list(c))
        else:
            words[-1].append(c)

    return ["".join(word) for word in words]
