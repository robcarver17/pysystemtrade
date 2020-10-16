import pandas as pd
import numpy as np
import datetime

from collections import namedtuple

from syscore.objects import header, table, body_text
from syscore.dateutils import ROOT_BDAYS_INYEAR
from sysproduction.diagnostic.backtest_state import from_marker_to_datetime
from sysproduction.data.positions import diagPositions


def report_system_classic(data, data_backtest):
    """

    :param strategy_name: str
    :param data: dataBlob
    :param data_backtest: dataBacktest object populated with a specific backtest
    :return: list of report format type objects
    """

    strategy_name = data_backtest.strategy_name

    format_output = []
    report_header = header(
        "Strategy report for %s backtest timestamp %s produced at %s" %
        (strategy_name, data_backtest.timestamp, str(
            datetime.datetime.now())))
    format_output.append(report_header)

    unweighted_forecasts_df = get_forecast_matrix(
        data_backtest,
        stage_name="forecastScaleCap",
        method_name="get_capped_forecast")
    unweighted_forecasts_df_rounded = unweighted_forecasts_df.round(1)
    unweighted_forecasts_table = table(
        "Unweighted forecasts", unweighted_forecasts_df_rounded
    )
    format_output.append(unweighted_forecasts_table)

    # Forecast weights
    forecast_weights_df = get_forecast_matrix_over_code(
        data_backtest, stage_name="combForecast", method_name="get_forecast_weights")
    forecast_weights_df_as_perc = forecast_weights_df * 100
    forecast_weights_df_as_perc_rounded = forecast_weights_df_as_perc.round(1)
    forecast_weights_table = table(
        "Forecast weights", forecast_weights_df_as_perc_rounded
    )
    format_output.append(forecast_weights_table)

    # Weighted forecast
    weighted_forecasts_df = forecast_weights_df * unweighted_forecasts_df
    weighted_forecast_rounded = weighted_forecasts_df.round(1)
    weighted_forecast_table = table(
        "Weighted forecasts",
        weighted_forecast_rounded)
    format_output.append(weighted_forecast_table)

    # Cash target
    cash_target_dict = data_backtest.system.positionSize.get_daily_cash_vol_target()
    cash_target_text = body_text(
        "\nVol target calculation %s\n" %
        cash_target_dict)

    format_output.append(cash_target_text)

    # Vol calc
    vol_calc_df = get_stage_breakdown_over_codes(
        data_backtest,
        method_list=[
            daily_returns_vol,
            daily_denom_price,
            rawdata_daily_perc_vol],
    )
    vol_calc_df["annual % vol"] = vol_calc_df["Daily % vol"] * \
        ROOT_BDAYS_INYEAR
    vol_calc_df_rounded = vol_calc_df.round(4)
    vol_calc_table = table("Vol calculation", vol_calc_df_rounded)
    format_output.append(vol_calc_table)

    # Subsystem position table
    subystem_positions_df = get_stage_breakdown_over_codes(
        data_backtest,
        method_list=[
            get_block_value,
            get_price_volatility,
            get_instrument_ccy_vol,
            get_fx_rate,
            get_instrument_value_vol,
            get_daily_cash_vol_target,
            get_vol_scalar,
            get_combined_forecast,
            get_subsystem_position,
        ],
    )
    subystem_positions_df_rounded = subystem_positions_df.round(2)
    subystem_positions_table = table(
        "Subsystem position", subystem_positions_df_rounded
    )
    format_output.append(subystem_positions_table)

    # Portfolio position table: ss position, instr weight, IDM, position
    # required
    portfolio_positions_df = get_stage_breakdown_over_codes(
        data_backtest,
        method_list=[
            get_subsystem_position,
            get_instrument_weights,
            get_idm,
            get_required_portfolio_position,
        ],
    )
    portfolio_positions_df_rounded = portfolio_positions_df.round(3)
    portfolio_positions_table = table(
        "Portfolio positions", portfolio_positions_df_rounded
    )

    format_output.append(portfolio_positions_table)

    # position diags
    position_diags_df = calc_position_diags(portfolio_positions_df, subystem_positions_df)

    position_diags_df_rounded = position_diags_df.round(2)
    position_diags_table = table("Position diags", position_diags_df_rounded)

    format_output.append(position_diags_table)

    # Position vs buffer table: position required, buffers, actual position
    versus_buffers_df = get_stage_breakdown_over_codes(
        data_backtest,
        method_list=[
            get_required_portfolio_position,
            get_lower_buffer,
            get_upper_buffer,
        ],
    )

    instrument_code_list = versus_buffers_df.index
    timestamp_positions = get_position_at_timestamp_df_for_instrument_code_list(
        data_backtest, data, instrument_code_list)
    current_positions = get_current_position_df_for_instrument_code_list(
        data_backtest, data, instrument_code_list
    )
    versus_buffers_and_positions_df = pd.concat(
        [versus_buffers_df, timestamp_positions, current_positions], axis=1
    )
    versus_buffers_and_positions_df_rounded = versus_buffers_and_positions_df.round(
        1)
    versus_buffers_and_positions_table = table(
        "Positions vs buffers", versus_buffers_and_positions_df_rounded
    )

    format_output.append(versus_buffers_and_positions_table)

    format_output.append(body_text("End of report for %s" % strategy_name))

    return format_output


def get_forecast_matrix(
    data_backtest, stage_name="combForecast", method_name="get_capped_forecast"
):
    instrument_codes = data_backtest.system.get_instrument_list()
    trading_rules = data_backtest.system.rules.trading_rules()
    trading_rule_names = list(trading_rules.keys())

    datetime_cutoff = from_marker_to_datetime(data_backtest.timestamp)

    value_dict = {}
    for rule_name in trading_rule_names:
        value_dict[rule_name] = []
        for instrument_code in instrument_codes:
            stage = getattr(data_backtest.system, stage_name)
            method = getattr(stage, method_name)
            value = method(instrument_code, rule_name).ffill()[
                :datetime_cutoff][-1]
            value_dict[rule_name].append(value)

    value_df = pd.DataFrame(value_dict, index=instrument_codes)

    return value_df


def get_forecast_matrix_over_code(
        data_backtest,
        stage_name="combForecast",
        method_name="get_forecast_weights"):
    instrument_codes = data_backtest.system.get_instrument_list()
    trading_rules = data_backtest.system.rules.trading_rules()
    trading_rule_names = list(trading_rules.keys())

    datetime_cutoff = from_marker_to_datetime(data_backtest.timestamp)

    value_dict = {}
    for instrument_code in instrument_codes:
        stage = getattr(data_backtest.system, stage_name)
        method = getattr(stage, method_name)
        value_row = method(instrument_code).ffill()[:datetime_cutoff].iloc[-1]
        values_by_rule = [
            value_row.get(
                rule_name,
                np.nan) for rule_name in trading_rule_names]
        value_dict[instrument_code] = values_by_rule

    value_df = pd.DataFrame(value_dict, index=trading_rule_names)
    value_df = value_df.transpose()

    return value_df


# ss position, instr weight, IDM, position required

configForMethod = namedtuple(
    "ConfigForMethod",
    [
        "stage_name",
        "method_name",
        "name",
        "global_bool",
        "requires_code_bool",
        "col_selector",
        "scalar_dict_bool",
        "scalar_dict_entry",
    ],
)

daily_returns_vol = configForMethod(
    "rawdata",
    "daily_returns_volatility",
    "Daily return vol",
    False,
    True,
    None,
    False,
    False,
)

daily_denom_price = configForMethod(
    "rawdata",
    "daily_denominator_price",
    "Price",
    False,
    True,
    None,
    False,
    False)

rawdata_daily_perc_vol = configForMethod(
    "rawdata",
    "get_daily_percentage_volatility",
    "Daily % vol",
    False,
    True,
    None,
    False,
    False,
)

get_combined_forecast = configForMethod(
    "positionSize",
    "get_combined_forecast",
    "Combined forecast",
    False,
    True,
    None,
    False,
    None,
)

get_block_value = configForMethod(
    "positionSize",
    "get_block_value",
    "Block_Value",
    False,
    True,
    None,
    False,
    None)

get_price_volatility = configForMethod(
    "positionSize",
    "get_price_volatility",
    "Daily price % vol",
    False,
    True,
    None,
    False,
    None,
)

get_fx_rate = configForMethod(
    "positionSize", "get_fx_rate", "FX", False, True, None, False, None
)

get_instrument_ccy_vol = configForMethod(
    "positionSize",
    "get_instrument_currency_vol",
    "ICV",
    False,
    True,
    None,
    False,
    None)

get_instrument_value_vol = configForMethod(
    "positionSize",
    "get_instrument_value_vol",
    "IVV",
    False,
    True,
    None,
    False,
    None)

get_daily_cash_vol_target = configForMethod(
    "positionSize",
    "get_daily_cash_vol_target",
    "Daily Cash Vol Tgt",
    False,
    False,
    None,
    True,
    "daily_cash_vol_target",
)

get_vol_scalar = configForMethod(
    "positionSize",
    "get_volatility_scalar",
    "Vol Scalar",
    False,
    True,
    None,
    False,
    None,
)

get_subsystem_position = configForMethod(
    "positionSize",
    "get_subsystem_position",
    "subsystem_position",
    False,
    True,
    None,
    False,
    None,
)

get_instrument_weights = configForMethod(
    "portfolio",
    "get_instrument_weights",
    "instr weight",
    False,
    False,
    None,
    False,
    None,
)

get_idm = configForMethod(
    "portfolio",
    "get_instrument_diversification_multiplier",
    "IDM",
    True,
    False,
    None,
    False,
    None,
)

get_required_portfolio_position = configForMethod(
    "portfolio",
    "get_notional_position",
    "Notional position",
    False,
    True,
    None,
    False,
    None,
)

get_lower_buffer = configForMethod(
    "portfolio",
    "get_actual_buffers_for_position",
    "Lower buffer",
    False,
    True,
    "bot_pos",
    False,
    None,
)

get_upper_buffer = configForMethod(
    "portfolio",
    "get_actual_buffers_for_position",
    "Upper buffer",
    False,
    True,
    "top_pos",
    False,
    None,
)


def get_stage_breakdown_over_codes(data_backtest, method_list=[]):

    value_dict = {}
    for method_config in method_list:
        value_dict[method_config.name] = get_list_of_values_by_instrument_for_config(
            data_backtest, method_config)

    instrument_codes = data_backtest.system.get_instrument_list()
    value_df = pd.DataFrame(value_dict, index=instrument_codes)

    return value_df


def get_list_of_values_by_instrument_for_config(
        data_backtest, config_for_method):
    instrument_codes = data_backtest.system.get_instrument_list()
    datetime_cutoff = from_marker_to_datetime(data_backtest.timestamp)

    stage = getattr(data_backtest.system, config_for_method.stage_name)
    method = getattr(stage, config_for_method.method_name)

    if config_for_method.global_bool:
        # Same value regardless of instrument
        value = method().ffill()[:datetime_cutoff].iloc[-1]
        if config_for_method.col_selector is not None:
            value = value[config_for_method.col_selector]
        value_list = [value] * len(instrument_codes)

        return value_list

    if config_for_method.requires_code_bool:
        # call for each code
        if config_for_method.col_selector is not None:
            value_list = [
                method(instrument_code)
                .ffill()[:datetime_cutoff]
                .iloc[-1][config_for_method.col_selector]
                for instrument_code in instrument_codes
            ]
        else:
            value_list = [
                method(instrument_code).ffill()[:datetime_cutoff].iloc[-1]
                for instrument_code in instrument_codes
            ]

        return value_list

    if config_for_method.scalar_dict_bool:
        value = method()[config_for_method.scalar_dict_entry]
        value_list = [value] * len(instrument_codes)

        return value_list

    # get dataframe

    value_row = method().ffill()[:datetime_cutoff].iloc[-1]
    value_list = [value_row.get(instrument_code, np.nan)
                  for instrument_code in instrument_codes]

    return value_list


def get_current_position_df_for_instrument_code_list(
    data_backtest, data, instrument_code_list
):
    position_list = [
        get_current_position_for_instrument_code(data_backtest, data, instrument_code)
        for instrument_code in instrument_code_list
    ]
    position_df = pd.DataFrame(
        position_list, index=instrument_code_list, columns=["Current position"]
    )
    return position_df


def get_position_at_timestamp_df_for_instrument_code_list(
    data_backtest, data, instrument_code_list
):
    position_list = [
        get_position_for_instrument_code_at_timestamp(
            data_backtest, data, instrument_code
        )
        for instrument_code in instrument_code_list
    ]
    position_df = pd.DataFrame(
        position_list,
        index=instrument_code_list,
        columns=["Position at timestamp"])
    return position_df


def get_position_for_instrument_code_at_timestamp(
        data_backtest, data, instrument_code):
    diag_positions = diagPositions(data)
    positions_over_time = diag_positions.get_position_df_for_strategy_and_instrument(
        data_backtest.strategy_name, instrument_code)
    datetime_cutoff = from_marker_to_datetime(data_backtest.timestamp)

    position_at_backtest_state = (
        positions_over_time[:datetime_cutoff].ffill().values[-1]
    )

    return position_at_backtest_state


def get_current_position_for_instrument_code(
        data_backtest, data, instrument_code):
    diag_positions = diagPositions(data)
    current_position = diag_positions.get_position_for_strategy_and_instrument(
        data_backtest.strategy_name, instrument_code
    )

    return current_position

def calc_position_diags(portfolio_positions_df, subystem_positions_df):
    idm = portfolio_positions_df.IDM
    instr_weight = portfolio_positions_df['instr weight']
    vol_scalar = subystem_positions_df['Vol Scalar']

    average_position = idm * instr_weight * vol_scalar

    return average_position