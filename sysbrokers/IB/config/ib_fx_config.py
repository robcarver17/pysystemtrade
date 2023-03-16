from collections import namedtuple

import pandas as pd

from syscore.constants import missing_file, missing_instrument
from syscore.fileutils import resolve_path_and_filename_for_package
from syslogdiag.logger import CURRENCY_CODE_LOG_LABEL

IB_CCY_CONFIG_FILE = resolve_path_and_filename_for_package(
    "sysbrokers.IB.config.ib_config_spot_FX.csv"
)


ibFXConfig = namedtuple("ibFXConfig", ["ccy1", "ccy2", "invert"])


def get_ib_config_from_file(log) -> pd.DataFrame:
    try:
        config_data = pd.read_csv(IB_CCY_CONFIG_FILE)
    except BaseException:
        log.warn("Can't read file %s" % IB_CCY_CONFIG_FILE)
        config_data = missing_file

    return config_data


def config_info_for_code(config_data: pd.DataFrame, currency_code, log) -> ibFXConfig:
    new_log = log.setup(**{CURRENCY_CODE_LOG_LABEL: currency_code})
    if config_data is missing_file:
        new_log.warn(
            "Can't get IB FX config for %s as config file missing" % currency_code,
            fx_code=currency_code,
        )

        return missing_instrument

    ccy1 = config_data[config_data.CODE == currency_code].CCY1.values[0]
    ccy2 = config_data[config_data.CODE == currency_code].CCY2.values[0]
    invert = config_data[config_data.CODE == currency_code].INVERT.values[0] == "YES"

    ib_config_for_code = ibFXConfig(ccy1, ccy2, invert)

    return ib_config_for_code


def get_list_of_codes(log, config_data: pd.DataFrame) -> list:
    if config_data is missing_file:
        log.warn("Can't get list of fxcodes for IB as config file missing")
        return []

    list_of_codes = list(config_data.CODE)

    return list_of_codes
