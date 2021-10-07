import pandas as pd

from syscore.objects import header, table, body_text
from sysdata.data_blob import dataBlob
from sysobjects.production.backtest_storage import interactiveBacktest
from sysproduction.strategy_code.report_system_classic import report_system_classic
from sysproduction.data.positions import dataOptimalPositions

def report_system_dynamic(data: dataBlob, backtest: interactiveBacktest):
    format_output = report_system_classic(data=data,
                                          backtest=backtest)

    optimal_positions_df = get_optimal_positions_table_as_df(data=data,
                                                          strategy_name =
                                                          backtest.strategy_name)
    optimal_positions_table = table("Optimal positions", optimal_positions_df)
    format_output.append(optimal_positions_table)

    return format_output

def get_optimal_positions_table_as_df(data: dataBlob,
                                        strategy_name: str) -> pd.DataFrame:

    data_optimal_positions = dataOptimalPositions(data)
    list_of_instruments = data_optimal_positions.get_list_of_instruments_for_strategy_with_optimal_position(
        strategy_name)

    data_optimal_positions.get_current_optimal_position_for_instrument_strategy()