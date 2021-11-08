from flask import Flask, g, render_template, request
from werkzeug.local import LocalProxy

import sysproduction.reporting.api
from syscore.objects import missing_data
from syscore.genutils import str2Bool

from syscontrol.list_running_pids import describe_trading_server_login_data

from sysdata.config.control_config import get_control_config

from sysdata.data_blob import dataBlob

from sysobjects.production.roll_state import (
    RollState,
)


from sysproduction.data.prices import diagPrices
from sysproduction.reporting import (
    costs_report,
    pandl_report,
    risk_report,
    roll_report,
    trades_report,
    status_reporting,
)
from sysproduction.reporting.api import reportingApi

from sysproduction.data.broker import dataBroker
from sysproduction.data.control_process import dataControlProcess
from sysproduction.data.capital import dataCapital
from sysproduction.data.positions import diagPositions, dataOptimalPositions
from sysproduction.interactive_update_roll_status import (
    modify_roll_state,
    setup_roll_data_with_state_reporting,
)
from sysproduction.reporting.data.rolls import rollingAdjustedAndMultiplePrices

import syscore.dateutils

import asyncio
import datetime
import json
import pandas as pd

app = Flask(__name__)


def get_data():
    if not hasattr(g, "data"):
        g.data = dataBlob(log_name="dashboard")
    return g.data


data = LocalProxy(get_data)


def get_reporting_api():
    return reportingApi(data)


reporting_api = LocalProxy(get_reporting_api)


@app.teardown_appcontext
def cleanup_data(exception):
    if hasattr(g, "data"):
        g.data.close()
        del g.data


def dict_of_df_to_dict(d, orient):
    return {
        k: json.loads(v.to_json(orient=orient, date_format="iso"))
        if isinstance(v, pd.DataFrame)
        else v
        for k, v in d.items()
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/capital")
def capital():
    capital_data = dataCapital(data)
    capital_series = capital_data.get_series_of_all_global_capital()
    now = capital_series.iloc[-1]["Actual"]
    yesterday = capital_series.last("1D").iloc[0]["Actual"]
    return {"now": now, "yesterday": yesterday}


@app.route("/costs")
def costs():
    end = datetime.datetime.now()
    start = syscore.dateutils.n_days_ago(250)
    costs = costs_report.get_costs_report_data(data, start, end)
    df_costs = costs["combined_df_costs"].to_dict(orient="index")
    df_costs = {k: {kk: str(vv) for kk, vv in v.items()} for k, v in df_costs.items()}
    costs["combined_df_costs"] = df_costs
    costs["table_of_SR_costs"] = costs["table_of_SR_costs"].to_dict(orient="index")
    return costs


@app.route("/forex")
def forex():
    asyncio.set_event_loop(asyncio.new_event_loop())
    data_broker = dataBroker(data)
    return data_broker.broker_fx_balances()


@app.route("/liquidity")
def liquidity():
    liquidity_data = reporting_api.liquidity_data().to_dict(orient="index")
    return liquidity_data


@app.route("/pandl")
def pandl():
    pandl_data = {}
    pandl_data[
        "pandl_for_instruments_across_strategies"
    ] = reporting_api.table_pandl_for_instruments_across_strategies().Body.to_dict(
        orient="records"
    )
    pandl_data[
        "strategies"
    ] = reporting_api.table_strategy_pandl_and_residual().Body.to_dict(orient="records")
    pandl_data["sector_pandl"] = reporting_api.table_sector_pandl().Body.to_dict(
        orient="records"
    )

    return pandl_data


@app.route("/processes")
def processes():
    asyncio.set_event_loop(asyncio.new_event_loop())

    data_control = dataControlProcess(data)
    data_control.check_if_pid_running_and_if_not_finish_all_processes()

    retval = {
        "config": reporting_api.table_of_control_config_list_for_all_processes().Body,
        "control": reporting_api.table_of_control_status_list_for_all_processes().Body,
        "process": reporting_api.table_of_process_status_list_for_all_processes().Body,
        # "method_data": reporting_api.table_of_control_data_list_for_all_methods().Body,
        "price": reporting_api.table_of_last_price_updates().Body,
    }

    retval = dict_of_df_to_dict(retval, orient="index")

    allprocess = {}
    for k in retval["config"].keys():
        allprocess[k] = {
            **retval["config"].get(k, {}),
            **retval["control"].get(k, {}),
            **retval["process"].get(k, {}),
        }
    retval["process"] = allprocess
    retval.pop("control")
    retval["config"] = {
        "monitor": describe_trading_server_login_data(),
        "mongo": f"{data.mongo_db.host}:{data.mongo_db.port} - {data.mongo_db.database_name}",
        "ib": f"{data.ib_conn._ib_connection_config['ipaddress']}:{data.ib_conn._ib_connection_config['port']}",
    }

    return retval


@app.route("/reconcile")
def reconcile():
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

    positions = {}

    db_breaks = (
        diag_positions.get_list_of_breaks_between_contract_and_strategy_positions()
    )
    ib_breaks = []
    gateway_ok = True
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
        data_broker = dataBroker(data)
        db_contract_pos = (
            data_broker.get_db_contract_positions_with_IB_expiries()
            .as_pd_df()
            .to_dict()
        )
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
        ib_breaks = (
            data_broker.get_list_of_breaks_between_broker_and_db_contract_positions()
        )
    except:
        # IB gateway connection failed
        gateway_ok = False
    return {
        "strategy": strategies,
        "positions": positions,
        "db_breaks": db_breaks,
        "ib_breaks": ib_breaks,
        "gateway_ok": gateway_ok,
    }


@app.route("/rolls")
def rolls():
    rolls = reporting_api.table_of_roll_data().Body
    report = rolls.to_dict(orient="index")

    for instrument in rolls.index:
        allowable = setup_roll_data_with_state_reporting(data, instrument)
        report[instrument]["allowable"] = allowable.allowable_roll_states_as_list_of_str

    return report


@app.route("/rolls", methods=["POST"])
def rolls_post():
    instrument = request.form["instrument"]
    new_state = RollState[request.form["state"]]

    if new_state == RollState.Roll_Adjusted and request.form["confirmed"] != "true":
        # Send back the adjusted prices for checking
        number_to_return = 6
        try:
            rolling = rollingAdjustedAndMultiplePrices(data, instrument)
            current_multiple = {
                str(k): v
                for k, v in rolling.current_multiple_prices.tail(number_to_return)
                .to_dict(orient="index")
                .items()
            }
            # We need to convert values to strings because there are
            # sometimes NaNs which are not valid json
            new_multiple = {
                str(k): {kk: str(vv) for kk, vv in v.items()}
                for k, v in rolling.updated_multiple_prices.tail(number_to_return + 1)
                .to_dict(orient="index")
                .items()
            }
            current_adjusted = {
                str(k): round(v, 2)
                for k, v in rolling.current_adjusted_prices.tail(number_to_return)
                .to_dict()
                .items()
            }
            new_adjusted = {
                str(k): round(v, 2)
                for k, v in rolling.new_adjusted_prices.tail(number_to_return + 1)
                .to_dict()
                .items()
            }
            single = {
                k: {"current": current_adjusted[k], "new": new_adjusted[k]}
                for k in current_adjusted.keys()
            }
            multiple = {
                k: {"current": current_multiple[k], "new": new_multiple[k]}
                for k in current_adjusted.keys()
            }
            new_date = list(new_adjusted.keys())[-1]
            single[new_date] = {"new": new_adjusted[new_date]}
            multiple[new_date] = {"new": new_multiple[new_date]}
            prices = {"single": single, "multiple": multiple}
            return prices
        except:
            # Cannot roll for some reason
            return {}

    roll_data = setup_roll_data_with_state_reporting(data, instrument)
    modify_roll_state(
        data, instrument, roll_data.original_roll_status, new_state, False
    )
    roll_data = setup_roll_data_with_state_reporting(data, instrument)
    return {
        "new_state": request.form["state"],
        "allowable": roll_data.allowable_roll_states_as_list_of_str,
    }


@app.route("/risk")
def risk():
    risk_data = risk_report.calculate_risk_report_data(data)
    risk_data["corr_data"] = risk_data["corr_data"].as_pd()
    risk_data = dict_of_df_to_dict(risk_data, "index")
    return risk_data


@app.route("/trades")
def trades():
    end = datetime.datetime.now()
    start = syscore.dateutils.n_days_ago(1)
    return_data = {}
    trades_data = dict_of_df_to_dict(
        trades_report.get_trades_report_data(data, start, end), "index"
    )
    return_data["overview"] = {
        k: {kk: str(vv) for kk, vv in v.items()}
        for k, v in trades_data["overview"].items()
    }
    return_data["delays"] = {
        k: {kk: str(vv) for kk, vv in v.items()}
        for k, v in trades_data["delays"].items()
    }
    return_data["raw_slippage"] = {
        k: {kk: str(vv) for kk, vv in v.items()}
        for k, v in trades_data["raw_slippage"].items()
    }
    return_data["vol_slippage"] = {
        k: {kk: str(vv) for kk, vv in v.items()}
        for k, v in trades_data["vol_slippage"].items()
    }
    return_data["cash_slippage"] = {
        k: {kk: str(vv) for kk, vv in v.items()}
        for k, v in trades_data["cash_slippage"].items()
    }

    return return_data


@app.route("/strategy")
def strategy():
    return {}


def visible_on_lan() -> bool:
    config = get_control_config()
    visible = config.get_element_or_missing_data("dashboard_visible_on_lan")
    if visible is missing_data:
        return False

    visible = str2Bool(visible)

    return visible


if __name__ == "__main__":
    visible = visible_on_lan()
    if visible:
        data = dataBlob()
        data.log.warn(
            "Starting dashboard with web page visible to all - security implications!!!!"
        )
        app.run(
            threaded=True,
            use_debugger=False,
            use_reloader=False,
            passthrough_errors=True,
            host="0.0.0.0",
        )

    else:
        app.run(
            threaded=True,
            use_debugger=False,
            use_reloader=False,
            passthrough_errors=True,
        )
