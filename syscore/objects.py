"""
Do fun things with objects and classes
"""
from collections import namedtuple
import importlib


class named_object:
    def __init__(self, name):
        self._name = str(name)

    def __repr__(self):
        return self._name


missing_contract = named_object("missing contract")
missing_instrument = named_object("missing instrument")

missing_order = named_object("missing order")
locked_order = named_object("locked order")
duplicate_order = named_object("duplicate order")
zero_order = named_object("zero order")

fill_exceeds_trade = named_object("fill too big for trade")

order_is_in_status_finished = named_object(
    "order status is modification finished")
order_is_in_status_modified = named_object("order status is being modified")
order_is_in_status_not_modified = named_object(
    "order status is not currently modified"
)
order_is_in_status_reject_modification = named_object(
    "order status is modification rejected"
)

no_order_id = named_object("no order ID")
no_children = named_object("no_children")
no_parent = named_object("no parent")

rolling_cant_trade = named_object("rolling can't trade")
ROLL_PSEUDO_STRATEGY = "_ROLL_PSEUDO_STRATEGY"

not_updated = named_object("not updated")

class status(named_object):
    pass
success = status("success")
failure = status("failure")

arg_not_supplied = named_object("arg not supplied")
user_exit = named_object("exit")

table = namedtuple("table", "Heading Body")
header = namedtuple("header", "Heading")
body_text = namedtuple("bodytext", "Text")


def get_methods(a_stage_object) -> list:
    dir_list = dir(a_stage_object)

    # remove "_"

    dir_list = [
        method_name for method_name in dir_list if method_name[0] != "_"]

    # remove special
    special_list = ["log", "name", "parent", "description"]
    dir_list = [
        method_name for method_name in dir_list if method_name not in special_list]

    return dir_list


def resolve_function(func_or_func_name):
    """
    if func_or_func_name is a callable function, then return the function

    If it is a string containing '.' then it is a function in a module, return the function

    :param func_or_func_name: Name of a function including package.module, or a callable function
    :type func_or_func_name: int, float, or something else eg np.nan

    :returns: function

    >>> resolve_function(str)
    <class 'str'>

    >>> resolve_function("syscore.algos.robust_vol_calc").__name__
    'robust_vol_calc'

    """

    if hasattr(func_or_func_name, "__call__"):
        # it's a function, just return it so can be used
        # doesn't work for all functions, but we only care about callable ones
        return func_or_func_name

    if not isinstance(func_or_func_name, str):
        raise Exception(
            "Called resolve_function with non string or callable object %s"
            % str(func_or_func_name)
        )

    if "." in func_or_func_name:
        # it's another module, have to get it
        mod_name, func_name = func_or_func_name.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name, None)

    else:
        raise Exception(
            "Need full module file name string: %s isn't good enough"
            % func_or_func_name
        )

    return func


def resolve_data_method(some_object,
                        data_string: str):
    """
    eg if data_string="data1.data2.method" then returns the method some_object.data1.data2.method

    :param some_object: The object with a method
    :type some_object: object

    :param data_string: method or attribute within object
    :type data_string: str

    :returns: method in some_object

    >>> from sysdata.data import simData
    >>>
    >>> data=simData()
    >>> resolve_data_method(data, "get_instrument_price")
    <bound method Data.get_instrument_price of Data object with 0 instruments>
    >>>
    >>> meta_data=simData()
    >>> setattr(meta_data, "meta", data)
    >>> resolve_data_method(meta_data, "meta.get_instrument_price")
    <bound method Data.get_instrument_price of Data object with 0 instruments>
    >>>
    >>> meta_meta_data=simData()
    >>> setattr(meta_meta_data, "moremeta", meta_data)
    >>> resolve_data_method(meta_meta_data, "moremeta.meta.get_instrument_price")
    <bound method Data.get_instrument_price of Data object with 0 instruments>

    """

    list_to_parse = data_string.rsplit(".")

    return _recursively_get_attr_within_list(some_object, list_to_parse)

def _recursively_get_attr_within_list(an_object,
                                      list_to_parse: list):
    if len(list_to_parse) == 0:
        return an_object

    next_attr = list_to_parse.pop(0)
    sub_object = getattr(an_object, next_attr)

    return _recursively_get_attr_within_list(sub_object, list_to_parse)


def update_recalc(stage_object, additional_protected=[]):
    """
    Update the recalculation dictionary

    Used when a stage inherits from another

    (see system.stage and systems.futures.rawdata for an example)

    :param stage_object: The stage object with attributes to test
    :type stage_object: object

    :param additional_protected: Things to add to this attribute
    :type additional_protected: list of str

    :returns: None (changes stage_object)

    """

    original_dont_delete = getattr(stage_object, "_protected", [])

    child_dont_delete = list(set(original_dont_delete + additional_protected))

    setattr(stage_object, "_protected", child_dont_delete)


def hasallattr(some_object, attrlist=[]):
    """
    Check something has all the attributes you need

    :param some_object: The object with attributes to test
    :type some_object: object

    :param attrlist: Attributes to check
    :type attrlist: list of str

    :returns: bool

    >>> from sysdata.data import simData
    >>> data=simData()
    >>> setattr(data, "one", 1)
    >>> setattr(data, "two", 2)
    >>> hasallattr(data, ["one", "two"])
    True

    >>> hasallattr(data, ["one", "two","three"])
    False


    """
    return all([hasattr(some_object, attrname) for attrname in attrlist])


def get_class_name(class_object):
    return class_object.__name__


class missingData(Exception):
    pass


class existingData(Exception):
    pass


missing_file = named_object("missing file")
missing_data = named_object("missing data")