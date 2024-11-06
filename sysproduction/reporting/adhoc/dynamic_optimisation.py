"""
# include these lines if running line by line in IDE console mode, but don't work in a headless server

import matplotlib
matplotlib.use("TkAgg")
"""

import matplotlib.pyplot as plt
from matplotlib import cm
import pandas as pd
import numpy as np

from sysproduction.data.strategies import get_valid_strategy_name_from_user
from sysdata.data_blob import dataBlob

from sysproduction.reporting.data.risk import (
    get_asset_classes_for_instrument_list,
    calculate_dict_of_beta_loadings_by_asset_class_given_weights,
    get_beta_for_instrument_list,
    get_current_annualised_perc_stdev_for_instrument,
)

from sysproduction.reporting.reporting_functions import (
    parse_report_results,
    output_file_report,
    PdfOutputWithTempFileName,
)
from sysproduction.reporting.report_configs import reportConfig
from sysproduction.data.optimal_positions import dataOptimalPositions

from sysquant.estimators.stdev_estimator import stdevEstimates
from sysquant.optimisation.weights import portfolioWeights

from sysdata.config.production_config import get_production_config


def get_notional_risk_target():
    ## might be overridden by strategy but we don't have the backtest .yaml here
    return 25.0


def dynamic_optimisation_graphical(data: dataBlob, strategy_name: str):
    report_config = reportConfig(
        title="Dynamic Optimisation Graphical", function="not_used", output="file"
    )

    report_output = get_figures_for_DO(data, strategy_name)

    parsed_report_results = parse_report_results(data, report_results=report_output)

    output_file_report(
        parsed_report=parsed_report_results, data=data, report_config=report_config
    )


def get_figures_for_DO(data: dataBlob, strategy_name: str):
    df_results = get_data_for_scatter_plot(data, strategy_name)
    all_results = []
    index_risk = get_notional_risk_target()

    loadings_natural_risk_df, loadings_fix_index_risk_df = get_pd_df_of_betas_to_plot(
        data, strategy_name=strategy_name, index_risk=index_risk
    )

    pdf_output = PdfOutputWithTempFileName(data)
    loadings_fix_index_risk_df.plot.bar()
    plt.title("Beta loadings with index risk set to %.1f annualised" % index_risk)
    figure_object = pdf_output.save_chart_close_and_return_figure()
    all_results.append(figure_object)

    pdf_output = PdfOutputWithTempFileName(data)
    loadings_natural_risk_df.plot.bar()
    plt.title("Beta loadings with natural risk for asset class index")
    figure_object = pdf_output.save_chart_close_and_return_figure()
    all_results.append(figure_object)

    pdf_output = PdfOutputWithTempFileName(data)
    plot_scatter_colors_only(df_results)
    plt.title(
        "Optimised vs rounded weight*stdev scatter plot, colours are asset classes"
    )
    figure_object = pdf_output.save_chart_close_and_return_figure()
    all_results.append(figure_object)

    list_of_asset_classes = list(set(list(df_results.asset_classes)))
    for asset_class in list_of_asset_classes:
        pdf_output = PdfOutputWithTempFileName(data)
        plot_scatter_for_asset_class(df_results, asset_class)
        plt.title("Optimised vs rounded weight*stdev scatter plot for %s" % asset_class)
        figure_object = pdf_output.save_chart_close_and_return_figure()
        all_results.append(figure_object)

    return all_results


def get_data_for_scatter_plot(data: dataBlob, strategy_name: str) -> pd.DataFrame:
    optimal_position_objects_as_list = get_optimal_position_objects_as_list(
        data=data, strategy_name=strategy_name
    )
    unrounded_weights = get_unrounded_weights(optimal_position_objects_as_list)
    optimised_weights = get_optimised_weights(optimal_position_objects_as_list)

    list_of_instruments = instrument_codes_from_optimal_positions_as_list(
        optimal_position_objects_as_list
    )
    stdev = get_standard_deviations_for_instrument_list(data, list_of_instruments)

    unrounded_weights_product_risk = unrounded_weights.product_with_stdev(stdev)
    optimised_weights_product_risk = optimised_weights.product_with_stdev(stdev)

    dict_of_asset_classes = get_asset_classes_for_instrument_list(
        data, list_of_instruments
    )

    results = pd.DataFrame(
        dict(
            unrounded_weights_product_risk=unrounded_weights_product_risk,
            optimised_weights_product_risk=optimised_weights_product_risk,
            asset_classes=dict_of_asset_classes,
        ),
        index=list_of_instruments,
    )

    return results


def plot_scatter_for_asset_class(results: pd.DataFrame, asset_class: str):
    subset_results = results[results.asset_classes == asset_class]
    plot_scatter_names_only(subset_results)


def plot_scatter_names_only(results: pd.DataFrame):
    list_of_instruments = list(results.index)
    x_figures = results.unrounded_weights_product_risk
    y_figures = results.optimised_weights_product_risk
    fig, ax = plt.subplots()
    ax.scatter(x_figures, y_figures, marker="")
    for i, txt in enumerate(list_of_instruments):
        ax.annotate(txt, (x_figures[i], y_figures[i]))


def plot_scatter_colors_only(results: pd.DataFrame):
    list_of_asset_classes = list(results.asset_classes)
    unique_list_of_asset_classes = list(set(list_of_asset_classes))
    code_asset_class_as_integer = [
        unique_list_of_asset_classes.index(asset_class)
        for asset_class in list_of_asset_classes
    ]
    color_map = cm.rainbow(np.linspace(0, 1, len(unique_list_of_asset_classes)))
    asset_class_color_list = [color_map[i] for i in code_asset_class_as_integer]
    results.plot.scatter(
        "unrounded_weights_product_risk",
        "optimised_weights_product_risk",
        c=asset_class_color_list,
    )


def get_unrounded_weights(optimal_positions_as_list) -> portfolioWeights:
    return portfolioWeights(
        get_item_from_optimised_weights_list(
            optimal_positions_as_list, "optimum_weight"
        )
    )


def get_optimised_weights(optimal_positions_as_list) -> portfolioWeights:
    return portfolioWeights(
        get_item_from_optimised_weights_list(
            optimal_positions_as_list, "optimised_weight"
        )
    )


def get_item_from_optimised_weights_list(
    optimal_positions_as_list: list, item_name: str
) -> dict:
    optimal_weights_as_dict = dict(
        [
            (
                op.instrument_strategy.instrument_code,
                getattr(op.optimal_position, item_name),
            )
            for op in optimal_positions_as_list
        ]
    )

    return optimal_weights_as_dict


def get_optimal_position_objects_as_list(data: dataBlob, strategy_name: str):
    data_optimal_positions = dataOptimalPositions(data)
    optimal_positions_as_list = (
        data_optimal_positions.get_list_of_current_optimal_positions_for_strategy_name(
            strategy_name
        )
    )
    return optimal_positions_as_list


def instrument_codes_from_optimal_positions_as_list(optimal_positions_as_list) -> list:
    return [op.instrument_strategy.instrument_code for op in optimal_positions_as_list]


def get_standard_deviations_for_instrument_list(
    data: dataBlob, instrument_list: list
) -> stdevEstimates:
    stdev_dict = dict(
        [
            (
                instrument_code,
                get_current_annualised_perc_stdev_for_instrument(data, instrument_code),
            )
            for instrument_code in instrument_list
        ]
    )

    return stdevEstimates(stdev_dict)


def get_pd_df_of_betas_to_plot(
    data: dataBlob, strategy_name: str, index_risk: float
) -> tuple:
    optimal_position_objects_as_list = get_optimal_position_objects_as_list(
        data=data, strategy_name=strategy_name
    )
    unrounded_weights = get_unrounded_weights(optimal_position_objects_as_list)
    optimised_weights = get_optimised_weights(optimal_position_objects_as_list)

    list_of_instruments = instrument_codes_from_optimal_positions_as_list(
        optimal_position_objects_as_list
    )
    dict_of_asset_classes = get_asset_classes_for_instrument_list(
        data, list_of_instruments
    )

    dict_of_betas_natural_risk = get_beta_for_instrument_list(
        data=data, dict_of_asset_classes=dict_of_asset_classes
    )

    loadings_natural_risk_df = get_pd_df_of_beta_loadings(
        unrounded_weights=unrounded_weights,
        optimised_weights=optimised_weights,
        dict_of_betas=dict_of_betas_natural_risk,
        dict_of_asset_classes=dict_of_asset_classes,
    )

    dict_of_betas_fix_index_risk = get_beta_for_instrument_list(
        data=data, dict_of_asset_classes=dict_of_asset_classes, index_risk=index_risk
    )

    loadings_fix_index_risk_df = get_pd_df_of_beta_loadings(
        unrounded_weights=unrounded_weights,
        optimised_weights=optimised_weights,
        dict_of_betas=dict_of_betas_fix_index_risk,
        dict_of_asset_classes=dict_of_asset_classes,
    )

    return loadings_natural_risk_df, loadings_fix_index_risk_df


def get_pd_df_of_beta_loadings(
    unrounded_weights: portfolioWeights,
    optimised_weights: portfolioWeights,
    dict_of_betas: dict,
    dict_of_asset_classes: dict,
):
    beta_loadings_unrounded = (
        calculate_dict_of_beta_loadings_by_asset_class_given_weights(
            unrounded_weights, dict_of_betas, dict_of_asset_classes
        )
    )

    beta_loadings_optimised = (
        calculate_dict_of_beta_loadings_by_asset_class_given_weights(
            optimised_weights, dict_of_betas, dict_of_asset_classes
        )
    )

    both_loadings = pd.concat(
        [pd.Series(beta_loadings_unrounded), pd.Series(beta_loadings_optimised)], axis=1
    )

    both_loadings.columns = ["Unrounded", "Optimised weights"]
    both_loadings = both_loadings.sort_index()

    return both_loadings


def dynamic_optimisation_text(data: dataBlob, strategy_name: str):
    report_config = reportConfig(
        title="Dynamic Optimisation Text", function="not_used", output="file"
    )

    report_output = []

    #### WE'D ADD REPORT OBJECTS LIKE BODY_TEXT, TABLE HERE

    parsed_report_results = parse_report_results(data, report_results=report_output)

    output_file_report(
        parsed_report=parsed_report_results, data=data, report_config=report_config
    )


if __name__ == "__main__":
    ### Do two separate reports, one graphical, one text

    data = dataBlob()
    ## interactively get backtest to use
    strategy_name = get_valid_strategy_name_from_user(data)
    dynamic_optimisation_graphical(strategy_name=strategy_name, data=data)

    dynamic_optimisation_text(strategy_name=strategy_name, data=data)
