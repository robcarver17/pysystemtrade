import inspect
from syscore.interactive.input import (
    get_input_from_user_and_convert_to_type,
)

NO_DEFAULT = object()
NO_TYPE_PROVIDED = object()
NO_VALID_ARGUMENT_PASSED = object()
EMPTY_VALUE = inspect._empty


def interactively_input_arguments_for_function(func, full_funcname):
    """
    Prints the docstring of func, then asks for all of its arguments with defaults

    Optionally casts to type, if any argument name is an entry in the dict type_casting
    """

    func_arguments = inspect.signature(func).parameters

    print(
        "\n %s:\n %s \n Arguments: %s"
        % (full_funcname, str(inspect.getdoc(func)), str(list(func_arguments.keys())))
    )

    args = []
    kwargs = dict()
    for (argname, parameter_signature) in func_arguments.items():
        arg_value = input_and_type_cast_argument(argname, parameter_signature)

        is_kwarg = has_default(parameter_signature)
        if is_kwarg:
            kwargs[argname] = arg_value
        else:
            args.append(arg_value)

    return args, kwargs


def input_and_type_cast_argument(argname: str, parameter_signature: inspect.Parameter):
    """
    Interactively get a value for a parameter, considering any type casting required or defaults

    :return: argument value
    """

    default_provided = has_default(parameter_signature)
    needs_casting = has_type(parameter_signature)

    if default_provided:
        argdefault = parameter_default(parameter_signature)
        default_str = " (default: '%s')" % str(argdefault)
    else:
        default_str = ""

    if needs_casting:
        type_to_cast_to = parameter_type(parameter_signature)
        type_string = " (type: %s)" % str(type_to_cast_to)
    else:
        type_to_cast_to = NO_TYPE_PROVIDED
        type_string = ""

    prompt = "Argument %s %s" % (argname, type_string)

    if needs_casting:
        check_type = True
    else:
        check_type = False

    arg_value = get_input_from_user_and_convert_to_type(
        prompt=prompt,
        type_expected=type_to_cast_to,
        allow_default=default_provided,
        default_str=default_str,
        check_type=check_type,
    )

    return arg_value


def has_type(parameter_signature) -> bool:
    return parameter_type(parameter_signature) is not NO_TYPE_PROVIDED


def parameter_type(
    parameter_signature: inspect.Parameter,
):

    ptype = parameter_signature.annotation
    if ptype is EMPTY_VALUE:
        # get from default
        if has_default(parameter_signature):
            return_type = get_default_type(parameter_signature)
        else:
            # give up
            return NO_TYPE_PROVIDED
    else:
        return_type = ptype

    return return_type


def get_default_type(parameter_signature: inspect.Parameter) -> str:
    default_value = parameter_default(parameter_signature)
    default_ptype = type(default_value)

    return default_ptype


def has_default(parameter_signature: inspect.Parameter) -> bool:
    return parameter_default(parameter_signature) is not NO_DEFAULT


def parameter_default(parameter_signature: inspect.Parameter):
    default = parameter_signature.default
    if default is EMPTY_VALUE:
        default = NO_DEFAULT
    return default
