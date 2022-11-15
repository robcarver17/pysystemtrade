import yaml
from sysobjects.production.trading_hours import dictOfDictOfWeekdayOpeningTimes

def read_trading_hours(filename: str):
    try:
        with open(filename, "r") as file_to_parse:
            simple_dict = yaml.load(
                file_to_parse,
                Loader=yaml.Loader
            )
    except:
        print("File %s not found, no saved trading hours" % filename)
        simple_dict = {}

    return dictOfDictOfWeekdayOpeningTimes.from_simple_dict(simple_dict)

def write_trading_hours(dict_of_dict_of_trading_hours: dictOfDictOfWeekdayOpeningTimes,
                        filename: str):
    simple_dict = dict_of_dict_of_trading_hours.to_simple_dict()
    with open(filename, "w") as file_to_parse:
        yaml.dump(simple_dict,
                  file_to_parse,
                  sort_keys = False)

