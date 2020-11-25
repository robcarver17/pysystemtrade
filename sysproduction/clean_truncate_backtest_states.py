from syscore.fileutils import delete_old_files_with_extension_in_pathname
from sysproduction.diagnostic.backtest_state import get_directory_store_backtests
from sysdata.data_blob import dataBlob


def clean_truncate_backtest_states():
    data = dataBlob()
    cleaner = cleanTruncateBacktestStates(data)
    cleaner.clean_backtest_states()

    return None


class cleanTruncateBacktestStates:
    def __init__(self, data):
        self.data = data

    def clean_backtest_states(self):
        directory_to_use = get_directory_store_backtests()
        self.data.log.msg(
            "Deleting old .pck and .yaml backtest state files in directory %s"
            % directory_to_use
        )
        delete_old_files_with_extension_in_pathname(
            directory_to_use, days_old=5, extension=".pck"
        )
        delete_old_files_with_extension_in_pathname(
            directory_to_use, days_old=5, extension=".yaml"
        )
