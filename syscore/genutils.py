"""
Utilities I can't put anywhere else...
"""

from math import copysign
from copy import copy
import sys
import numpy as np


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
        set(
            sum([dict_group[groupname]
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
    except:
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

    def __init__(self, range_to_iter, suffix="Progress", toolbar_width=80):
        self.toolbar_width = toolbar_width
        self.current_iter = 0
        self.suffix = suffix
        self.range_to_iter = range_to_iter
        self.range_per_block = range_to_iter / np.float(toolbar_width)
        self.display_bar()


    def iterate(self):
        self.current_iter += 1
        self.display_bar()

        if self.current_iter == self.range_to_iter:
            self.finished()

    def how_many_blocks_had(self):
        return int(self.current_iter / self.range_per_block)

    def how_many_blocks_left(self):
        return int((self.range_to_iter - self.current_iter) / self.range_per_block)

    def display_bar(self):
        percents = round(100.0 * self.current_iter / float(self.range_to_iter),
                         1)
        bar = '=' * self.how_many_blocks_had() + '-' * self.how_many_blocks_left()
        progress_string = '\0\r [%s] %s%s %s' % (bar, percents, '%',
                                                 self.suffix)
        sys.stdout.write(progress_string)
        sys.stdout.flush()

    def finished(self):
        sys.stdout.write("\n")


if __name__ == '__main__':
    import doctest
    doctest.testmod()
