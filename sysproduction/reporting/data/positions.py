from sysproduction.data.broker import dataBroker
from sysproduction.data.positions import dataOptimalPositions, diagPositions


def get_optimal_positions(data):
    data_optimal = dataOptimalPositions(data)
    opt_positions = data_optimal.get_pd_of_position_breaks()

    return opt_positions


def get_my_positions(data):
    data_broker = dataBroker(data)
    my_positions = data_broker.get_db_contract_positions_with_IB_expiries().as_pd_df()
    my_positions = my_positions.sort_values("instrument_code")

    return my_positions


def get_broker_positions(data):
    data_broker = dataBroker(data)
    broker_positions = data_broker.get_all_current_contract_positions().as_pd_df()
    broker_positions = broker_positions.sort_values("instrument_code")
    return broker_positions


def get_position_breaks(data):

    data_optimal = dataOptimalPositions(data)
    breaks_str0 = "Breaks Optimal vs actual %s" % str(
        data_optimal.get_list_of_optimal_position_breaks()
    )

    diag_positions = diagPositions(data)
    breaks_str1 = "Breaks Instrument vs Contract %s" % str(
        diag_positions.get_list_of_breaks_between_contract_and_strategy_positions()
    )

    data_broker = dataBroker(data)
    breaks_str2 = "Breaks Broker vs Contract %s" % str(
        data_broker.get_list_of_breaks_between_broker_and_db_contract_positions()
    )

    return breaks_str0 + "\n " + breaks_str1 + "\n " + breaks_str2
