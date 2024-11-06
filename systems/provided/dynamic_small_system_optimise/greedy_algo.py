from copy import copy

import numpy as np


def greedy_algo_across_integer_values(
    obj_instance: "objectiveFunctionForGreedy",
) -> np.array:
    ## Starting weights
    ## These will either be all zero, or in the presence of constraints will include the minima
    weight_start = obj_instance.starting_weights_as_np
    best_value = obj_instance.evaluate(weight_start)
    best_solution = weight_start

    at_limit = [False] * len(weight_start)

    done = False

    while not done:
        new_best_value, new_solution, at_limit = _find_possible_new_best_live(
            best_solution=best_solution,
            best_value=best_value,
            obj_instance=obj_instance,
            at_limit=at_limit,
        )

        if new_best_value < best_value:
            # reached a new optimum
            best_value = new_best_value
            best_solution = new_solution
        else:
            # we can't do any better
            break

    return best_solution


def _find_possible_new_best_live(
    best_solution: np.array,
    best_value: float,
    obj_instance: "objectiveFunctionForGreedy",
    at_limit: list,
) -> tuple:
    new_best_value = best_value
    new_solution = best_solution

    per_contract_value = obj_instance.per_contract_value_as_np
    direction = obj_instance.direction_as_np

    count_assets = len(best_solution)
    for i in range(count_assets):
        if at_limit[i]:
            continue
        temp_step = copy(best_solution)
        temp_step[i] = temp_step[i] + per_contract_value[i] * direction[i]

        at_limit = _update_at_limit(
            i, at_limit=at_limit, temp_step=temp_step, obj_instance=obj_instance
        )
        if at_limit[i]:
            continue

        temp_objective_value = obj_instance.evaluate(temp_step)

        if temp_objective_value < new_best_value:
            new_best_value = temp_objective_value
            new_solution = temp_step

    return new_best_value, new_solution, at_limit


def _update_at_limit(
    i: int,
    at_limit: list,
    temp_step: np.array,
    obj_instance: "objectiveFunctionForGreedy",
) -> list:
    direction_this_item = obj_instance.direction_as_np[i]
    temp_weight_this_item = temp_step[i]
    if direction_this_item > 0:
        max_this_item = obj_instance.maxima_as_np[i]
        if temp_weight_this_item > max_this_item:
            at_limit[i] = True

    else:
        min_this_item = obj_instance.minima_as_np[i]
        if temp_weight_this_item < min_this_item:
            at_limit[i] = True

    return at_limit
