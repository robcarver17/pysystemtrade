"""
Do fun things with objects and classes
"""

import importlib
from copy import deepcopy

def resolve_function(func_or_func_name):
    """
    if func_or_func_name is a callable function, then return the function
    
    If it is a string containing '.' then it is a function in a module, return the function
    
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
        func = getattr(mod, func_name)

    else:
        raise Exception("Need full module file name string: %s isn't good enough" % func_or_func_name)
        
    return func

def resolve_data_method(some_object, data_string, _resolved_object=None):
    """
    eg if data_string="data1.data2.method" then returns the method some_object.data1.data2.method
    
    """
    if _resolved_object is None:
        _resolved_object=deepcopy(some_object)
        
    if "." in data_string:
        mod_name, data_string = data_string.rsplit('.',1)
        _resolved_object=getattr(_resolved_object, mod_name)
        return resolve_data_method(some_object, data_string, _resolved_object)
    else:
        mod_name=data_string
        resolved_object=getattr(_resolved_object, mod_name)

    return resolved_object

def calc_or_cache(some_object, dictname, keyname, func, *args, **kwargs):
    """
    Assumes that some_object has an attribute dictname, and that is a dict
    
    If dictname[keyname] exists return it. Else call func with *args and **kwargs

    Used for cache within various kinds of objects like config, price, data, system...
    

    """
    somedict=getattr(some_object, dictname)
    
    if keyname not in somedict.keys():
        
        somedict[keyname]=func(some_object, keyname, *args, **kwargs)
        setattr(some_object, dictname, somedict)
    
    return somedict[keyname]


def update_recalc(subsystem_object, additional_delete_on_recalc=[], additional_dont_delete=[]):
    """
    Update the recalculation dictionaries when inheriting from a parent
    
    (see system.basesystem and subsystem)
    """
    
    parent_delete_on_recalc=subsystem_object._delete_on_recalc
    parent_dont_delete=subsystem_object._dont_recalc
    
    child_delete_on_recalc=list(set(parent_delete_on_recalc+additional_delete_on_recalc))
    child_dont_delete=list(set(parent_dont_delete+additional_dont_delete))
    
    setattr(subsystem_object, "_delete_on_recalc", child_delete_on_recalc)
    setattr(subsystem_object, "_dont_delete", child_dont_delete)


def hasallattr(some_object, attrlist=[]):
    """
    Check something has all the attributes you need
    """
    return all([hasattr(some_object, attrname) for attrname in attrlist])