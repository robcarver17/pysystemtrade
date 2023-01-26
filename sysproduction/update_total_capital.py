from syscore.constants import success, failure

from sysdata.data_blob import dataBlob
from sysproduction.data.capital import dataCapital, dataMargin
from sysproduction.data.broker import dataBroker


def update_total_capital():
    """
    Do an update of accounting information

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
    def __init__(self, data: dataBlob):
        self.data = data

    def update_total_capital(self):
        self.update_capital()
        self.update_margin()

    def update_margin(self):
        data = self.data
        margin_data = dataMargin(data)
        broker_data = dataBroker(data)

        log = data.log

        margin_in_base_currency = broker_data.get_margin_used_in_base_currency()
        log.msg("Broker margin value is %f" % margin_in_base_currency)

        # Update total capital
        margin_data.add_total_margin_entry(margin_in_base_currency)
        margin_series = margin_data.get_series_of_total_margin()

        log.msg("Recent margin\n %s" % str(margin_series.tail(10)))

    def update_capital(self):
        data = self.data
        capital_data = dataCapital(data)
        broker_data = dataBroker(data)

        log = data.log

        # This assumes that each account only reports either in one currency or
        # for each currency, i.e. no double counting
        total_account_value_in_base_currency = (
            broker_data.get_total_capital_value_in_base_currency()
        )
        log.msg("Broker account value is %f" % total_account_value_in_base_currency)

        # Update total capital
        try:
            new_capital = capital_data.update_and_return_total_capital_with_new_broker_account_value(
                total_account_value_in_base_currency
            )
        except Exception as e:
            # Problem, most likely spike OR
            log.critical(
                "Error %s whilst updating total capital; you may have to use update_capital_manual script or function OR IF YOU HAVEN'T DONE SO ALREADY YOU MUST RUN sysdata/production/TEMP_capital_transfer.py from the command line to transfer your old capital"
                % e
            )
            return failure

        log.msg("New capital is %f" % new_capital)


if __name__ == "__main__":
    update_total_capital()
