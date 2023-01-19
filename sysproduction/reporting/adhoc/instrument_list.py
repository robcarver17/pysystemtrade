import pandas as pd

from syscore.interactive.progress_bar import progressBar

from sysproduction.data.broker import dataBroker
from sysproduction.data.instruments import diagInstruments
from sysproduction.reporting.reporting_functions import (
    parse_report_results,
    output_file_report,
    header,
    table,
    pandas_display_for_reports,
)
from sysproduction.reporting.report_configs import reportConfig
from sysproduction.reporting.data.costs import get_tick_value_for_instrument_code

from sysdata.data_blob import dataBlob


def instrument_list_report():

    report_config = reportConfig(
        title="Instrument list", function="not_used", output="file"
    )

    data = dataBlob()

    diag_instruments = diagInstruments(data)
    list_of_instruments = diag_instruments.get_list_of_instruments()

    p = progressBar(len(list_of_instruments))
    list_of_results = []
    for instrument_code in list_of_instruments:
        row_for_instrument = instrument_results_as_pd_df_row(
            data=data, instrument_code=instrument_code
        )
        list_of_results.append(row_for_instrument)
        p.iterate()

    results_as_df = pd.concat(list_of_results, axis=0)

    report_results = []
    report_results.append(header("List of instruments with configuration"))
    report_results.append(table("Columns are ", results_as_df))

    pandas_display_for_reports()

    parsed_report_results = parse_report_results(data, report_results=report_results)

    output_file_report(
        parsed_report=parsed_report_results, data=data, report_config=report_config
    )


def instrument_results_as_pd_df_row(data: dataBlob, instrument_code: str):
    diag_instruments = diagInstruments(data)
    meta_data = diag_instruments.get_meta_data(instrument_code)
    data_broker = dataBroker(data)
    instrument_broker_data = data_broker.get_brokers_instrument_with_metadata(
        instrument_code
    )
    tick_value = get_tick_value_for_instrument_code(
        data=data, instrument_code=instrument_code
    )

    meta_data_as_dict = meta_data.as_dict()
    broker_data_as_dict = instrument_broker_data.meta_data.as_dict()
    relabelled_broker_data_as_dict = dict(
        [("Broker_%s" % key, value) for key, value in broker_data_as_dict.items()]
    )

    merged_data = {**meta_data_as_dict, **relabelled_broker_data_as_dict}
    merged_data["tick_value"] = tick_value

    merged_data_as_pd = pd.DataFrame(merged_data, index=[instrument_code])

    return merged_data_as_pd


if __name__ == "__main__":
    instrument_list_report()
