
import matplotlib

"""
# include these lines if running line by line in IDE console mode, but don't work in a headless server

import matplotlib
matplotlib.use("TkAgg")
"""

import matplotlib.pyplot as plt
from matplotlib import cm
import pandas as pd
import numpy as np
import statsmodels.formula.api as sm


from syscore.pdutils import prices_to_daily_prices
from syscore.dateutils import n_days_ago
from sysproduction.data.strategies import get_valid_strategy_name_from_user
from sysdata.data_blob import dataBlob

from sysproduction.data.backtest import interactiveBacktest
from sysproduction.data.risk import get_current_annualised_perc_stdev_for_instrument
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.prices import diagPrices

from sysproduction.reporting.reporting_functions import parse_report_results, output_file_report, PdfOutputWithTempFileName
from sysproduction.reporting.report_configs import reportConfig
from sysproduction.data.positions import dataOptimalPositions

from sysquant.estimators.stdev_estimator import stdevEstimates
from sysquant.optimisation.weights import portfolioWeights

def dynamic_optimisation_graphical(data: dataBlob,
                                   strategy_name: str):

    report_config = reportConfig(
        title="Dynamic Optimisation Graphical",
        function="not_used",
        output="file"
    )

    report_output = get_figures_for_DO(data,
                                       strategy_name)

    parsed_report_results = parse_report_results(data,
                                          report_results=report_output)

    output_file_report(parsed_report=parsed_report_results,
                       data=data, report_config=report_config)

def get_figures_for_DO(data: dataBlob,
                       strategy_name: str):

    df_results = get_data_for_scatter_plot(data, strategy_name)
    all_results = []

    pd_df_of_betas_to_plot = get_pd_df_of_betas_to_plot(data,
                                                        strategy_name=strategy_name)

    pdf_output = PdfOutputWithTempFileName(data)
    pd_df_of_betas_to_plot.plot.bar()
    plt.title("Beta loadings")
    figure_object = pdf_output.save_chart_close_and_return_figure()
    all_results.append(figure_object)

    pdf_output = PdfOutputWithTempFileName(data)
    plot_scatter_colors_only(df_results)
    plt.title("Optimised vs rounded weight*stdev scatter plot, colours are asset classes")
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

def get_data_for_scatter_plot(data: dataBlob,
                              strategy_name: str) -> pd.DataFrame:

    optimal_position_objects_as_list = get_optimal_position_objects_as_list(data=data, strategy_name=strategy_name)
    unrounded_weights = get_unrounded_weights(optimal_position_objects_as_list)
    optimised_weights = get_optimised_weights(optimal_position_objects_as_list)

    list_of_instruments = instrument_codes_from_optimal_positions_as_list(optimal_position_objects_as_list)
    stdev = get_standard_deviations_for_instrument_list(data, list_of_instruments)

    unrounded_weights_product_risk = unrounded_weights.product_with_stdev(stdev)
    optimised_weights_product_risk = optimised_weights.product_with_stdev(stdev)

    dict_of_asset_classes = get_asset_classes_for_instrument_list(data, list_of_instruments)

    results =  pd.DataFrame(
        dict(unrounded_weights_product_risk = unrounded_weights_product_risk,
             optimised_weights_product_risk = optimised_weights_product_risk,
             asset_classes = dict_of_asset_classes),
        index = list_of_instruments
    )

    return results

def plot_scatter_for_asset_class(results: pd.DataFrame,
                                 asset_class: str):

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
    code_asset_class_as_integer = [unique_list_of_asset_classes.index(asset_class)
                                   for asset_class in list_of_asset_classes]
    color_map = cm.rainbow(np.linspace(0,1,len(unique_list_of_asset_classes)))
    asset_class_color_list = [color_map[i] for i in code_asset_class_as_integer]
    results.plot.scatter('unrounded_weights_product_risk',
                         'optimised_weights_product_risk',
                         c = asset_class_color_list)



def get_unrounded_weights(optimal_positions_as_list) -> portfolioWeights:
    return portfolioWeights(get_item_from_optimised_weights_list(optimal_positions_as_list,
                                                'optimum_weight'))


def get_optimised_weights(optimal_positions_as_list) -> portfolioWeights:
    return portfolioWeights(get_item_from_optimised_weights_list(optimal_positions_as_list,
                                                'optimised_weight'))

def get_item_from_optimised_weights_list(optimal_positions_as_list: list,
                                         item_name: str) -> dict:

    optimal_weights_as_dict = dict([
        (op.instrument_strategy.instrument_code,
        getattr(op.optimal_position, item_name))
        for op in optimal_positions_as_list])

    return optimal_weights_as_dict


def get_optimal_position_objects_as_list(data: dataBlob, strategy_name: str):
    data_optimal_positions = dataOptimalPositions(data)
    optimal_positions_as_list = data_optimal_positions.get_list_of_current_optimal_positions_for_strategy_name(strategy_name)
    return optimal_positions_as_list

def instrument_codes_from_optimal_positions_as_list(optimal_positions_as_list) -> list:
   return [
        op.instrument_strategy.instrument_code
        for op in optimal_positions_as_list]


def get_standard_deviations_for_instrument_list(data: dataBlob,
                                                instrument_list: list) -> stdevEstimates:

    stdev_dict = dict([
        (instrument_code, get_current_annualised_perc_stdev_for_instrument(data,
                                                                           instrument_code))
        for instrument_code in instrument_list
    ])

    return stdevEstimates(stdev_dict)


def get_asset_classes_for_instrument_list(data, instrument_codes: list) -> dict:
    diag_instruments = diagInstruments(data)

    dict_of_asset_classes = dict([
        (instrument_code,
         diag_instruments.get_asset_class(instrument_code))

        for instrument_code in instrument_codes
    ])

    return dict_of_asset_classes

def get_pd_df_of_betas_to_plot(data: dataBlob,
                           strategy_name: str) -> pd.DataFrame:

    optimal_position_objects_as_list = get_optimal_position_objects_as_list(data=data, strategy_name=strategy_name)
    unrounded_weights = get_unrounded_weights(optimal_position_objects_as_list)
    optimised_weights = get_optimised_weights(optimal_position_objects_as_list)

    list_of_instruments = instrument_codes_from_optimal_positions_as_list(optimal_position_objects_as_list)
    dict_of_asset_classes = get_asset_classes_for_instrument_list(data, list_of_instruments)

    dict_of_betas = get_beta_for_instrument_list(data=data,
                                                 dict_of_asset_classes=dict_of_asset_classes)

    beta_loadings_unrounded =\
        calculate_dict_of_beta_loadings_by_asset_class_given_weights(
            unrounded_weights,
            dict_of_betas,
            dict_of_asset_classes)

    beta_loadings_optimised = \
        calculate_dict_of_beta_loadings_by_asset_class_given_weights(
            optimised_weights,
            dict_of_betas,
            dict_of_asset_classes)

    both_loadings = pd.concat([
                              pd.Series(beta_loadings_unrounded),
                              pd.Series(beta_loadings_optimised)],
                              axis=1)
    both_loadings.columns = ['Unrounded', 'Optimised weights']

    return both_loadings

def calculate_dict_of_beta_loadings_by_asset_class_given_weights(
                        weights: portfolioWeights,
                        dict_of_betas: dict,
                        dict_of_asset_classes: dict
                                        ) -> dict:

    dict_of_beta_loadings_per_instrument = calculate_dict_of_beta_loadings_per_instrument(
        dict_of_betas=dict_of_betas, weights=weights
    )

    beta_loadings_across_asset_classes = calculate_beta_loadings_across_asset_classes(
        dict_of_asset_classes=dict_of_asset_classes,
        dict_of_beta_loadings_per_instrument=dict_of_beta_loadings_per_instrument
    )

    return beta_loadings_across_asset_classes

def calculate_dict_of_beta_loadings_per_instrument(
        dict_of_betas: dict,
    weights: portfolioWeights
        ) -> dict:

    list_of_instruments = weights.assets

    dict_of_beta_loadings_per_instrument =\
         dict([
             (instrument_code,
              dict_of_betas[instrument_code] * weights[instrument_code])
             for instrument_code in list_of_instruments
         ])

    return dict_of_beta_loadings_per_instrument

def calculate_beta_loadings_across_asset_classes(
                                            dict_of_asset_classes: dict,
                                           dict_of_beta_loadings_per_instrument: dict
                                            ) -> dict:

    list_of_asset_classes = list(set(list(dict_of_asset_classes.values())))
    beta_loadings_across_asset_classes = dict([
        (asset_class,
         calculate_beta_loading_for_asset_class(asset_class=asset_class,
                                                dict_of_asset_classes=dict_of_asset_classes,
                                                dict_of_beta_loadings_per_instrument=dict_of_beta_loadings_per_instrument))
        for asset_class in list_of_asset_classes
    ])

    return beta_loadings_across_asset_classes

def calculate_beta_loading_for_asset_class(asset_class: str,
                                           dict_of_asset_classes: dict,
                                           dict_of_beta_loadings_per_instrument: dict
                                           ) -> dict:

    relevant_instruments = [instrument_code for
                            instrument_code, asset_class_for_instrument in
                            dict_of_asset_classes.items()
                            if asset_class == asset_class_for_instrument]

    relevant_beta_loads = np.array([
        dict_of_beta_loadings_per_instrument[instrument_code]
        for instrument_code in relevant_instruments
    ])

    return np.nansum(relevant_beta_loads)

def get_beta_for_instrument_list(data: dataBlob,
                            dict_of_asset_classes: dict):

    list_of_instruments = list(dict_of_asset_classes.keys())
    perc_returns = last_years_perc_returns_for_list_of_instruments(data=data,
                                                                   list_of_instruments=list_of_instruments)
    equally_weighted_returns_across_asset_classes = get_equally_weighted_returns_across_asset_classes(
        dict_of_asset_classes=dict_of_asset_classes,
        perc_returns=perc_returns,

    )
    dict_of_betas = dict_of_beta_by_instrument(dict_of_asset_classes=dict_of_asset_classes,
                                               perc_returns=perc_returns,
                                               equally_weighted_returns_across_asset_classes=equally_weighted_returns_across_asset_classes)

    return dict_of_betas

def last_years_perc_returns_for_list_of_instruments(data: dataBlob,
                            list_of_instruments: list) -> pd.DataFrame:
    diag_prices = diagPrices(data)
    adj_prices_as_dict = dict(
        (instrument_code,
         diag_prices.get_adjusted_prices(instrument_code))
        for instrument_code in list_of_instruments
    )

    adj_prices_as_df = pd.concat(adj_prices_as_dict, axis=1)
    adj_prices_as_df.columns = list_of_instruments
    daily_adj_prices_as_df = prices_to_daily_prices(adj_prices_as_df)
    last_year_daily_adj_prices_as_df = daily_adj_prices_as_df[n_days_ago(365):]
    perc_returns = (last_year_daily_adj_prices_as_df - last_year_daily_adj_prices_as_df.shift(1)) / last_year_daily_adj_prices_as_df.shift(1)

    return perc_returns

def get_equally_weighted_returns_across_asset_classes(
                                                      dict_of_asset_classes: dict,
                                                      perc_returns: pd.DataFrame
                                                      ) -> pd.DataFrame:

    list_of_asset_classes = list(set(list(dict_of_asset_classes.values())))

    results_as_list = [
         get_equally_weighted_returns_for_asset_class(
             asset_class=asset_class,
             dict_of_asset_classes=dict_of_asset_classes,
             perc_returns=perc_returns
             )

        for asset_class in list_of_asset_classes
    ]

    results_as_pd = pd.concat(results_as_list, axis=1)
    results_as_pd.columns = list_of_asset_classes

    return results_as_pd


def get_equally_weighted_returns_for_asset_class(
                                        asset_class: str,
                                        dict_of_asset_classes: dict,
                                        perc_returns: pd.DataFrame) -> pd.Series:

    instruments_in_asset_class = [instrument for
                                  instrument, asset_class_for_instrument in
                                  dict_of_asset_classes.items()
                                  if asset_class == asset_class_for_instrument]
    relevant_returns = perc_returns[instruments_in_asset_class]
    ew_index_returns = relevant_returns.mean(axis=1)

    return ew_index_returns

def dict_of_beta_by_instrument(dict_of_asset_classes: dict,
                               perc_returns: pd.DataFrame,
                       equally_weighted_returns_across_asset_classes: pd.DataFrame) -> dict:

    list_of_instruments = list(set(list(dict_of_asset_classes.keys())))
    dict_of_betas = dict([
        (instrument_code,
         beta_for_instrument(instrument_code=instrument_code,
                             perc_returns=perc_returns,
                             dict_of_asset_classes=dict_of_asset_classes,
                             equally_weighted_returns_across_asset_classes=equally_weighted_returns_across_asset_classes))
        for instrument_code in list_of_instruments
    ])

    return dict_of_betas

def beta_for_instrument(instrument_code: str,
                        dict_of_asset_classes: dict,
                        perc_returns: pd.DataFrame,

    equally_weighted_returns_across_asset_classes: pd.DataFrame) -> float:

    asset_class = dict_of_asset_classes[instrument_code]
    perc_returns_for_instrument = perc_returns[instrument_code]
    perc_returns_for_asset_class = equally_weighted_returns_across_asset_classes[asset_class]

    both_returns = pd.concat([perc_returns_for_instrument,
                              perc_returns_for_asset_class], axis=1)
    both_returns.columns = ['y', 'x']
    both_returns = both_returns.dropna()

    reg_result = sm.ols(formula = "y ~ x", data = both_returns).fit()
    beta = reg_result.params.x

    return beta

def dynamic_optimisation_text(data: dataBlob,
                                   strategy_name: str):

    report_config = reportConfig(
        title="Dynamic Optimisation Text",
        function="not_used",
        output="file"
    )

    report_output = []

    #### WE'D ADD REPORT OBJECTS LIKE BODY_TEXT, TABLE HERE

    parsed_report_results = parse_report_results(data,
                                          report_results=report_output)

    output_file_report(parsed_report=parsed_report_results,
                       data=data, report_config=report_config)


if __name__ == '__main__':
    ### Do two seperate reports, one graphical, one text

    data = dataBlob()
    ## interactively get backtest to use
    strategy_name = get_valid_strategy_name_from_user(data)
    dynamic_optimisation_graphical(strategy_name = strategy_name,
                                   data = data)

    dynamic_optimisation_text(strategy_name = strategy_name,
                                   data = data)
