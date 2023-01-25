from copy import copy
import os
from shutil import copyfile

from syscore.dateutils import create_datetime_marker_string
from syscore.fileutils import files_with_extension_in_pathname, get_resolved_pathname
from syscore.objects import (
    resolve_function,
)
from syscore.constants import missing_data, arg_not_supplied, success, failure
from syscore.interactive.menus import print_menu_of_values_and_get_response

from sysdata.config.production_config import get_production_config
from sysdata.data_blob import dataBlob

from sysobjects.production.backtest_storage import interactiveBacktest
from sysproduction.data.generic_production_data import productionDataLayerGeneric
from sysproduction.data.strategies import (
    get_valid_strategy_name_from_user,
    diagStrategiesConfig,
)


PICKLE_EXT = ".pck"
CONFIG_EXT = ".yaml"
PICKLE_FILE_SUFFIX = "_backtest"
CONFIG_FILE_SUFFIX = "_config"
PICKLE_SUFFIX = PICKLE_FILE_SUFFIX + PICKLE_EXT
CONFIG_SUFFIX = CONFIG_FILE_SUFFIX + CONFIG_EXT


def user_choose_backtest(data: dataBlob = arg_not_supplied) -> interactiveBacktest:
    (
        strategy_name,
        timestamp,
    ) = interactively_choose_strategy_name_timestamp_for_backtest(data)
    data_backtest = dataBacktest(data=data)
    backtest = data_backtest.load_backtest(
        strategy_name=strategy_name, timestamp=timestamp
    )

    return backtest


def interactively_choose_strategy_name_timestamp_for_backtest(
    data: dataBlob = arg_not_supplied,
) -> (str, str):
    strategy_name = get_valid_strategy_name_from_user(data=data)
    timestamp = interactively_choose_timestamp(data=data, strategy_name=strategy_name)

    return strategy_name, timestamp


def interactively_choose_timestamp(
    strategy_name: str, data: dataBlob = arg_not_supplied
):
    data_backtest = dataBacktest(data)
    list_of_timestamps = sorted(
        data_backtest.get_list_of_timestamps_for_strategy(strategy_name)
    )
    # most recent last
    print("Choose the backtest to load:\n")
    timestamp = print_menu_of_values_and_get_response(
        list_of_timestamps, default_str=list_of_timestamps[-1]
    )
    return timestamp


class dataBacktest(productionDataLayerGeneric):
    def get_most_recent_backtest(self, strategy_name: str) -> interactiveBacktest:
        list_of_timestamps = sorted(
            self.get_list_of_timestamps_for_strategy(strategy_name)
        )
        # most recent last
        timestamp_to_use = list_of_timestamps[-1]

        backtest = self.load_backtest(strategy_name, timestamp_to_use)
        return backtest

    def load_backtest(self, strategy_name: str, timestamp: str) -> interactiveBacktest:
        system = create_system_with_saved_state(self.data, strategy_name, timestamp)

        backtest = interactiveBacktest(
            system=system, strategy_name=strategy_name, timestamp=timestamp
        )

        return backtest

    def get_list_of_timestamps_for_strategy(self, strategy_name):
        timestamp_list = get_list_of_timestamps_for_strategy(strategy_name)
        return timestamp_list


def get_list_of_timestamps_for_strategy(strategy_name):
    list_of_files = get_list_of_pickle_files_for_strategy(strategy_name)
    list_of_timestamps = [
        rchop(file_name, PICKLE_FILE_SUFFIX) for file_name in list_of_files
    ]

    return list_of_timestamps


def create_system_with_saved_state(data, strategy_name, date_time_signature):
    """

    :param system_caller: some callable function that accepts a config parameter
    :param strategy_name: str
    :param date_time_signature: str
    :return: system
    """
    system_caller = get_system_caller(data, strategy_name, date_time_signature)
    system = system_caller()
    system = load_backtest_state(system, strategy_name, date_time_signature)

    return system


def get_system_caller(data, strategy_name, date_time_signature):
    # returns a method we can use to recreate a system

    strategy_loader_config_original = (
        get_strategy_class_backtest_loader_config_without_warning(
            data=data, strategy_name=strategy_name
        )
    )

    ## Whenever popping best to copy first
    strategy_loader_config = copy(strategy_loader_config_original)
    strategy_class_object = resolve_function(strategy_loader_config.pop("object"))
    function = strategy_loader_config.pop("function")
    config_filename = get_backtest_config_filename(strategy_name, date_time_signature)

    strategy_class_instance = strategy_class_object(
        data, strategy_name, backtest_config_filename=config_filename
    )
    method = getattr(strategy_class_instance, function)

    return method


def get_loader_config(data: dataBlob, strategy_name: str) -> dict:
    try:
        strategy_loader_config = (
            get_strategy_class_backtest_loader_config_without_warning(
                data, strategy_name
            )
        )
    except BaseException:
        strategy_loader_config = dict(
            object="sysproduction.strategy_code.run_system_classic.runSystemClassic",
            function="system_method",
        )
        data.log.warn(
            "No configuration strategy_list/strategy_name/load_backtests; using defaults %s"
            % str(strategy_loader_config)
        )

    return strategy_loader_config


def get_strategy_class_backtest_loader_config_without_warning(data, strategy_name):
    diag_strategy_config = diagStrategiesConfig(data)
    strategy_loader_config = (
        diag_strategy_config.get_strategy_config_dict_for_specific_process(
            strategy_name, "load_backtests"
        )
    )
    return strategy_loader_config


def load_backtest_state(system, strategy_name, date_time_signature):
    """
    Given a system, recover the saved state

    :param system: a system object whose config is compatible
    :param strategy_name: str

    :return: system with cache filled from pickled backtest state file
    """
    filename = get_backtest_pickle_filename(strategy_name, date_time_signature)
    system.cache.unpickle(filename)

    return system


def store_backtest_state(data, system, strategy_name="default_strategy"):
    """
    Store a pickled backtest state and backtest config for a system

    :param data: data object, used to access the log
    :param system: a system object which has run
    :param strategy_name: str
    :param backtest_config_filename: the filename of the config used to run the backtest

    :return: success
    """

    ensure_backtest_directory_exists(strategy_name)

    datetime_marker = create_datetime_marker_string()

    pickle_filename = get_backtest_pickle_filename(strategy_name, datetime_marker)
    pickle_state(data, system, pickle_filename)

    config_save_filename = get_backtest_config_filename(strategy_name, datetime_marker)
    system.config.save(config_save_filename)

    return success


def ensure_backtest_directory_exists(strategy_name):
    full_directory = get_backtest_directory_for_strategy(strategy_name)
    try:
        os.makedirs(full_directory)
    except FileExistsError:
        pass


def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[: -len(suffix)]
    return None


def get_list_of_pickle_files_for_strategy(strategy_name):
    full_directory = get_backtest_directory_for_strategy(strategy_name)
    list_of_files = files_with_extension_in_pathname(full_directory, PICKLE_EXT)

    return list_of_files


def get_backtest_pickle_filename(strategy_name, datetime_marker):
    # eg
    # '/home/rob/data/backtests/medium_speed_TF_carry/20200616_122543_backtest.pck'
    prefix = get_backtest_filename_prefix(strategy_name, datetime_marker)
    suffix = PICKLE_SUFFIX

    return prefix + suffix


def get_backtest_config_filename(strategy_name, datetime_marker):
    # eg
    # '/home/rob/data/backtests/medium_speed_TF_carry/20200616_122543_config.yaml'
    prefix = get_backtest_filename_prefix(strategy_name, datetime_marker)
    suffix = CONFIG_SUFFIX

    return prefix + suffix


def get_backtest_filename_prefix(strategy_name, datetime_marker):
    # eg '/home/rob/data/backtests/medium_speed_TF_carry/20200622_102913'
    full_directory = get_backtest_directory_for_strategy(strategy_name)
    full_filename_prefix = os.path.join(full_directory, datetime_marker)

    return full_filename_prefix


def get_backtest_directory_for_strategy(strategy_name):
    # eg '/home/rob/data/backtests/medium_speed_TF_carry'
    directory_store_backtests = get_directory_store_backtests()

    directory_store_backtests = get_resolved_pathname(directory_store_backtests)
    full_directory = os.path.join(directory_store_backtests, strategy_name)

    return full_directory


def get_directory_store_backtests():
    # eg '/home/rob/data/backtests/'
    production_config = get_production_config()
    store_directory = production_config.get_element_or_missing_data(
        "backtest_store_directory"
    )
    if store_directory is missing_data:
        raise Exception("Need to specify backtest_store_directory in config file")

    return store_directory


def pickle_state(data, system, backtest_filename):

    try:
        system.cache.pickle(backtest_filename)
        data.log.msg("Pickled backtest state to %s" % backtest_filename)
        return success
    except Exception as e:
        data.log.warn(
            "Couldn't save backtest state to %s error %s" % (backtest_filename, e)
        )
        return failure


def copy_config_file(data, resolved_backtest_config_filename, config_save_filename):
    try:
        copyfile(resolved_backtest_config_filename, config_save_filename)
        data.log.msg(
            "Copied config file from %s to %s"
            % (resolved_backtest_config_filename, config_save_filename)
        )
        return success
    except Exception as e:
        data.log.warn(
            "Couldn't copy config file from %s to %s error %s"
            % (resolved_backtest_config_filename, config_save_filename, e)
        )
        return failure
