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
        log.debug("Broker margin value is %f" % margin_in_base_currency)

        # Update total capital
        margin_data.add_total_margin_entry(margin_in_base_currency)
        margin_series = margin_data.get_series_of_total_margin()

        log.debug("Recent margin\n%s" % str(margin_series.tail(10)))

    def update_capital(self):
        data = self.data
        broker_data = dataBroker(data)

        # This assumes that each account only reports either in one currency or
        # for each currency, i.e. no double counting
        total_account_value_in_base_currency = (
            broker_data.get_total_capital_value_in_base_currency()
        )
        data.log.debug(
            "Broker account value is %f" % total_account_value_in_base_currency
        )

        _update_capital_with_broker_account_value(
            data=data,
            total_account_value_in_base_currency=total_account_value_in_base_currency,
        )


def _update_capital_with_broker_account_value(
    data: dataBlob, total_account_value_in_base_currency: float
):
    log = data.log

    capital_data = dataCapital(data)

    total_capital_data_exists = capital_data.check_for_total_capital_data()
    if total_capital_data_exists:
        _update_capital_with_broker_account_value_if_capital_data_exists(
            data=data,
            total_account_value_in_base_currency=total_account_value_in_base_currency,
        )
    else:
        log.critical("No total capital - setting up with current broker account value")
        capital_data.create_initial_capital(
            broker_account_value=total_account_value_in_base_currency,
            are_you_really_sure=True,
        )


def _update_capital_with_broker_account_value_if_capital_data_exists(
    data: dataBlob, total_account_value_in_base_currency: float
):
    log = data.log

    capital_data = dataCapital(data)

    # Update total capital
    try:
        new_capital = (
            capital_data.update_and_return_total_capital_with_new_broker_account_value(
                total_account_value_in_base_currency
            )
        )
    except Exception as e:
        # Problem, most likely spike
        log.critical("Error %s whilst updating total capital" % e)
        return failure

    log.debug("New capital is %f" % new_capital)


if __name__ == "__main__":
    update_total_capital()
