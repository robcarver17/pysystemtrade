### Get all the data we need to run production code
### Stick in a standard 'blob', so the names are common

from sysbrokers.IB.ibFuturesContractPriceData import ibFuturesContractPriceData
from sysbrokers.IB.ibSpotFXData import ibFxPricesData

from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData

from sysdata.csv.csv_futures_contract_prices import csvFuturesContractPriceData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.csv.csv_spot_fx import csvFxPricesData

from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData
from sysdata.mongodb.mongo_roll_state_storage import mongoRollStateData
from sysdata.mongodb.mongo_position_by_contract_state import mongoPositionByContractData
from sysdata.mongodb.mongo_capital import mongoCapitalData
from sysdata.mongodb.mongo_optimal_position import mongoOptimalPositionData

from sysdata.mongodb.mongo_connection import mongoDb

from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData


from sysdata.mongodb.mongo_connection import mongoDb

from syslogdiag.log import logtoscreen
from syscore.objects import arg_not_supplied, success, failure


class dataBlob(object):
    def __init__(self, arg_string=arg_not_supplied, mongo_db=arg_not_supplied, ib_conn=arg_not_supplied,
                 csv_data_paths=arg_not_supplied, log=logtoscreen("")):
        """
        Set up of a data pipeline with standard attribute names, logging, links to DB etc

        Class names we know how to handle are:
        'ib*', 'mongo*', 'arctic*', 'csv*'

        So: "arcticFuturesContractPriceData arcticFuturesContractPriceData mongoFuturesContractData'

        .... is equivalent of this sort of thing:
            ib_pricedata = ibFuturesContractPriceData(ib_conn, log=log.setup(component="IB-price-data"))
            arctic_pricedata = arcticFuturesContractPriceData(mongo_db=mongo_db,
                                                      log=log.setup(component="arcticFuturesContractPriceData"))
            mongo_contractsdata = mongoFuturesContractData(mongo_db=mongo_db,
                                                   log = log.setup(component="mongoFuturesContractData"))


        :param arg_string: str like a named tuple in the form 'classNameOfData1 classNameOfData2' and so on
        :param mongo_db: mongo DB object
        :param ib_conn: ib connection
        :param csv_data_paths: dict, keynames are function names eg csvFuturesContractPriceData, values are paths
        :param log: logger

        """
        if mongo_db is arg_not_supplied:
            mongo_db = mongoDb()

        self.mongo_db = mongo_db
        self.ib_conn = ib_conn
        self.log = log
        self.csv_data_paths = csv_data_paths
        self.attr_list = []
        self.class_list = []

        if arg_string is arg_not_supplied:
            # can set up dynamically later
            return None

        self.add_class_list(arg_string)

    def __repr__(self):
        return "dataBlob with elements: %s" % ",".join(self.attr_list)

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
        attr_name, resolved_instance = process_class_id(class_name, mongo_db=self.mongo_db, \
                                                        ib_conn=self.ib_conn, log=self.log,
                                                        csv_data_paths = self.csv_data_paths)
        setattr(self, attr_name, resolved_instance)

        self.attr_list.append(attr_name)
        self.class_list.append(class_name)

        return success

def process_class_id(class_name, mongo_db = arg_not_supplied, ib_conn = arg_not_supplied,
                     log = logtoscreen(""), csv_data_paths = arg_not_supplied):
    """

    :param class_name: name of class to add to data
    :param mongo_db: mongo DB object
    :param ib_conn: ib connection
    :param log: logger (is called in eval, don't remove)
    :param csv_data_paths: dict of data paths for csv

    :return: 2 tuple: identifying attribute name str, instance of class
    """

    split_up_name = camel_case_split(class_name)
    prefix = split_up_name[0]

    if prefix=='ib' and ib_conn is arg_not_supplied:
        raise Exception("Tried to set up %s without passing IB connection" % class_name)

    if (prefix=='mongo' or prefix is 'arctic') and mongo_db is arg_not_supplied:
        raise Exception("Tried to set up %s without passing mongo_db" % class_name)

    if prefix=='csv':
        if csv_data_paths is arg_not_supplied:
            raise Exception("Need csv_data_paths dict for class name %s" % class_name)
        datapath = csv_data_paths.get(class_name, "")
        if datapath is "":
            raise Exception("Need to have key %s in csv_data_paths" % class_name)

    eval_dict = dict(ib = "%s(ib_conn, log=log.setup(component='%s'))",
                     mongo = "%s(mongo_db=mongo_db, log=log.setup(component='%s'))",
                     arctic = "%s(mongo_db=mongo_db, log=log.setup(component='%s'))",
                     csv = "%s(datapath=datapath, log=log.setup(component='%s'))")

    to_eval = eval_dict[prefix] % (class_name, class_name) # class_name appears twice as always passed as a log
    ## The eval may use ib_conn, mongo_db, datapath and will always use log
    resolved_instance = eval(to_eval)

    attr_name = identifying_name(split_up_name)

    return attr_name, resolved_instance

def identifying_name(split_up_name):
    lower_split_up_name = [x.lower() for x in split_up_name]
    data_label = lower_split_up_name.pop(-1) # always 'data'
    try:
        assert data_label=="data"
    except:
        raise Exception("Get_data strings only work if class name ends in ...Data")

    return "_".join(lower_split_up_name)

def camel_case_split(str):
    words = [[str[0]]]

    for c in str[1:]:
        if words[-1][-1].islower() and c.isupper():
            words.append(list(c))
        else:
            words[-1].append(c)

    return [''.join(word) for word in words]

