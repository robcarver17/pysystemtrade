"""
Do fun things with objects and classes
"""

import importlib
from copy import deepcopy

"""
This is used for items which affect an entire system, not just one instrument
"""
ALL_KEYNAME="all"

def resolve_function(func_or_func_name):
    """
    if func_or_func_name is a callable function, then return the function
    
    If it is a string containing '.' then it is a function in a module, return the function

    :param func_or_func_name: Name of a function including package.module, or a callable function
    :type func_or_func_name: int, float, or something else eg np.nan
    
    :returns: function
    
    >>> resolve_function(str)
    <class 'str'>
    
    >>> resolve_function("syscore.algos.robust_vol_calc")
    <function robust_vol_calc at 0xb70077c4>
    
    """

    if hasattr(func_or_func_name, "__call__"):
        ## it's a function, just return it so can be used
        ## doesn't work for all functions, but we only care about callable ones
        return func_or_func_name
    
    if not type(func_or_func_name)==str:
        raise Exception("Called resolve_function with non string or callable object %s" % str(func_or_func_name))

    if "." in func_or_func_name:
        ## it's another module, have to get it
        mod_name, func_name = func_or_func_name.rsplit('.',1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name, None)

    else:
        raise Exception("Need full module file name string: %s isn't good enough" % func_or_func_name)
        
    return func

def resolve_data_method(some_object, data_string):
    """
    eg if data_string="data1.data2.method" then returns the method some_object.data1.data2.method

    :param some_object: The object with a method
    :type some_object: object
    
    :param data_string: method or attribute within object
    :type data_string: str
    
    :returns: method in some_object
    
    >>> from sysdata.data import Data
    >>>
    >>> data=Data()
    >>> resolve_data_method(data, "get_instrument_price")
    <bound method Data.get_instrument_price of Data object with 0 instruments>
    >>>
    >>> meta_data=Data()
    >>> setattr(meta_data, "meta", data)
    >>> resolve_data_method(meta_data, "meta.get_instrument_price")
    <bound method Data.get_instrument_price of Data object with 0 instruments>
    >>> 
    >>> meta_meta_data=Data()
    >>> setattr(meta_meta_data, "moremeta", meta_data)
    >>> resolve_data_method(meta_meta_data, "moremeta.meta.get_instrument_price")
    <bound method Data.get_instrument_price of Data object with 0 instruments>
    
    """

    list_to_parse=data_string.rsplit(".")
    
    def _get_attr_within_list(an_object, list_to_parse):
        if len(list_to_parse)==0:
            return an_object
        next_attr=list_to_parse.pop(0)
        sub_object=getattr(an_object, next_attr)
        return _get_attr_within_list(sub_object, list_to_parse)

    return _get_attr_within_list(some_object, list_to_parse)





def calc_or_cache(some_object, dictname, keyname, func, *args, **kwargs):
    """
    Assumes that some_object has an attribute dictname, and that is a dict
    
    If dictname[keyname] exists return it. Else call func with *args and **kwargs
    if the latter updates the dictionary

    Used for cache within various kinds of objects like config, price, data, system...

    :param some_object: The object with object.dictname 
    :type some_object: object
    
    :param dictname: attribute of object containing a dict 
    :type dictname: str

    :param keyname: keyname to look for in dict 
    :type keyname: valid dict key
    
    :param func: function to call if keyname missing. will take some_object and keyname as first two args
    :type func: function

    :param args, kwargs: also passed to fun if called
    
    :returns: contents of dict or result of calling function
    
    
    """
    somedict=getattr(some_object, dictname, None)
    if somedict is None:
        setattr(some_object, dictname, dict())
        somedict=dict()
    
    if keyname not in somedict.keys():
        
        somedict[keyname]=func(some_object, keyname, *args, **kwargs)
        setattr(some_object, dictname, somedict)
    
    return somedict[keyname]




def calc_or_cache_nested(some_object, dictname, keyname1, keyname2, func, *args, **kwargs):
    """
    Assumes that some_object has an attribute dictname, and that is a nested dict
    
    If dictname[keyname1][keyname2] exists return it. 
    Else call func with arguments: some_object, keyname1, keyname2, *args and **kwargs
    if we have to call the func updates the dictionary with it's value

    Used for cache within various kinds of objects like config, price, data, system...

    :param some_object: The object with object.dictname 
    :type some_object: object
    
    :param dictname: attribute of object containing a dict 
    :type dictname: str

    :param keyname1: keyname to look for in dict 
    :type keyname1: valid dict key

    :param keyname2: keyname to look for in nested dict 
    :type keyname2: valid dict key

    :param func: function to call if keyname missing. will take some_object and keyname1, keyname2 as first three args
    :type func: function

    :param args, kwargs: also passed to fun if called
    
    :returns: contents of dict or result of calling function
    
    
    """

    somedict=getattr(some_object, dictname, None)
    if somedict is None:
        setattr(some_object, dictname, dict())
        somedict=dict()
    
    found=False
    if keyname1 in somedict.keys():
        ## okay check the nested dict
        if keyname2 in somedict[keyname1].keys():
            found=True
    else:
        ## Need to add the top level dict
        somedict[keyname1]=dict()
    
    if not found:        
        somedict[keyname1][keyname2]=func(some_object, keyname1, keyname2, *args, **kwargs)
        setattr(some_object, dictname, somedict)
    
    return somedict[keyname1][keyname2]


def update_recalc(subsystem_object, additional_delete_on_recalc=[], additional_dont_delete=[]):
    """
    Update the recalculation dictionaries 
    
    Used when a subsystem inherits from another
    
    (see system.subsystem and systems.futures.rawdata for an example)

    :param subsystem_object: The subsystem object with attributes to test
    :type subsystem_object: object

    :param additional_delete_on_recalc: Things to add to this attribute
    :type additional_delete_on_recalc: list of str
    
    :param additional_dont_delete: Things to add to this attribute
    :type additional_dont_delete: list of str
    
    :returns: None (changes subsystem_object)

    """
    
    original_delete_on_recalc=getattr(subsystem_object,"_delete_on_recalc", [])
    original_dont_delete=getattr(subsystem_object,"_dont_recalc", [])
    
    child_delete_on_recalc=list(set(original_delete_on_recalc+additional_delete_on_recalc))
    child_dont_delete=list(set(original_dont_delete+additional_dont_delete))
    
    setattr(subsystem_object, "_delete_on_recalc", child_delete_on_recalc)
    setattr(subsystem_object, "_dont_delete", child_dont_delete)


def hasallattr(some_object, attrlist=[]):
    """
    Check something has all the attributes you need

    :param some_object: The object with attributes to test
    :type some_object: object

    :param attrlist: Attributes to check
    :type attrlist: list of str
    
    :returns: bool

    >>> from sysdata.data import Data
    >>> data=Data()
    >>> setattr(data, "one", 1)
    >>> setattr(data, "two", 2)
    >>> hasallattr(data, ["one", "two"])
    True

    >>> hasallattr(data, ["one", "two","three"])
    False
    
    
    """
    return all([hasattr(some_object, attrname) for attrname in attrlist])

if __name__ == '__main__':
    import doctest
    doctest.testmod()