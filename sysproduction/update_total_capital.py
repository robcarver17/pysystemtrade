
from syscore.objects import success, failure

from sysproduction.data.get_data import dataBlob
from sysproduction.data.capital import dataCapital
from sysproduction.data.broker import dataBroker

def update_total_capital():
    """
    Do a daily update of accounting information

    Get the total account value from IB, and calculate the p&l since we last ran

    Needs to know about any withdrawals.

    Does spike checking: large changes in account value are checked before writing

    If your strategy has very high risk you may wish to do this more frequently than daily

    This is incorporate into the 'run' process, run_capital_update

    :return: Nothing
    """
    with dataBlob(log_name="Update-Total-Capital") as data:
        total_capital = totalCapitalUpdate(data)
        total_capital.update_total_capital()

    return success


class totalCapitalUpdate(object):
    def __init__(self, data):
        self.data = data

    def update_total_capital(self):
        data = self.data
        capital_data = dataCapital(data)
        broker_data = dataBroker(data)

        log = data.log

        # This assumes that each account only reports either in one currency or
        # for each currency, i.e. no double counting
        total_account_value_in_base_currency = broker_data.get_total_capital_value_in_base_currency()
        log.msg(
            "Broker account value is %f" %
            total_account_value_in_base_currency)

        # Update total capital
        try:
            new_capital = capital_data.get_total_capital_with_new_broker_account_value(
                total_account_value_in_base_currency)
        except Exception as e:
            # Problem, most likely spike
            log.critical(
                "Error %s whilst updating total capital; you may have to use update_capital_manual script or function" %
                e)
            return failure

        log.msg("New capital is %f" % new_capital)
