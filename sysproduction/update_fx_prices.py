"""
Update spot FX prices using interactive brokers data, dump into mongodb
"""

from syscore.objects import success, failure, data_error
from syslogdiag.emailing import send_mail_msg

from sysproduction.data.get_data import dataBlob
from sysproduction.data.currency_data import currencyData
from sysproduction.data.broker import dataBroker

def update_fx_prices():
    """
    Update FX prices stored in Arctic (Mongo) with interactive brokers prices (usually going back about a year)

    :return: Nothing
    """

    with dataBlob(log_name="Update-FX-Prices") as data:
        update_fx_prices_object = updateFxPrices(data)
        update_fx_prices_object.update_fx_prices()

    return success

class updateFxPrices(object):
    def __init__(self, data):
        self.data = data

    def update_fx_prices(self, method_name):
        data = self.data
        data.log = data.log.setup(method_name = method_name)

        log = data.log
        broker_fx_source = dataBroker(data)
        list_of_codes_all = broker_fx_source.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFx.csv
        log.msg("FX Codes: %s" % str(list_of_codes_all))

        for fx_code in list_of_codes_all:
            try:
                log.label(currency_code = fx_code)
                update_fx_prices_for_code(fx_code, data)
            except Exception as e:
                log.warn("Something went wrong with FX update %s" % e)

        return None

def update_fx_prices_for_code(fx_code, data):
    broker_fx_source = dataBroker(data)
    db_fx_data = currencyData(data)

    new_fx_prices = broker_fx_source.get_fx_prices(fx_code) # returns fxPrices object
    rows_added = db_fx_data.update_fx_prices(fx_code, new_fx_prices, check_for_spike=True)

    if rows_added is data_error:
        msg = "Spike found in prices for %s: need to manually check by running interactive_manual_check_fx_prices" % str(fx_code)
        data.log.warn(msg)
        try:
            send_mail_msg(msg, "FX Price Spike")
        except:
            data.log.warn("Couldn't send email about price spike")

    return success

