from flask import Flask, render_template, _app_ctx_stack, g
from werkzeug.local import LocalProxy

from sysdata.data_blob import dataBlob

from sysproduction.data.prices import diagPrices
from sysproduction.reporting import roll_report
from sysproduction.data.broker import dataBroker
from sysproduction.data.capital import dataCapital
from sysproduction.data.positions import diagPositions, dataOptimalPositions

from pprint import pprint

import asyncio

app = Flask(__name__)


def get_data():
    if not hasattr(g, "data"):
        g.data = dataBlob(log_name="dashboard")
    return g.data


@app.teardown_request
def cleanup_data(exception):
    if hasattr(g, "data"):
        g.data.close()
    del g.data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/processes")
def processes():
    data = get_data()
    data_control = dataControlProcess(data)
    control_process_data = data_control.db_control_process_data
    names = control_process_data.get_list_of_process_names()
    pprint(names)
    running_modes = {}
    for name in names:
        running_modes[name] = control_process_data.get_control_for_process_name(
            name
        ).running_mode_str
    processes = data_control.get_dict_of_control_processes()
    return {"running_modes": running_modes}


@app.route("/capital")
def capital():
    data = get_data()
    asyncio.set_event_loop(asyncio.new_event_loop())
    capital_data = dataCapital(data)
    print(f"data capital: {id(capital_data)}")
    print(f"data blob: {id(data)}")

    capital_series = capital_data.get_series_of_all_global_capital()
    now = capital_series.iloc[-1]["Actual"]
    yesterday = capital_series.last("1D").iloc[0]["Actual"]
    return {"now": now, "yesterday": yesterday}


@app.route("/reconcile")
def reconcile():
    data = get_data()
    diag_positions = diagPositions(data)
    data_optimal = dataOptimalPositions(data)
    optimal_positions = data_optimal.get_pd_of_position_breaks().to_dict()
    strategies = {}
    for instrument in optimal_positions["breaks"].keys():
        strategies[instrument] = {
            "break": optimal_positions["breaks"][instrument],
            "optimal": str(optimal_positions["optimal"][instrument]),
            "current": optimal_positions["current"][instrument],
        }

    asyncio.set_event_loop(asyncio.new_event_loop())
    data_broker = dataBroker(data)
    print(f"data broker: {id(data_broker)}")
    print(f"data blob: {id(data)}")
    db_contract_pos = (
        data_broker.get_db_contract_positions_with_IB_expiries().as_pd_df().to_dict()
    )
    positions = {}
    for idx in db_contract_pos["instrument_code"].keys():
        code = db_contract_pos["instrument_code"][idx]
        contract_date = db_contract_pos["contract_date"][idx]
        position = db_contract_pos["position"][idx]
        positions[code + "-" + contract_date] = {
            "code": code,
            "contract_date": contract_date,
            "db_position": position,
        }
    ib_contract_pos = (
        data_broker.get_all_current_contract_positions().as_pd_df().to_dict()
    )
    for idx in ib_contract_pos["instrument_code"].keys():
        code = ib_contract_pos["instrument_code"][idx]
        contract_date = ib_contract_pos["contract_date"][idx]
        position = ib_contract_pos["position"][idx]
        positions[code + "-" + contract_date]["ib_position"] = position

    db_breaks = (
        diag_positions.get_list_of_breaks_between_contract_and_strategy_positions()
    )
    ib_breaks = (
        data_broker.get_list_of_breaks_between_broker_and_db_contract_positions()
    )
    return {
        "strategy": strategies,
        "positions": positions,
        "db_breaks": db_breaks,
        "ib_breaks": ib_breaks,
    }


@app.route("/rolls")
def rolls():
    data = get_data()
    diag_prices = diagPrices(data)

    all_instruments = diag_prices.get_list_of_instruments_in_multiple_prices()
    report = {}
    for instrument in all_instruments:
        report[instrument] = roll_report.get_roll_data_for_instrument(instrument, data)
    return report


if __name__ == "__main__":
    # strategy()
    app.run(
        threaded=True, use_debugger=False, use_reloader=False, passthrough_errors=True
    )
