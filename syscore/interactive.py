from copy import copy


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

    copy_menu_of_options_as_list = copy(menu_of_options_as_list)
    if default_str != "":
        try:
            copy_menu_of_options_as_list.index(default_str)
        except ValueError:
            copy_menu_of_options_as_list.append(default_str)

        default_option = copy_menu_of_options_as_list.index(default_str)
    else:
        default_option = None

    menu_of_options = dict(
        [
            (int_key, menu_value)
            for int_key, menu_value in enumerate(copy_menu_of_options_as_list)
        ]
    )
    ans = print_menu_and_get_response(
        menu_of_options, default_option=default_option, default_str=default_str
    )
    option_chosen = copy_menu_of_options_as_list[ans]

    return option_chosen


def print_menu_and_get_response(
        menu_of_options,
        default_option=None,
        default_str=""):
    """

    :param copy_menu_of_options: A dict, keys are ints, values are str
    :param default_option: None, or one of the keys
    :return: int menu chosen
    """
    copy_menu_of_options = copy(menu_of_options)
    menu_options_list = sorted(copy_menu_of_options.keys())
    for option in menu_options_list:
        print("%d: %s" % (option, copy_menu_of_options[option]))
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