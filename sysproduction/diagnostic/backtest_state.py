import os
import datetime
from shutil import copyfile

from syscore.objects import success, failure, resolve_function
from syscore.fileutils import get_resolved_pathname, files_with_extension_in_pathname
from sysdata.private_config import get_private_then_default_key_value
from sysproduction.run_systems import get_strategy_class_object_config

PICKLE_EXT = ".pck"
CONFIG_EXT = ".yaml"
PICKLE_FILE_SUFFIX = "_backtest"
CONFIG_FILE_SUFFIX = "_config"
PICKLE_SUFFIX = PICKLE_FILE_SUFFIX + PICKLE_EXT
CONFIG_SUFFIX = CONFIG_FILE_SUFFIX + CONFIG_EXT

date_formatting = "%Y%m%d_%H%M%S"


def create_datetime_string(datetime_to_use):
    datetime_marker = datetime_to_use.strftime(date_formatting)

    return datetime_marker


def from_marker_to_datetime(datetime_marker):
    return datetime.datetime.strptime(datetime_marker, date_formatting)


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
    process_name = "load_backtests"
    try:
        config_this_process = get_strategy_class_object_config(
            process_name, data, strategy_name
        )
    except BaseException:
        data.log.warn(
            "No configuration strategy_list/strategy_name/load_backtests; using defaults"
        )
        config_this_process = dict(
            object="sysproduction.strategy_code.run_system_classic.runSystemClassic",
            function="system_method",
        )

    strategy_class_object = resolve_function(config_this_process.pop("object"))
    function = config_this_process.pop("function")
    config_filename = get_backtest_config_filename(
        strategy_name, date_time_signature)

    strategy_class_instance = strategy_class_object(
        data, strategy_name, backtest_config_filename=config_filename
    )
    method = getattr(strategy_class_instance, function)

    return method


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


def clean_backtest_files(strategy_name):
    """
    Remove all saved backtests which are too old

    Keep a file from one of each of the last N months
    Delete any other files which are more than a month old

    :param strategy_name:
    :return:
    """
    directory_store_backtests = get_directory_store_backtests()

    raise NotImplementedError


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
    datetime_to_use = datetime.datetime.now()
    datetime_marker = create_datetime_string(datetime_to_use)

    pickle_filename = get_backtest_pickle_filename(
        strategy_name, datetime_marker)
    pickle_state(data, system, pickle_filename)

    config_save_filename = get_backtest_config_filename(
        strategy_name, datetime_marker)
    system.config.save(config_save_filename)

    return success


def ensure_backtest_directory_exists(strategy_name):
    full_directory = get_backtest_directory_for_strategy(strategy_name)
    try:
        os.mkdir(full_directory)
    except FileExistsError:
        pass


def get_list_of_timestamps_for_strategy(strategy_name):
    list_of_files = get_list_of_pickle_files_for_strategy(strategy_name)
    list_of_timestamps = [
        rchop(file_name, PICKLE_FILE_SUFFIX) for file_name in list_of_files
    ]

    return list_of_timestamps


def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[: -len(suffix)]
    return None


def get_list_of_pickle_files_for_strategy(strategy_name):
    full_directory = get_backtest_directory_for_strategy(strategy_name)
    list_of_files = files_with_extension_in_pathname(
        full_directory, PICKLE_EXT)

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

    directory_store_backtests = get_resolved_pathname(
        directory_store_backtests)
    full_directory = os.path.join(directory_store_backtests, strategy_name)

    return full_directory


def get_directory_store_backtests():
    # eg '/home/rob/data/backtests/'
    key_name = "backtest_store_directory"
    store_directory = get_private_then_default_key_value(
        key_name, raise_error=True)

    return store_directory


def pickle_state(data, system, backtest_filename):

    try:
        system.cache.pickle(backtest_filename)
        data.log.msg("Pickled backtest state to %s" % backtest_filename)
        return success
    except Exception as e:
        data.log.warn(
            "Couldn't save backtest state to %s error %s" %
            (backtest_filename, e))
        return failure


def copy_config_file(
        data,
        resolved_backtest_config_filename,
        config_save_filename):
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
