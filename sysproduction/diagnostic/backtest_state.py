import os
import datetime
from shutil import copyfile

from syscore.objects import success, failure, arg_not_supplied
from syscore.fileutils import get_resolved_pathname, get_filename_for_package
from sysdata.private_config import get_private_then_default_key_value

def get_directory_store_backtests():
    key_name = 'backtest_store_directory'
    store_directory = get_private_then_default_key_value(key_name, raise_error=True)

    return store_directory

def load_backtest_state(system, strategy_name, date_time_signature):
    """
    Given a system, recover the saved state

    :param system: a system object whose config is compatible
    :param strategy_name: str

    :return: system with cache filled from pickled backtest state file
    """
    directory_store_backtests = get_directory_store_backtests()
    raise NotImplementedError

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

def store_backtest_state(data, system, strategy_name="default_strategy",
                     backtest_config_filename=arg_not_supplied):
    """
    Store a pickled backtest state and backtest config for a system

    :param data: data object, used to access the log
    :param system: a system object which has run
    :param strategy_name: str
    :param backtest_config_filename: the filename of the config used to run the backtest

    :return: success
    """

    if backtest_config_filename is arg_not_supplied:
        error_msg = "Have to provide a backtest config file name to store state"
        data.log.warn(error_msg)
        raise Exception(error_msg)

    full_filename_prefix = get_state_filename_prefix( strategy_name)

    backtest_filename = full_filename_prefix + "_backtest.pck"
    pickle_state(data, system, backtest_filename)

    config_save_filename = full_filename_prefix + "_config.yaml"
    resolved_backtest_config_filename = get_filename_for_package(backtest_config_filename)
    copy_config_file(data, resolved_backtest_config_filename, config_save_filename)

    return success

def get_state_filename_prefix(strategy_name):
    directory_store_backtests = get_directory_store_backtests()

    directory_store_backtests = get_resolved_pathname(directory_store_backtests)
    full_directory = os.path.join(directory_store_backtests, strategy_name)
    try:
        os.mkdir(full_directory)
    except FileExistsError:
        pass
    datetime_marker = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename_prefix = os.path.join(full_directory, datetime_marker)

    return full_filename_prefix


def pickle_state(data, system, backtest_filename):

    try:
        system.cache.pickle(backtest_filename)
        data.log.msg("Pickled backtest state to %s" % backtest_filename)
        return success
    except Exception as e:
        data.log.warn("Couldn't save backtest state to %s error %s" % (backtest_filename, e))
        return failure

def copy_config_file(data, resolved_backtest_config_filename, config_save_filename):
    try:
        copyfile(resolved_backtest_config_filename, config_save_filename)
        data.log.msg("Copied config file from %s to %s" % (resolved_backtest_config_filename, config_save_filename))
        return success
    except Exception as e:
        data.log.warn("Couldn't copy config file from %s to %s error %s" % (resolved_backtest_config_filename,
                                                                            config_save_filename,
                                                                            e))
        return failure

