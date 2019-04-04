'''
Created on 16 Nov 2016
@author: rob
v2.0 12th Feb 2019, fills types from annotations
'''

import inspect
import importlib
import sys

# import of system libraries required to make this work
import sysproduction

def resolve_func(func_reference_name):
    split_func = func_reference_name.rsplit('.', 1)
    if len(split_func) == 1:
        raise Exception(
            "%s should include filename as well as function e.g. filename.funcname or module.filename.funcname" % func_reference_name)
    funcname = split_func.pop()
    funcsource = split_func.pop()

    ## stop overzealous interpreter tripping up
    func = None

    ## imports have to be done in main
    try:
        mod = importlib.import_module(funcsource)
    except ImportError:
        raise Exception(
            "NOT FOUND: Module %s specified for function reference %s\n" % (funcsource, func_reference_name))

    func = getattr(mod, funcname, None)

    if func is None:
        raise Exception("NOT FOUND: function %s in module %s  specified for function reference %s" % (
            funcname, mod, func_reference_name))

    return func


NO_DEFAULT = object()
NO_TYPE_PROVIDED = object()
NO_VALID_ARGUMENT_PASSED = object()


def parameter_default(parameter_signature):
    default = parameter_signature.default
    if default is inspect._empty:
        default = NO_DEFAULT
    return default


def has_default(parameter_signature):
    return parameter_default(parameter_signature) is not NO_DEFAULT


def parameter_type(parameter_signature):
    ptype = parameter_signature.annotation
    if ptype is inspect._empty:
        # get from default
        if has_default(parameter_signature):
            default_value = parameter_default(parameter_signature)
            ptype = type(default_value)
        else:
            # give up
            return NO_TYPE_PROVIDED

    return ptype.__name__


def has_type(parameter_signature):
    return parameter_type(parameter_signature) is not NO_TYPE_PROVIDED


def input_and_type_cast_argument(argname, parameter_signature):
    """
    Interactively get a value for a parameter, considering any type casting required or defaults
    :param argname: str
    :param parameter_signature: results of doing inspect.signature(func)['parameter name']
    :return: argument value
    """

    default_provided = has_default(parameter_signature)
    needs_casting = has_type(parameter_signature)

    if default_provided:
        argdefault = parameter_default(parameter_signature)

    if needs_casting:
        type_to_cast_to = parameter_type(parameter_signature)

    # Should never return this unless something gone horribly wrong
    arg_value = NO_VALID_ARGUMENT_PASSED

    while arg_value is NO_VALID_ARGUMENT_PASSED:
        if default_provided:
            default_string = " (default: '%s')" % str(argdefault)
        else:
            default_string = ""

        if needs_casting:
            type_string = " (type: %s)" % str(type_to_cast_to)
        else:
            type_string = ""

        arg_value = input("Argument %s %s %s?" % (argname, default_string, type_string))

        if arg_value == "":  # just pressed carriage return...
            if default_provided:
                arg_value = argdefault
                break
            else:
                print("No default provided for %s - need a value. Please type something!" % argname)
                arg_value = NO_VALID_ARGUMENT_PASSED
        else:
            ## A value has been typed - check if needs type casting

            if needs_casting:
                try:
                    ## Cast the type
                    ## this might not work
                    type_func = eval("%s" % type_to_cast_to)
                    arg_value = type_func(arg_value)
                    break
                except:
                    print("\nCouldn't cast value %s to type %s\n" %
                          (arg_value, type_to_cast_to))
                    arg_value = NO_VALID_ARGUMENT_PASSED
            else:
                ## no type casting required
                pass

    return arg_value


def fill_args_and_run_func(func, full_funcname):
    """
    Prints the docstring of func, then asks for all of its arguments with defaults

    Optionally casts to type, if any argument name is an entry in the dict type_casting
    """
    ##print doc string

    print("\n")
    print(full_funcname + ":")
    print(inspect.getdoc(func))
    print("\n")
    func_arguments = inspect.signature(func).parameters

    print("\nArguments:")
    print(list(func_arguments.keys()))
    print("\n")

    args = []
    kwargs = dict()
    for (argname, parameter_signature) in func_arguments.items():
        arg_value = input_and_type_cast_argument(argname, parameter_signature)
        if arg_value is NO_VALID_ARGUMENT_PASSED:
            raise Exception(
                "Invalid argument passed - should not happen - check function 'input_and_type_cast_argument' logic")

        is_kwarg = has_default(parameter_signature)
        if is_kwarg:
            kwargs[argname] = arg_value
        else:
            args.append(arg_value)

    return args, kwargs


if __name__ == '__main__':

    if len(sys.argv) == 1:
        print("Enter the name of a function with full pathname eg systems.basesystem.System")
        exit()

    func_reference_name = sys.argv[1]

    # find the function
    func = resolve_func(func_reference_name)

    # get arguments
    args, kwargs = fill_args_and_run_func(func, func_reference_name)

    # call the function
    func(*args, **kwargs)