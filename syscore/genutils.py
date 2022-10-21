"""
Utilities I can't put anywhere else...
"""

import time

from math import copysign, gcd
from copy import copy
import sys
import numpy as np
import datetime
import functools
import math
from collections import namedtuple

Changes = namedtuple('Changes', ['new', 'existing', 'removing'])

def round_significant_figures(x, figures=3):
    return round(x, figures - int(math.floor(math.log10(abs(x)))) - 1)

def new_removing_existing(original_list: list, new_list: list):
    existing = list(set(original_list).intersection(set(new_list)))
    new = list(set(new_list).difference(set(original_list)))
    removing = list(set(original_list).difference(set(new_list)))

    return Changes(new=new, existing=existing, removing=removing)


def flatten_list(some_list):
    flattened = [item for sublist in some_list for item in sublist]

    return flattened


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

    all_names = sorted(
        set(sum([dict_group[groupname] for groupname in dict_group.keys()], []))
    )

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

    gdict = dict([(name, _return_group(name, dict_group)) for name in all_names])

    return gdict


def str2Bool(x):
    if isinstance(x, bool):
        return x
    return x.lower() in ("t", "true")


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


PROGRESS_EXP_FACTOR = 0.9


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
        show_each_time=False,
        show_timings=True,
    ):

        self._start_time = time.time()
        self.toolbar_width = toolbar_width
        self.current_iter = 0
        self.suffix = suffix
        self.range_to_iter = range_to_iter
        self.range_per_block = range_to_iter / float(toolbar_width)
        self._how_many_blocks_displayed = -1  # will always display first time
        self._show_each_time = show_each_time
        self._show_timings = show_timings

        self.display_bar()

    def estimated_time_remaining(self):
        total_iter = self.range_to_iter
        iter_left = total_iter - self.current_iter
        time_per_iter = self.current_estimate_of_times
        if time_per_iter is None:
            return 0

        return iter_left * time_per_iter

    def update_time_estimate(self):
        ## don't maintain a list per se, instead exponential
        time_since_last_call = self.time_since_last_called()
        current_estimate = self.current_estimate_of_times
        if current_estimate is None:
            ## seed
            current_estimate = time_since_last_call
        else:
            current_estimate = ((1 - PROGRESS_EXP_FACTOR) * time_since_last_call) + (
                PROGRESS_EXP_FACTOR * current_estimate
            )

        self.current_estimate_of_times = current_estimate

    @property
    def current_estimate_of_times(self) -> float:
        current_estimate = getattr(self, "_current_estimate_of_times", None)
        return current_estimate

    @current_estimate_of_times.setter
    def current_estimate_of_times(self, current_estimate: float):
        self._current_estimate_of_times = current_estimate

    def time_since_last_called(self) -> float:
        time_of_last_call = self.get_and_set_time_of_last_call()
        current_time = self.current_time

        return current_time - time_of_last_call

    def get_and_set_time_of_last_call(self):
        time_of_last_iter = copy(getattr(self, "_time_of_last_call", self.start_time))
        self._time_of_last_call = self.current_time

        return time_of_last_iter

    def elapsed_time(self):
        return self.current_time - self.start_time

    @property
    def start_time(self):
        return self._start_time

    @property
    def current_time(self):
        return time.time()

    def iterate(self):
        self.current_iter += 1
        self.update_time_estimate()
        if self.number_of_blocks_changed() or self._show_each_time:
            self.display_bar()

        if self.current_iter == self.range_to_iter:
            self.finished()

    def how_many_blocks_had(self):
        return int(self.current_iter / self.range_per_block)

    def how_many_blocks_left(self):
        return int((self.range_to_iter - self.current_iter) / self.range_per_block)

    def number_of_blocks_changed(self):
        original_blocks = self._how_many_blocks_displayed
        new_blocks = self.how_many_blocks_had()

        if new_blocks > original_blocks:
            return True
        else:
            return False

    def display_bar(self):
        percents = round(100.0 * self.current_iter / float(self.range_to_iter), 1)
        if self._show_timings:
            time_remaining = self.estimated_time_remaining()
            time_elapsed = self.elapsed_time()
            total_est_time = time_elapsed + time_remaining
            time_str = "(%.1f/%.1f/%.1f secs left/elapsed/total)" % (
                time_remaining,
                time_elapsed,
                total_est_time,
            )
        else:
            time_str = ""

        bar = "=" * self.how_many_blocks_had() + "-" * self.how_many_blocks_left()
        progress_string = "\0\r [%s] %s%s %s %s" % (
            bar,
            percents,
            "%",
            self.suffix,
            time_str,
        )
        sys.stdout.write(progress_string)
        sys.stdout.flush()
        self._how_many_blocks_displayed = self.how_many_blocks_had()

    def finished(self):
        self.display_bar()
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

def override_tuple_fields(original_tuple_instance, dict_of_new_fields:dict):
    original_tuple_instance_as_dict = named_tuple_as_dict(original_tuple_instance)
    combined_dict = dict(original_tuple_instance_as_dict, **dict_of_new_fields)
    original_tuple_class = original_tuple_instance.__class__
    try:
        new_named_tuple = original_tuple_class(**combined_dict)
    except:
        raise Exception("One or more of new fields %s don't belong in named tuple %s"
                        % (str(dict_of_new_fields), str(original_tuple_instance)))
    return new_named_tuple

def named_tuple_as_dict(original_tuple_instance) -> dict:
    return dict([
        (field_name, getattr(original_tuple_instance, field_name))
                for field_name in original_tuple_instance._fields])

def transfer_object_attributes(named_tuple_object, original_object):
    kwargs = dict(
        [
            (field_name, getattr(original_object, field_name))
            for field_name in named_tuple_object._fields
        ]
    )
    new_object = named_tuple_object(**kwargs)

    return new_object


def highest_common_factor_for_list(list_of_ints: list) -> int:
    """

    :param list_of_ints:
    :return: int

    >>> highest_common_factor_for_list([2,3,4])
    1
    >>> highest_common_factor_for_list([2,6,4])
    2
    """
    return functools.reduce(gcd, list_of_ints)


def divide_list_of_ints_by_highest_common_factor(list_of_ints: list) -> list:
    """

    :param list_of_ints:
    :return: list

    >>> divide_list_of_ints_by_highest_common_factor([1,2])
    [1, 2]
    >>> divide_list_of_ints_by_highest_common_factor([2,4])
    [1, 2]
    >>> divide_list_of_ints_by_highest_common_factor([1,2,3])
    [1, 2, 3]
    >>> divide_list_of_ints_by_highest_common_factor([1])
    [1]
    """

    gcd_value = highest_common_factor_for_list(list_of_ints)
    new_list = [int(float(x) / gcd_value) for x in list_of_ints]
    return new_list


def list_of_ints_with_highest_common_factor_positive_first(list_of_ints: list) -> list:
    """
    Used to identify the unique version of a spread or fly contract

    :param list_of_ints:
    :return: list

    >>> list_of_ints_with_highest_common_factor_positive_first([1])
    [1]
    >>> list_of_ints_with_highest_common_factor_positive_first([-1])
    [1]
    >>> list_of_ints_with_highest_common_factor_positive_first([1,-1])
    [1, -1]
    >>> list_of_ints_with_highest_common_factor_positive_first([-1,1])
    [1, -1]
    >>> list_of_ints_with_highest_common_factor_positive_first([-1,2])
    [1, -2]
    >>> list_of_ints_with_highest_common_factor_positive_first([-2,2])
    [1, -1]
    >>> list_of_ints_with_highest_common_factor_positive_first([2,-2])
    [1, -1]
    >>> list_of_ints_with_highest_common_factor_positive_first([2,-4,2])
    [1, -2, 1]
    >>> list_of_ints_with_highest_common_factor_positive_first([-2,4,-2])
    [1, -2, 1]

    """
    new_list = divide_list_of_ints_by_highest_common_factor(list_of_ints)
    multiply_sign = sign(new_list[0])
    new_list = [int(x * multiply_sign) for x in new_list]
    return new_list


def np_convert(val):
    """
    Converts the passed numpy value to a native python type

    >>> val = np.int64(1)
    >>> type(val)
    <class 'numpy.int64'>
    >>> type(np_convert(val))
    <class 'int'>

    :param val:
    :return: val as native type
    """
    return val.item() if isinstance(val, np.generic) else val


if __name__ == "__main__":
    import doctest

    doctest.testmod()
