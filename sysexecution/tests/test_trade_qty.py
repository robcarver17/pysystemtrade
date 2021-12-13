from sysexecution.trade_qty import (
    tradeQuantity,
    change_trade_size_proportionally_to_meet_abs_qty_limit,
    reduce_trade_size_proportionally_so_smallest_leg_is_max_size,
    reduce_trade_size_proportionally_to_abs_limit_per_leg,
)


def _doc_tests1():
    """

    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([0], 0)
    [0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([0], 1)
    [0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1], 0)
    [0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1], 1)
    [1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1], 2)
    [1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([2], 0)
    [0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([2], 1)
    [1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([2], 2)
    [2]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([2], 3)
    [2]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1], 0)
    [0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1], 1)
    [-1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1], 2)
    [-1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2], 0)
    [0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2], 1)
    [-1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2], 2)
    [-2]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2], 3)
    [-2]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([0,0], 0)
    [0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([0,0], 1)
    [0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1,-1], 0)
    [0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1,-1], 1)
    [1, -1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1,-1], 2)
    [1, -1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1,1], 0)
    [0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1,1], 1)
    [-1, 1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1,1], 2)
    [-1, 1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([2,-2], 0)
    [0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([2,-2], 1)
    [1, -1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([2,-2], 2)
    [2, -2]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([2,-2], 3)
    [2, -2]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2,2], 0)
    [0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2,2], 1)
    [-1, 1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2,2], 2)
    [-2, 2]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2,2], 3)
    [-2, 2]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1,2,-1], 0)
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1,2,-1], 1)
    [-1, 2, -1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-1,2,-1], 2)
    [-1, 2, -1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1,-2,1], 0)
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1,-2,1], 1)
    [1, -2, 1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([1,-2,1], 2)
    [1, -2, 1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2,4,-2], 0)
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2,4,-2], 1)
    [-1, 2, -1]
    >>> reduce_trade_size_proportionally_so_smallest_leg_is_max_size([-2,4,-2], 2)
    [-2, 4, -2]
    """


def _doc_tests2():
    """

    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([0], [0])
    [0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([0], [1])
    [0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1], [0])
    [0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1], [1])
    [1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1], [2])
    [1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2], [0])
    [0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2], [1])
    [1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2], [2])
    [2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2], [3])
    [2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1], [0])
    [0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1], [1])
    [-1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1], [2])
    [-1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2], [0])
    [0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2], [1])
    [-1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2], [2])
    [-2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2], [3])
    [-2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-1], [0, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-1], [1, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-1], [0, 1])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-1], [1, 1])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,1], [0, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,1], [1, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,1], [0, 1])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,1], [0, 2])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,1], [1, 1])
    [-1, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,1], [2, 1])
    [-1, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,1], [1, 2])
    [-1, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,1], [2, 2])
    [-1, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [0, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [1, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [0, 1])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [1, 1])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [1, 2])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [2, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [0, 2])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [2, 1])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [2, 2])
    [2, -2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [3, 2])
    [2, -2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [2, 3])
    [2, -2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([2,-2], [3, 3])
    [2, -2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [0, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [1, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [0, 1])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [1, 1])
    [-1, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [1, 2])
    [-1, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [2, 1])
    [-1, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [2, 2])
    [-2, 2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [3, 2])
    [-2, 2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [2, 3])
    [-2, 2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,2], [3, 3])
    [-2, 2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [0, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [1, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [0, 1])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [1, 1])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [1, 2])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [0, 2])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [2, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [2, 1])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [2, 2])
    [2, -2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [1, 3])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [3, 0])
    [0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [3, 1])
    [1, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [3, 2])
    [2, -2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [2, 3])
    [2, -2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [3, 3])
    [3, -3]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([3,-3], [4, 3])
    [3, -3]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-2,1], [0, 0,0])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-2,1], [0, 0,1])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-2,1], [0, 1,0])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-2,1], [0, 1,1])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-2,1], [1, 1,1])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-2,1], [1, 2,1])
    [1, -2, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([1,-2,1], [2, 2,1])
    [1, -2, 1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,2,-1], [0, 0,0])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,2,-1], [0, 0,1])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,2,-1], [1, 1,1])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,2,-1], [2, 1,1])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,2,-1], [2, 2,1])
    [-1, 2, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,2,-1], [1, 2,1])
    [-1, 2, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,2,-1], [3, 2,1])
    [-1, 2, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-1,2,-1], [3, 2,0])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,4,-2], [1, 2,0])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,4,-2], [1, 1,1])
    [0, 0, 0]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,4,-2], [2, 2,1])
    [-1, 2, -1]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,4,-2], [2, 4,6])
    [-2, 4, -2]
    >>> reduce_trade_size_proportionally_to_abs_limit_per_leg([-2,4,-2], [2000, 4,6])
    [-2, 4, -2]

    """


def _doctests3():
    """
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([0]), 0)
    [0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1]), 0)
    [0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1]), 1)
    [1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1]), 2)
    [1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2]), 0)
    [0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2]), 0)
    [0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2]), 1)
    [1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2]), 2)
    [2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2]), 3)
    [2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([0,0]), 0)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([0,0]), 1)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-1]), 0)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-1]), 1)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-1]), 2)
    [1, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-1]), 3)
    [1, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,1]), 1)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,1]), 2)
    [-1, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,1]), 3)
    [-1, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,1]), 4)
    [-1, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-1]), 0)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-1]), 1)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-1]), 2)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-1]), 3)
    [2, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-1]), 4)
    [2, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,1]), 1)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,1]), 2)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,1]), 3)
    [-2, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,1]), 4)
    [-2, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-2]), 0)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-2]), 1)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-2]), 2)
    [1, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-2]), 3)
    [1, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-2]), 4)
    [2, -2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-2]), 5)
    [2, -2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-2]), 6)
    [2, -2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,2]), 0)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,2]), 1)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,2]), 2)
    [-1, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,2]), 3)
    [-1, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,2]), 4)
    [-2, 2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,2]), 5)
    [-2, 2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-2,2]), 6)
    [-2, 2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 0)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 1)
    [0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 2)
    [1, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 3)
    [1, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 4)
    [2, -2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 5)
    [2, -2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 6)
    [3, -3]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 7)
    [3, -3]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([3,-3]), 9)
    [3, -3]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-2,1]), 0)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-2,1]), 1)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-2,1]), 2)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-2,1]), 3)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-2,1]), 4)
    [1, -2, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-2,1]), 5)
    [1, -2, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([1,-2,1]), 8)
    [1, -2, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,2,-1]), 0)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,2,-1]), 1)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,2,-1]), 2)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,2,-1]), 3)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,2,-1]), 4)
    [-1, 2, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([-1,2,-1]), 8)
    [-1, 2, -1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 0)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 0)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 1)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 2)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 3)
    [0, 0, 0]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 4)
    [1, -2, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 5)
    [1, -2, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 7)
    [1, -2, 1]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 8)
    [2, -4, 2]
    >>> change_trade_size_proportionally_to_meet_abs_qty_limit(tradeQuantity([2,-4,2]), 9)
    [2, -4, 2]
    """

    pass
