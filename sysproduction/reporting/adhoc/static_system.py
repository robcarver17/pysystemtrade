from systems.provided.rob_system.run_system import futures_system, System
from copy import copy
from systems.provided.static_small_system_optimise.optimise_small_system import (
    find_best_ordered_set_of_instruments,
    get_correlation_matrix,
)

from sysquant.estimators.correlation_estimator import correlationEstimate
from sysproduction.reporting.reporting_functions import (
    parse_report_results,
    output_file_report,
    header,
    body_text,
)

from sysdata.data_blob import dataBlob

from sysproduction.reporting.report_configs import reportConfig


def static_system_adhoc_report(
    system_function, list_of_capital_and_estimate_instrument_count_tuples: list
):

    data = dataBlob()
    report_config = reportConfig(
        title="Static selection of instruments", function="not_used", output="file"
    )

    system = system_function()
    corr_matrix = get_correlation_matrix(system)  ## capital irrelevant

    all_results = []
    all_results.append(
        header(
            "Selected instruments using static selection for different levels of capital"
        )
    )
    for (
        capital,
        est_number_of_instruments,
    ) in list_of_capital_and_estimate_instrument_count_tuples:
        system = futures_system()
        instrument_list = static_system_results_for_capital(
            system,
            corr_matrix=corr_matrix,
            est_number_of_instruments=est_number_of_instruments,
            capital=capital,
        )

        text_to_output = body_text(
            "For capital of %d, %d instruments, Selected order: %s"
            % (capital, len(instrument_list), str(instrument_list))
        )
        all_results.append(text_to_output)

        instrument_list.sort()
        text_to_output = body_text("Sorted: %s \n" % (str(instrument_list)))
        all_results.append(text_to_output)

    parsed_report_results = parse_report_results(data, report_results=all_results)

    output_file_report(
        parsed_report=parsed_report_results, data=data, report_config=report_config
    )


def static_system_results_for_capital(
    system: System,
    corr_matrix: correlationEstimate,
    est_number_of_instruments: int,
    capital: float,
):

    notional_starting_IDM = est_number_of_instruments**0.25
    max_instrument_weight = 1.0 / est_number_of_instruments

    return find_best_ordered_set_of_instruments(
        system=system,
        corr_matrix=corr_matrix,
        capital=capital,
        max_instrument_weight=max_instrument_weight,
        notional_starting_IDM=notional_starting_IDM,
    )


if __name__ == "__main__":
    list_of_capital_and_estimate_instrument_count_tuples = [
        [10000, 5],
        [25000, 7],
        [50000, 14],
        [100000, 16],
        [250000, 22],
        [500000, 28],
        [1000000, 36],
        [2500000, 40],
        [5000000, 50],
        [10000000, 50],
        [25000000, 50],
    ]
    static_system_adhoc_report(
        system_function=futures_system,
        list_of_capital_and_estimate_instrument_count_tuples=list_of_capital_and_estimate_instrument_count_tuples,
    )
