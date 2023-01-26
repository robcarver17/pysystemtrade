from copy import copy
from typing import List, Tuple, Union

from syscore.interactive.input import (
    get_input_from_user_and_convert_to_type,
)

TOP_LEVEL = -1
EXIT_OPTION = -1
TRAVERSING_MENU = -2


class interactiveMenu(object):
    def __init__(
        self,
        top_level_menu_of_options: dict,
        nested_menu_of_options: dict,
        dict_of_functions: dict,
        *args,
        **kwargs,
    ):
        """

        Run an interactive menu with one sublevel

        Example:

        def print_add1(x):
            print(x+1)

        def print_add2(x):
            print(x+2)

        def print_add3(x):
            print(x+3)


        menu = interactiveMenu({1: 'first submenu', 2: 'second submenu'},
                        {1: {11: 'submenu1, option 1', 12: 'submenu2, option2'},
                        2: {21: 'submenu2, option1'}},
                        {11: print_add1, 12: print_add2, 21: print_add3},
                        10)

        """

        self._top_level = top_level_menu_of_options
        self._nested = nested_menu_of_options
        self._dict_of_functions = dict_of_functions
        self._args = args
        self._kwargs = kwargs
        self.location = TOP_LEVEL

    def run_menu(self):
        still_running = True
        while still_running:
            option_chosen = self.propose_options_and_get_input()
            if option_chosen == EXIT_OPTION:
                print("FINISHED")
                return None
            if option_chosen == TRAVERSING_MENU:
                continue

            method_chosen = self._dict_of_functions[option_chosen]
            method_chosen(*self._args, **self._kwargs)

    def propose_options_and_get_input(self):
        if self.at_top_level:
            option_chosen = self._propose_options_and_get_input_at_top_level()
        else:
            option_chosen = self._propose_options_and_get_input_at_sub_level()

        return option_chosen

    def _propose_options_and_get_input_at_top_level(self):
        option_chosen = print_menu_and_get_desired_option_index(
            self.top_level_menu, default_option_index=EXIT_OPTION, default_str="EXIT"
        )
        if option_chosen == EXIT_OPTION:
            return EXIT_OPTION
        else:
            self.location = option_chosen
            return TRAVERSING_MENU

    def _propose_options_and_get_input_at_sub_level(self) -> int:

        sub_menu = self.current_submenu
        option_chosen = print_menu_and_get_desired_option_index(
            sub_menu, default_option_index=EXIT_OPTION, default_str="Back"
        )
        if option_chosen == EXIT_OPTION:
            self.location = TOP_LEVEL
            return TRAVERSING_MENU
        else:
            return option_chosen

    @property
    def at_top_level(self) -> bool:
        return self.location == TOP_LEVEL

    @property
    def location(self) -> int:
        return self._location

    @location.setter
    def location(self, new_location: int):
        self._location = new_location

    @property
    def current_submenu(self) -> dict:
        if self.at_top_level:
            return self.top_level_menu

        return self.nested_menu[self.location]

    @property
    def top_level_menu(self) -> dict:
        return self._top_level

    @property
    def nested_menu(self) -> dict:
        return self._nested

    @property
    def dict_of_function(self) -> dict:
        return self._dict_of_functions

    @property
    def args(self) -> tuple:
        return self._args

    @property
    def kwargs(self) -> dict:
        return self._kwargs


def print_menu_of_values_and_get_response(
    menu_of_options_as_list: List[str], default_str=""
) -> str:

    default_option_index, copy_menu_of_options_as_list = _get_index_of_default_option(
        menu_of_options_as_list=menu_of_options_as_list, default_str=default_str
    )

    menu_of_options = _list_menu_to_dict_menu(copy_menu_of_options_as_list)

    ans = print_menu_and_get_desired_option_index(
        menu_of_options,
        default_option_index=default_option_index,
        default_str=default_str,
    )
    option_chosen = copy_menu_of_options_as_list[ans]

    return option_chosen


def _get_index_of_default_option(
    menu_of_options_as_list: List[str], default_str=""
) -> Tuple[Union[type(None), int], List[str]]:

    copy_menu_of_options_as_list = copy(menu_of_options_as_list)
    if default_str == "":
        return None, copy_menu_of_options_as_list
    try:
        default_option = copy_menu_of_options_as_list.index(default_str)
    except ValueError:
        ## not in list have to add it
        copy_menu_of_options_as_list.append(default_str)
        default_option = copy_menu_of_options_as_list.index(default_str)

    return default_option, copy_menu_of_options_as_list


def _list_menu_to_dict_menu(menu_of_options_as_list: List[str]) -> dict:
    menu_of_options = dict(
        [
            (int_key, menu_value)
            for int_key, menu_value in enumerate(menu_of_options_as_list)
        ]
    )
    return menu_of_options


def print_menu_and_get_desired_option_index(
    menu_of_options: dict, default_option_index=None, default_str: str = ""
) -> int:
    _print_options_menu(menu_of_options)

    (
        allow_default,
        copy_menu_of_options,
        default_option_index,
        default_str,
    ) = _resolve_default_for_dict_of_menu_options(
        menu_of_options=menu_of_options,
        default_option_index=default_option_index,
        default_str=default_str,
    )
    menu_options_list = sorted(copy_menu_of_options.keys())

    invalid_response = True
    while invalid_response:
        ans = get_input_from_user_and_convert_to_type(
            "Your choice?",
            type_expected=int,
            allow_default=allow_default,
            default_value=default_option_index,
            default_str=default_str,
        )
        if ans not in menu_options_list:
            print("Not a valid option")
            continue
        else:
            break

    return ans


def _resolve_default_for_dict_of_menu_options(
    menu_of_options: dict, default_option_index=None, default_str: str = ""
) -> Tuple[bool, dict, int, str]:

    """

    >>> _resolve_default_for_dict_of_menu_options({1: 'a', 2: 'b'}, 1)
    (True, {1: 'a', 2: 'b'}, 1, 'a')
    >>> _resolve_default_for_dict_of_menu_options({1: 'a', 2: 'b'})
    (False, {1: 'a', 2: 'b'}, None, '')
    >>> _resolve_default_for_dict_of_menu_options({1: 'a', 2: 'b'}, default_str="x")
    (False, {1: 'a', 2: 'b'}, None, 'x')
    >>> _resolve_default_for_dict_of_menu_options({1: 'a', 2: 'b'}, 0, default_str="c")
    (True, {1: 'a', 2: 'b', 0: 'c'}, 0, 'c')

    """

    copy_menu_of_options = copy(menu_of_options)
    menu_options_list = sorted(copy_menu_of_options.keys())

    if default_option_index is None:
        allow_default = False
        ## will ignore default_str without an index for it
    else:
        allow_default = True
        if not default_option_index in menu_options_list:
            copy_menu_of_options[default_option_index] = default_str
        else:
            default_str = copy_menu_of_options[default_option_index]

    return allow_default, copy_menu_of_options, default_option_index, default_str


def _print_options_menu(menu_of_options: dict):
    menu_options_list = sorted(menu_of_options.keys())
    try:
        for option in menu_options_list:
            print("%d: %s" % (option, str(menu_of_options[option])))
        print("\n")
    except TypeError:
        raise Exception("All keys passed to menu must be of type int")
