"""
Update spot FX prices using interactive brokers data, dump into mongodb
"""

from syscore.objects import success, failure, data_error

from sysproduction.data.get_data import dataBlob
from sysproduction.data.currency_data import currencyData
from sysproduction.data.broker import dataBroker
from sysproduction.diagnostic.emailing import send_production_mail_msg


def update_fx_prices():
    """
    Update FX prices stored in Arctic (Mongo) with interactive brokers prices (usually going back about a year)

    :return: Nothing
    """

    ## Called as standalone
    with dataBlob(log_name="Update-FX-Prices") as data:
        update_fx_prices_object = updateFxPrices(data)
        update_fx_prices_object.update_fx_prices()

    return success


class updateFxPrices(object):
    ## Called by run_daily_price_updates
    def __init__(self, data):
        self.data = data

    def update_fx_prices(self):
        data = self.data
        update_fx_prices_with_data(data)

def update_fx_prices_with_data(data: dataBlob):
    broker_fx_source = dataBroker(data)
    list_of_codes_all = (
        broker_fx_source.get_list_of_fxcodes()
    )  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFx.csv
    data.log.msg("FX Codes: %s" % str(list_of_codes_all))

    for fx_code in list_of_codes_all:
        data.log.label(fx_code=fx_code)
        update_fx_prices_for_code(fx_code, data)


def update_fx_prices_for_code(fx_code: str, data: dataBlob):
    broker_fx_source = dataBroker(data)
    db_fx_data = currencyData(data)

    new_fx_prices = broker_fx_source.get_fx_prices(
        fx_code)  # returns fxPrices object
    rows_added = db_fx_data.update_fx_prices(
        fx_code, new_fx_prices, check_for_spike=True
    )

    if rows_added is data_error:
        report_fx_data_spike(data, fx_code)

    return success

def report_fx_data_spike(data: dataBlob, fx_code: str):
    msg = (
            "Spike found in prices for %s: need to manually check by running interactive_manual_check_fx_prices" %
            str(fx_code))
    data.log.warn(msg)
    try:
        send_production_mail_msg(
            data, msg, "FX Price Spike %s" %
                       str(fx_code))
    except BaseException:
        data.log.warn("Couldn't send email about price spike")

