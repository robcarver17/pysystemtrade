# A kind of scratchpad for ideas

from concurrent.futures import ProcessPoolExecutor
from functools import partial


def function_call_with_args(args_as_list, function=None, specific_kwargs={}):
    return function(*args_as_list, **specific_kwargs)


pfunc = partial(function_call_with_args, function = func, specific_kwargs = some_kwargs)

if __name__ == "__main__":
    def func(a, b, c=3):
        return a * b * c


    some_args = [1, 2]
    some_kwargs = dict(c=1)
    print(func(*some_args, **some_kwargs))

    args_list = [[1, 2], [3, 4]]
    pfunc = partial(func, **some_kwargs)
    result = [pfunc(*specific_arg_list) for specific_arg_list in args_list]



    with ProcessPoolExecutor() as executor:
        results = executor.map(pfunc, args_list)
        #results = executor.map(pfunc, args_list)

    for y in results:
        print(y)
