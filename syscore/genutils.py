"""
Utilities I can't put anywhere else...
"""

from math import copysign, gcd
from copy import copy
import sys
import numpy as np
import datetime
import functools


class not_required_flag(object):
    def __repr__(self):
        return "Not required"


NOT_REQUIRED = not_required_flag()


def group_dict_from_natural(dict_group):
    """
    If we're passed a natural grouping dict (eg dict(bonds=["US10", "KR3", "DE10"], equity=["SP500"]))
    Returns the dict optimised for algo eg dict(US10=["KR3", "DE10"], SP500=[], ..)

    :param dict_group: dictionary of groupings
    :type dict_group: dict

    :returns: dict


    >>> a=dict(bonds=["US10", "KR3", "DE10"], equity=["SP500"])
    >>> group_dict_from_natural(a)['KR3']
    ['US10', 'DE10']
    """
    if len(dict_group) == 0:
        return dict()

    all_names = sorted(set(sum([dict_group[groupname]
                                for groupname in dict_group.keys()], [])))

    def _return_without(name, group):
        if name in group:
            g2 = copy(group)
            g2.remove(name)
            return g2
        else:
            return None

    def _return_group(name, dict_group):
        ans = [
            _return_without(name, dict_group[groupname])
            for groupname in dict_group.keys()
        ]
        ans = [x for x in ans if x is not None]
        if len(ans) == 0:
            return []

        ans = ans[0]
        return ans

    gdict = dict([(name, _return_group(name, dict_group))
                  for name in all_names])

    return gdict


def str2Bool(x):
    if isinstance(x, bool):
        return x
    return x.lower() in ("t", "true")


def TorF(x):
    if x:
        return "T"
    else:
        return "F"


def str_of_int(x):
    """
    Returns the string of int of x, handling nan's or whatever

    :param x: Name of python package
    :type x: int or float

    :returns: 1.0 or -1.0

    >>> str_of_int(34)
    '34'

    >>> str_of_int(34.0)
    '34'

    >>> import numpy as np
    >>> str_of_int(np.nan)
    ''

    """
    if isinstance(x, int):
        return str(x)
    try:
        return str(int(x))
    except BaseException:
        return ""


def sign(x):
    """
    Return the sign of x (float or int)
    :param x: Thing we want sign of
    :type x: int, float

    :returns: 1 or -1

    >>> sign(3)
    1.0

    >>> sign(3.0)
    1.0

    >>> sign(-3)
    -1.0

    >>> sign(0)
    1.0


    """
    return copysign(1, x)


def value_or_npnan(x, return_value=None):
    """
    If x is np.nan return return_value
    else return x

    :param x: np.nan or other
    :return: x or return_value

    >>> value_or_npnan(np.nan)

    >>> value_or_npnan(np.nan, -1)
    -1

    >>> value_or_npnan("thing")
    'thing'

    >>> value_or_npnan(42)
    42

    """

    try:
        if np.isnan(x):
            return return_value
        else:
            pass
            # Not a nan will return x
    except BaseException:
        # Not something that can be compared to a nan
        pass

    # Either wrong type, or not a nan
    return x


def get_safe_from_dict(some_dict, some_arg_name, some_default):
    arg_from_dict = some_dict.get(some_arg_name, None)
    if arg_from_dict is None:
        return some_default
    else:
        return arg_from_dict


def are_dicts_equal(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    if len(intersect_keys) != len(d1_keys):
        return False
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    if len(same) != len(d1_keys):
        return False
    return True


class progressBar(object):
    """
    Example (not docstring as won't work)

    import time
    thing=progressBar(10000)
    for i in range(10000):
         # do something
         time.sleep(0.001)
         thing.iterate()
    thing.finished()

    """

    def __init__(
            self,
            range_to_iter,
            suffix="Progress",
            toolbar_width=80,
            show_each_time=False):
        self.toolbar_width = toolbar_width
        self.current_iter = 0
        self.suffix = suffix
        self.range_to_iter = range_to_iter
        self.range_per_block = range_to_iter / np.float(toolbar_width)
        self.display_bar()
        self._how_many_blocks_displayed = -1  # will always display first time
        self._show_each_time = show_each_time

    def iterate(self):
        self.current_iter += 1
        if self.number_of_blocks_changed() or self._show_each_time:
            self.display_bar()

        if self.current_iter == self.range_to_iter:
            self.finished()

    def how_many_blocks_had(self):
        return int(self.current_iter / self.range_per_block)

    def how_many_blocks_left(self):
        return int(
            (self.range_to_iter -
             self.current_iter) /
            self.range_per_block)

    def number_of_blocks_changed(self):
        original_blocks = self._how_many_blocks_displayed
        new_blocks = self.how_many_blocks_had()

        if new_blocks > original_blocks:
            return True
        else:
            return False

    def display_bar(self):
        percents = round(
            100.0 *
            self.current_iter /
            float(
                self.range_to_iter),
            1)
        bar = "=" * self.how_many_blocks_had() + "-" * self.how_many_blocks_left()
        progress_string = "\0\r [%s] %s%s %s" % (
            bar, percents, "%", self.suffix)
        sys.stdout.write(progress_string)
        sys.stdout.flush()
        self._how_many_blocks_displayed = self.how_many_blocks_had()

    def finished(self):
        sys.stdout.write("\n")


class quickTimer(object):
    def __init__(self, seconds=60):
        self._started = datetime.datetime.now()
        self._time_limit = seconds

    @property
    def unfinished(self):
        return not self.finished

    @property
    def finished(self):
        time_now = datetime.datetime.now()
        elapsed = time_now - self._started
        if elapsed.seconds > self._time_limit:
            return True
        else:
            return False


# avoids encoding problems with mongo
_none = ""


def none_to_object(x, object):
    if x is _none:
        return object
    else:
        return x


def object_to_none(x, object, y=_none):
    if x is object:
        return y
    else:
        return x


def get_unique_list(somelist):
    uniquelist = []

    for letter in somelist:
        if letter not in uniquelist:
            uniquelist.append(letter)

    return uniquelist


MISSING_STR = -1

def list_of_items_seperated_by_underscores(this_str, result = ()):
    find_underscore = this_str.find("_")
    if find_underscore is MISSING_STR:
        result_as_list = list(result)
        result_as_list.append(this_str)
        return result_as_list

    partial_str = this_str[:find_underscore]
    result = result + tuple([partial_str])

    remaining_str = this_str[find_underscore+1:]

    return list_of_items_seperated_by_underscores(remaining_str, result=result)

def get_and_convert(
        prompt,
        type_expected=int,
        allow_default=True,
        default_value=0,
        default_str=None):
    invalid = True
    input_str = prompt + " "
    if allow_default:
        if default_str is None:
            input_str = input_str + \
                "<RETURN for default %s> " % str(default_value)
        else:
            input_str = input_str + "<RETURN for %s> " % default_str

    while invalid:
        ans = input(input_str)

        if ans == "" and allow_default:
            return default_value
        try:
            result = type_expected(ans)
            return result
        except BaseException:
            print(
                "%s is not of expected type %s" %
                (ans, type_expected.__name__))
            continue



TOP_LEVEL = -1


class run_interactive_menu(object):
    def __init__(
        self,
        top_level_menu_of_options,
        nested_menu_of_options,
        exit_option=-1,
        another_menu=-2,
    ):
        """

        :param top_level_menu_of_options: A dict of top level options
        :param nested_menu_of_options: A dict of nested dicts, top levels keys are keys in top_level
        :return: object
        """

        self._top_level = top_level_menu_of_options
        self._nested = nested_menu_of_options
        self._location = TOP_LEVEL
        self._exit_option = exit_option
        self._another_menu = another_menu

    def propose_options_and_get_input(self):
        is_top_level = self._location == TOP_LEVEL
        if is_top_level:
            top_level_menu = self._top_level
            result = print_menu_and_get_response(
                top_level_menu, default_option=-1, default_str="EXIT"
            )
            if result == -1:
                return self._exit_option
            else:
                self._location = result
                return self._another_menu
        else:
            sub_menu = self._nested[self._location]
            result = print_menu_and_get_response(
                sub_menu, default_option=-1, default_str="Back"
            )
            if result == -1:
                self._location = -1
                return self._another_menu
            else:
                return result


def print_menu_of_values_and_get_response(
        menu_of_options_as_list, default_str=""):
    if default_str != "":
        try:
            menu_of_options_as_list.index(default_str)
        except ValueError:
            menu_of_options_as_list.append(default_str)

        default_option = menu_of_options_as_list.index(default_str)
    else:
        default_option = None

    menu_of_options = dict(
        [
            (int_key, menu_value)
            for int_key, menu_value in enumerate(menu_of_options_as_list)
        ]
    )
    ans = print_menu_and_get_response(
        menu_of_options, default_option=default_option, default_str=default_str
    )
    option_chosen = menu_of_options_as_list[ans]

    return option_chosen


def print_menu_and_get_response(
        menu_of_options,
        default_option=None,
        default_str=""):
    """

    :param menu_of_options: A dict, keys are ints, values are str
    :param default_option: None, or one of the keys
    :return: int menu chosen
    """

    menu_options_list = sorted(menu_of_options.keys())
    for option in menu_options_list:
        print("%d: %s" % (option, menu_of_options[option]))
    print("\n")
    computer_says_no = True
    if default_option is None:
        allow_default = False
    else:
        allow_default = True
        menu_options_list = [default_option] + menu_options_list

    while computer_says_no:
        ans = get_and_convert(
            "Your choice?",
            default_value=default_option,
            type_expected=int,
            allow_default=allow_default,
            default_str=default_str,
        )
        if ans not in menu_options_list:
            print("Not a valid option")
            continue
        else:
            computer_says_no = False
            break

    return ans


def transfer_object_attributes(named_tuple_object, original_object):
    kwargs = dict(
        [
            (field_name, getattr(original_object, field_name))
            for field_name in named_tuple_object._fields
        ]
    )
    new_object = named_tuple_object(**kwargs)

    return new_object


def highest_common_factor_for_list(list_of_ints):
    return functools.reduce(gcd, list_of_ints)


def divide_list_of_ints_by_highest_common_factor(list_of_ints):
    gcd_value = highest_common_factor_for_list(list_of_ints)
    new_list = [int(float(x) / gcd_value) for x in list_of_ints]
    return new_list


def list_of_ints_with_highest_common_factor_positive_first(list_of_ints):
    new_list = divide_list_of_ints_by_highest_common_factor(list_of_ints)
    multiply_sign = sign(new_list[0])
    new_list = [x * multiply_sign for x in new_list]
    return new_list


if __name__ == "__main__":
    import doctest

    doctest.testmod()
