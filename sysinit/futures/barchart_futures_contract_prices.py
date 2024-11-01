from sysdata.csv.csv_futures_contract_prices import ConfigCsvFuturesPrices
import os
from syscore.fileutils import (
    get_resolved_pathname,
    files_with_extension_in_resolved_pathname,
)
from syscore.dateutils import month_from_contract_letter

from sysinit.futures.contract_prices_from_csv_to_db import (
    init_db_with_csv_futures_contract_prices,
)


def strip_file_names(pathname):
    # These won't have .csv attached
    resolved_pathname = get_resolved_pathname(pathname)
    file_names = files_with_extension_in_resolved_pathname(resolved_pathname)
    for filename in file_names:
        identifier = filename.split("_")[0]
        yearcode = int(identifier[len(identifier) - 2 :])
        monthcode = identifier[len(identifier) - 3].upper()
        if yearcode > 50:
            year = 1900 + yearcode
        else:
            year = 2000 + yearcode
        month = month_from_contract_letter(monthcode)
        marketcode = identifier[: len(identifier) - 3].upper()
        instrument = market_map[marketcode]

        datecode = str(year) + "{0:02d}".format(month)

        new_file_name = "%s_%s00.csv" % (instrument, datecode)
        new_full_name = os.path.join(resolved_pathname, new_file_name)
        old_full_name = os.path.join(resolved_pathname, filename + ".csv")
        print("Rename %s to\n %s" % (old_full_name, new_full_name))

        os.rename(old_full_name, new_full_name)

    return None


market_map = dict(
    AE="AEX",
    A6="AUD",
    HR="BOBL",
    II="BTP",
    GG="BUND",
    MX="CAC",
    BJ="CHEESE",
    KG="COTTON",
    HG="COPPER",
    ZC="CORN",
    CL="CRUDE_W",
    GE="EDOLLAR",
    E6="EUR",
    NG="GAS_US",
    B6="GBP",
    GC="GOLD",
    J6="JPY",
    HE="LEANHOG",
    LE="LIVECOW",
    DF="MILKDRY",
    DK="MILKWET",
    M6="MXP",
    NQ="NASDAQ",
    N6="NZD",
    FN="OAT",
    PA="PALLAD",
    HF="SHATZ",
    PL="PLAT",
    ZS="SOYBEAN",
    ES="SP500",
    ZT="US2",
    ZF="US5",
    ZN="US10",
    ZB="US20",
    VI="VIX",
    ZW="WHEAT",
    DV="V2X",
    UD="US30",
    FX="EUROSTX",
    GR="GOLD_micro",
    NM="NASDAQ_micro",
    QM="CRUDE_W_mini",
    QG="GAS_US_mini",
    ET="SP500_micro",
)


barchart_csv_config = ConfigCsvFuturesPrices(
    input_date_index_name="Time",
    input_skiprows=0,
    input_skipfooter=1,
    input_date_format="%m/%d/%Y",
    input_column_mapping=dict(
        OPEN="Open", HIGH="High", LOW="Low", FINAL="Last", VOLUME="Volume"
    ),
)


def transfer_barchart_prices_to_db(datapath):
    strip_file_names(datapath)
    init_db_with_csv_futures_contract_prices(datapath, csv_config=barchart_csv_config)


if __name__ == "__main__":
    input("Will overwrite existing prices are you sure?! CTL-C to abort")
    # modify flags as required
    datapath = "*** NEED TO DEFINE A DATAPATH ***"
    transfer_barchart_prices_to_db(datapath)
