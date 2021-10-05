from flask import Flask, render_template

from sysdata.data_blob import dataBlob

from sysproduction.data.prices import diagPrices
from sysproduction.reporting import roll_report
from sysproduction.data.capital import dataCapital

from pprint import pprint

app = Flask(__name__)

data = dataBlob(log_name="dashboard")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/capital")
def capital():
    capital_data = dataCapital(data)
    capital_series = capital_data.get_series_of_all_global_capital()
    now = capital_series.iloc[-1]['Actual']
    yesterday = capital_series.last('1D').iloc[0]['Actual']
    return {'now': now, 'yesterday': yesterday}

@app.route("/traffic_lights")
def traffic_lights():
    traffic_lights = {
        "stack": "green",
        "gateway": "red",
        "prices": "orange",
        # "capital": 123456,
        "breaks": "green",
    }
    return traffic_lights


@app.route("/rolls")
def rolls():
    # If we have a dictionary, Flask will automatically json-ify it
    diag_prices = diagPrices(data)

    all_instruments = diag_prices.get_list_of_instruments_in_multiple_prices()
    report = {}
    for instrument in all_instruments:
        report[instrument] = roll_report.get_roll_data_for_instrument(instrument, data)
    return report


if __name__ == "__main__":
    app.run(use_debugger=False, use_reloader=False, passthrough_errors=True)
