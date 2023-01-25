"""
Created on 16 Nov 2016
@author: rob
v2.0 12th Feb 2019, fills types from annotations
"""

import importlib
import sys

# import of system libraries required to make this work

from syscore.interactive.run_functions import (
    interactively_input_arguments_for_function,
)


def resolve_func(func_reference_name):
    split_func = func_reference_name.rsplit(".", 1)
    if len(split_func) == 1:
        raise Exception(
            "%s should include filename as well as function e.g. filename.funcname or module.filename.funcname"
            % func_reference_name
        )
    funcname = split_func.pop()
    funcsource = split_func.pop()

    # stop overzealous interpreter tripping up
    func = None

    # imports have to be done in main
    try:
        mod = importlib.import_module(funcsource)
    except ImportError:
        raise Exception(
            "NOT FOUND: Module %s specified for function reference %s\n"
            % (funcsource, func_reference_name)
        )

    func = getattr(mod, funcname, None)

    if func is None:
        raise Exception(
            "NOT FOUND: function %s in module %s  specified for function reference %s"
            % (funcname, mod, func_reference_name)
        )

    return func


if __name__ == "__main__":

    if len(sys.argv) == 1:
        print(
            "Enter the name of a function with full pathname eg systems.basesystem.System"
        )
        exit()

    func_reference_name = sys.argv[1]

    # find the function
    func = resolve_func(func_reference_name)

    # get arguments
    args, kwargs = interactively_input_arguments_for_function(func, func_reference_name)

    # call the function
    func(*args, **kwargs)
