from copy import copy

from sysbrokers.IB.ib_connection import connectionIB
from syscore.objects import arg_not_supplied, get_class_name
from syscore.text import camel_case_split
from sysdata.config.production_config import get_production_config, Config
from sysdata.mongodb.mongo_connection import mongoDb
from sysdata.mongodb.mongo_log import logToMongod
from syslogdiag.logger import logger

from sysdata.mongodb.mongo_IB_client_id import mongoIbBrokerClientIdData

class dataBlob(object):
    def __init__(
        self,
        class_list: list=arg_not_supplied,
        log_name: str="",
        csv_data_paths: dict=arg_not_supplied,
        ib_conn: connectionIB=arg_not_supplied,
        mongo_db: mongoDb=arg_not_supplied,
        log: logger=arg_not_supplied,
        keep_original_prefix: bool=False,
    ):
        """
        Set up of a data pipeline with standard attribute names, logging, links to DB etc

        Class names we know how to handle are:
        'ib*', 'mongo*', 'arctic*', 'csv*'

            data = dataBlob([arcticFuturesContractPriceData, arcticFuturesContractPriceData, mongoFuturesContractData])

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

            data = dataBlob([arcticFuturesContractPriceData, arcticFuturesContractPriceData, mongoFuturesContractData])

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
        self._keep_original_prefix = keep_original_prefix

        self._attr_list = []

        if class_list is arg_not_supplied:
            # can set up dynamically later
            pass
        else:
            self.add_class_list(class_list)

        self._original_data = copy(self)

    def __repr__(self):
        return "dataBlob with elements: %s" % ",".join(self._attr_list)


    def add_class_list(self, class_list: list):
        for class_object in class_list:
            self.add_class_object(class_object)

    def add_class_object(self, class_object):
        resolved_instance = self._get_resolved_instance_of_class(class_object)
        class_name = get_class_name(class_object)
        self._resolve_names_and_add(resolved_instance, class_name)

    def _get_resolved_instance_of_class(self, class_object):
        class_adding_method = self._get_class_adding_method(class_object)
        resolved_instance = class_adding_method(class_object)

        return resolved_instance


    def _get_class_adding_method(self, class_object):
        prefix = self._get_class_prefix(class_object)
        class_dict = dict(ib = self._add_ib_class, csv = self._add_csv_class, arctic = self._add_arctic_class,
                          mongo = self._add_mongo_class)

        method_to_add_with = class_dict.get(prefix, None)
        if method_to_add_with is None:
            error_msg = "Don't know how to handle object named %s" % get_class_name(class_object)
            self._raise_and_log_error(error_msg)

        return method_to_add_with

    def _get_class_prefix(self, class_object) -> str:
        class_name = get_class_name(class_object)
        split_up_name = camel_case_split(class_name)
        prefix = split_up_name[0]

        return prefix

    def _add_ib_class(self, class_object):
        log = self._get_specific_logger(class_object)
        try:
            resolved_instance = class_object(self.ib_conn, log = log)
        except Exception as e:
                class_name = get_class_name(class_object)
                msg = (
                        "Error %s couldn't evaluate %s(self.ib_conn, log = self.log.setup(component = %s)) This might be because (a) IB gateway not running, or (b) import is missing\
                         or (c) arguments don't follow pattern" % (str(e), class_name, class_name))
                self._raise_and_log_error(msg)

        return resolved_instance

    def _add_mongo_class(self, class_object):
        log = self._get_specific_logger(class_object)
        try:
            resolved_instance = class_object(mongo_db=self.mongo_db, log = log)
        except Exception as e:
                class_name = get_class_name(class_object)
                msg = (
                        "Error '%s' couldn't evaluate %s(mongo_db=self.mongo_db, log = self.log.setup(component = %s)) \
                        This might be because import is missing\
                         or arguments don't follow pattern" % (str(e), class_name, class_name))
                self._raise_and_log_error(msg)

        return resolved_instance

    def _add_arctic_class(self, class_object):
        log = self._get_specific_logger(class_object)
        try:
            resolved_instance = class_object(mongo_db=self.mongo_db, log = log)
        except Exception as e:
                class_name = get_class_name(class_object)
                msg = (
                        "Error %s couldn't evaluate %s(mongo_db=self.mongo_db, log = self.log.setup(component = %s)) \
                        This might be because import is missing\
                         or arguments don't follow pattern" % (str(e), class_name, class_name))
                self._raise_and_log_error(msg)

        return resolved_instance

    def _add_csv_class(self, class_object):
        datapath = self._get_csv_paths_for_class(class_object)
        log = self._get_specific_logger(class_object)

        try:
            resolved_instance = class_object(datapath = datapath, log = log)
        except Exception as e:
                class_name = get_class_name(class_object)
                msg = (
                        "Error %s couldn't evaluate %s(datapath = datapath, log = self.log.setup(component = %s)) \
                        This might be because import is missing\
                         or arguments don't follow pattern" % (str(e), class_name, class_name))
                self._raise_and_log_error(msg)

        return resolved_instance

    def _get_csv_paths_for_class(self, class_object) -> str:
        class_name = get_class_name(class_object)
        csv_data_paths = self.csv_data_paths
        if csv_data_paths is arg_not_supplied:
            self.log.warn("No datapaths provided for .csv, will use defaults  (may break in production, should be fine in sim)")
            return arg_not_supplied

        datapath = csv_data_paths.get(class_name, "")
        if datapath == "":
            self.log.warn(
                "No key for %s in csv_data_paths, will use defaults (may break in production, should be fine in sim)" %
                class_name)
            return arg_not_supplied

        return datapath

    @property
    def csv_data_paths(self) -> dict:
        csv_data_paths = getattr(self, "_csv_data_paths", arg_not_supplied)

        return csv_data_paths

    def _get_specific_logger(self, class_object):
        class_name = get_class_name(class_object)
        log = self.log.setup(component = class_name)

        return log

    def _resolve_names_and_add(self, resolved_instance, class_name: str):
        attr_name = self._get_new_name(class_name)
        self._add_new_class_with_new_name(resolved_instance, attr_name)

    def _get_new_name(self, class_name: str) -> str:
        split_up_name = camel_case_split(class_name)
        attr_name = identifying_name(
            split_up_name, keep_original_prefix=self._keep_original_prefix
        )

        return attr_name

    def _add_new_class_with_new_name(self, resolved_instance, attr_name:str):
        already_exists = self._already_existing_class_name(attr_name)
        if already_exists:
            ## not uncommon don't log or would be a sea of span
            pass
        else:
            setattr(self, attr_name, resolved_instance)
            self._add_attr_to_list(attr_name)

    def _already_existing_class_name(self, attr_name: str):
        existing_attr = getattr(self, attr_name, None)
        if existing_attr is None:
            return False
        else:
            return True


    def _add_attr_to_list(self, new_attr: str):
        self._attr_list.append(new_attr)

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
            self.db_ib_broker_client_id.release_clientid(
                self.ib_conn.client_id())

        # No need to explicitly close Mongo connections; handled by Python garbage collection

    @property
    def ib_conn(self) -> connectionIB:
        ib_conn = getattr(self, "_ib_conn", arg_not_supplied)
        if ib_conn is arg_not_supplied:
            ib_conn = self._get_new_ib_connection()
            self._ib_conn = ib_conn

        return ib_conn

    def _get_new_ib_connection(self) -> connectionIB:
        client_id = self._get_next_client_id_for_ib()

        ib_conn = connectionIB(client_id,
                               log=self.log)
        return ib_conn

    def _get_next_client_id_for_ib(self) -> int:
        ## default to tracking ID through mongo change if required
        self.add_class_object(mongoIbBrokerClientIdData)
        client_id = self.db_ib_broker_client_id.return_valid_client_id()

        return int(client_id)

    @property
    def mongo_db(self) -> mongoDb:
        mongo_db = getattr(self, "_mongo_db", arg_not_supplied)
        if mongo_db is arg_not_supplied:
            mongo_db= self._get_new_mongo_db()
            self._mongo_db = mongo_db

        return mongo_db

    def _get_new_mongo_db(self) -> mongoDb:
        mongo_db = mongoDb()

        return mongo_db

    @property
    def config(self) -> Config:
        config = getattr(self, "_config", None)
        if config is None:
            config = self._config = get_production_config()

        return config

    def _raise_and_log_error(self, error_msg: str):
        self.log.critical(error_msg)
        raise Exception(error_msg)

    @property
    def log(self):
        log = getattr(self, "_log", arg_not_supplied)
        if log is arg_not_supplied:
            log = logToMongod(self.log_name, mongo_db=self.mongo_db, data = self)
            log.set_logging_level("on")
            self._log = log

        return log

    @property
    def log_name(self) -> str:
        log_name = getattr(self, "_log_name", "")
        return log_name


source_dict = dict(arctic="db", mongo="db", csv="db", ib="broker")


def identifying_name(split_up_name: list, keep_original_prefix=False)-> str:
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


