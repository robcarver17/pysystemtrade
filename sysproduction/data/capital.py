from syscore.objects import missing_data, arg_not_supplied

from sysdata.production.capital import totalCapitalCalculationData
from sysdata.mongodb.mongo_capital import mongoCapitalData
from sysdata.private_config import get_private_then_default_key_value

from sysdata.data_blob import dataBlob


class dataCapital(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoCapitalData)
        self.data = data

    @property
    def capital_data(self):
        return self.data.db_capital

    @property
    def total_capital_calculator(self):
        # cache because could be slow getting calculation method from yaml
        if getattr(self, "_total_capital_calculator", None) is None:
            calc_method = get_private_then_default_key_value(
                "production_capital_method"
            )
            self._total_capital_calculator = totalCapitalCalculationData(
                self.data.db_capital, calc_method=calc_method
            )

        return self._total_capital_calculator

    def get_total_capital_with_new_broker_account_value(
        self, total_account_value_in_base_currency
    ):
        result = self.total_capital_calculator.get_total_capital_with_new_broker_account_value(
            total_account_value_in_base_currency)
        return result

    def get_series_of_total_capital(self):
        all_capital_data = self.total_capital_calculator.get_all_capital_calcs()

        return all_capital_data.Actual

    def get_series_of_maximum_capital(self):
        all_capital_data = self.total_capital_calculator.get_all_capital_calcs()

        return all_capital_data.Max

    def get_series_of_accumulated_capital(self):
        all_capital_data = self.total_capital_calculator.get_all_capital_calcs()

        return all_capital_data.Accumulated

    def get_series_of_broker_capital(self):
        all_capital_data = self.total_capital_calculator.get_all_capital_calcs()

        return all_capital_data.Broker

    def get_capital_pd_series_for_strategy(self, strategy_name):
        capital_series = self.capital_data.get_capital_pd_series_for_strategy(
            strategy_name
        )
        return capital_series

    def get_list_of_strategies_with_capital(self):
        strat_list = self.capital_data.get_list_of_strategies_with_capital()
        return strat_list

    def get_capital_for_strategy(self, strategy_name):
        capital_value = self.capital_data.get_current_capital_for_strategy(
            strategy_name
        )
        if capital_value is missing_data:
            self.data.log.error(
                "Capital data is missing for %s" %
                strategy_name)
            return missing_data

        return capital_value

    def update_capital_value_for_strategy(
        self, strategy_name, new_capital_value, date=arg_not_supplied
    ):
        self.capital_data.update_capital_value_for_strategy(
            strategy_name, new_capital_value, date=arg_not_supplied
        )


    def get_current_total_capital(self):
        return self.capital_data.get_current_total_capital()
