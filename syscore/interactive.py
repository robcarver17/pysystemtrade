import datetime
from copy import copy

from syscore.dateutils import (
    n_days_ago,
    calculate_start_and_end_dates,
    get_date_from_period_and_end_date,
)
from syscore.genutils import named_tuple_as_dict, override_tuple_fields, str2Bool
from syscore.objects import arg_not_supplied


def get_field_names_for_named_tuple(named_tuple_instance):
    original_tuple_as_dict = named_tuple_as_dict(named_tuple_instance)
    for key_name in original_tuple_as_dict.keys():
        original_tuple_entry = original_tuple_as_dict[key_name]
        original_tuple_entry_class = original_tuple_entry.__class__
        input_result = get_and_convert(
            key_name,
            default_value=original_tuple_entry,
            type_expected=original_tuple_entry_class,
        )

        original_tuple_as_dict[key_name] = input_result

    new_tuple = override_tuple_fields(named_tuple_instance, original_tuple_as_dict)

    return new_tuple


def get_and_convert(
    prompt, type_expected=int, allow_default=True, default_value=0, default_str=None
):
    invalid = True
    input_str = prompt + " "
    if allow_default:
        if default_str is None:
            input_str = input_str + "<RETURN for default %s> " % str(default_value)
        else:
            input_str = input_str + "<RETURN for %s> " % default_str

    while invalid:
        ans = input(input_str)

        if ans == "" and allow_default:
            return default_value
        try:
            if type_expected is bool:
                result = str2Bool(ans)
            else:
                result = type_expected(ans)
            return result
        except BaseException:
            print("%s is not of expected type %s" % (ans, type_expected.__name__))
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


def print_menu_of_values_and_get_response(menu_of_options_as_list, default_str=""):

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


def print_menu_and_get_response(menu_of_options, default_option=None, default_str=""):
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


def true_if_answer_is_yes(prompt="", allow_empty_to_return_none=False) -> bool:
    invalid = True
    while invalid:
        x = input(prompt)
        if allow_empty_to_return_none:
            if x == "":
                return None

        if x:
            x = x.lower()
            if x[0] == "y":
                return True
            elif x[0] == "n":
                return False
        print("Need one of yes/no, Yes/No, y/n, Y/N")


def get_report_dates():

    end_date = arg_not_supplied
    start_date = arg_not_supplied
    start_period = arg_not_supplied
    end_period = arg_not_supplied

    input_end_date = get_datetime_input(
        "End date for report?\n",
        allow_default=True,
        allow_period=True,
        allow_calendar_days=True,
    )

    if type(input_end_date) is int:
        ## calendar days
        end_date = n_days_ago(input_end_date, datetime.datetime.now())
    elif type(input_end_date) is str:
        ## period
        end_period = input_end_date
    elif type(input_end_date) is datetime.datetime:
        end_date = input_end_date
    else:
        raise Exception("Don't recognise %s" % str(input_end_date))

    input_start_date = get_datetime_input(
        "Start date for report? \n",
        allow_default=False,
        allow_period=True,
        allow_calendar_days=True,
    )

    if type(input_start_date) is int:
        ## calendar days
        start_date = n_days_ago(input_start_date, end_date)
    elif type(input_start_date) is str:
        ## period
        start_period = input_start_date
    elif type(input_start_date) is datetime.datetime:
        start_date = input_start_date
    else:
        raise Exception("Don't recognise %s" % str(input_start_date))

    start_date, end_date = calculate_start_and_end_dates(
        calendar_days_back=arg_not_supplied,
        end_date=end_date,
        start_date=start_date,
        start_period=start_period,
        end_period=end_period,
    )

    return start_date, end_date


def get_datetime_input(
    prompt: str,
    allow_default: bool = True,
    allow_calendar_days: bool = False,
    allow_period: bool = False,
):
    invalid_input = True
    input_str = (
        prompt
        + ": Enter date and time in format %Y-%m-%d eg '2020-05-30' OR '%Y-%m-%d %H:%M:%S' eg '2020-05-30 14:04:11'"
    )
    if allow_calendar_days:
        input_str = input_str + "\n OR [Enter a number to back N calendar days]"
    if allow_period:
        input_str = input_str + "OR [Enter a string for period, eg 'YTD', '3M', '2B']"
    if allow_default:
        input_str = input_str + "OR <RETURN for now>"

    while invalid_input:
        ans = input(input_str)
        if ans == "" and allow_default:
            return datetime.datetime.now()

        if allow_period:
            try:
                _NOT_USED = get_date_from_period_and_end_date(ans)
                ## all good, return as string
                return ans
            except:
                pass

        if allow_calendar_days:
            try:
                attempt_as_int = int(ans)
                return attempt_as_int
            except:
                pass

        try:
            ans = resolve_datetime_input_str(ans)
            return ans
        except:
            print("%s is not any valid input string" % ans)
            pass


def resolve_datetime_input_str(ans):
    if len(ans) == 10:
        return_datetime = datetime.datetime.strptime(ans, "%Y-%m-%d")
    elif len(ans) == 19:
        return_datetime = datetime.datetime.strptime(ans, "%Y-%m-%d %H:%M:%S")
    else:
        # problems formatting will also raise value error
        raise ValueError
    return return_datetime
