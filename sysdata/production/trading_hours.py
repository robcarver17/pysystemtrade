import yaml
from sysobjects.production.trading_hours.dict_of_weekly_trading_hours_any_day import (
    dictOfDictOfWeekdayTradingHours,
)
from syscore.fileutils import resolve_path_and_filename_for_package


def read_trading_hours(filename: str):
    resolved_filename = resolve_path_and_filename_for_package(filename)
    try:
        with open(resolved_filename, "r") as file_to_parse:
            simple_dict = yaml.load(file_to_parse, Loader=yaml.Loader)
    except:
        print("File %s not found, no saved trading hours" % filename)
        simple_dict = {}

    return dictOfDictOfWeekdayTradingHours.from_simple_dict(simple_dict)


def write_trading_hours(
    dict_of_dict_of_trading_hours: dictOfDictOfWeekdayTradingHours, filename: str
):
    simple_dict = dict_of_dict_of_trading_hours.to_simple_dict()
    resolved_filename = resolve_path_and_filename_for_package(filename)
    with open(resolved_filename, "w") as file_to_write_to:
        yaml.dump(simple_dict, file_to_write_to, sort_keys=False)
