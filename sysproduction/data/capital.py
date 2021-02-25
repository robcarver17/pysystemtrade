import  datetime
import  pandas as pd

from syscore.objects import arg_not_supplied, missing_data

from sysdata.production.capital import totalCapitalCalculationData
from sysdata.mongodb.mongo_capital import mongoCapitalData
from sysdata.data_blob import dataBlob

from sysproduction.data.generic_production_data import productionDataLayerGeneric
from sysdata.production.capital import capitalData

class dataCapital(productionDataLayerGeneric):

    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_object(mongoCapitalData)

        return data

    @property
    def db_capital_data(self) -> capitalData:
        return self.data.db_capital

    ## TOTAL CAPITAL...

    def get_current_total_capital(self) -> float:
        return self.total_capital_calculator.get_current_total_capital()

    def update_and_return_total_capital_with_new_broker_account_value(
            self, total_account_value_in_base_currency: float, check_limit: float = 0.1
    ) -> float:

        result = self.total_capital_calculator.update_and_return_total_capital_with_new_broker_account_value(
            total_account_value_in_base_currency, check_limit=check_limit)

        return result

    def get_series_of_all_global_capital(self) -> pd.DataFrame:
        all_capital_data = self.total_capital_calculator.get_all_capital_calcs()

        return all_capital_data

    def get_series_of_maximum_capital(self) -> pd.DataFrame:
        return self.total_capital_calculator.get_maximum_account()

    def get_series_of_accumulated_capital(self) -> pd.DataFrame:
        return self.total_capital_calculator.get_profit_and_loss_account()

    def get_series_of_broker_capital(self) -> pd.DataFrame:
        return self.total_capital_calculator.get_broker_account()

    @property
    def total_capital_calculator(self) -> totalCapitalCalculationData:
        # cache because could be slow getting calculation method from yaml
        total_capital_calculator =getattr(self, "_total_capital_calculator", None)
        if total_capital_calculator is None:
            total_capital_calculator = self._get_total_capital_calculator()
            self._total_capital_calculator  = total_capital_calculator

        return total_capital_calculator

    def _get_total_capital_calculator(self) -> totalCapitalCalculationData:
        calc_method = self.get_capital_calculation_method()
        total_capital_calculator = totalCapitalCalculationData(
            self.db_capital_data, calc_method=calc_method
        )

        return total_capital_calculator

    def get_capital_calculation_method(self) -> str:
        config = self.data.config

        return config.production_capital_method



    ## STRATEGY CAPITAL
    def get_capital_pd_series_for_strategy(self, strategy_name: str) -> pd.DataFrame:
        capital_series = self.db_capital_data.get_capital_pd_df_for_strategy(
            strategy_name
        )
        return capital_series

    def get_list_of_strategies_with_capital(self) -> list:
        strat_list = self.db_capital_data.get_list_of_strategies_with_capital()
        return strat_list

    def get_capital_for_strategy(self, strategy_name: str) -> float:
        capital_value = self.db_capital_data.get_current_capital_for_strategy(
            strategy_name
        )
        if capital_value is missing_data:
            self.data.log.error(
                "Capital data is missing for %s" %
                strategy_name)
            return missing_data

        return capital_value

    def update_capital_value_for_strategy(
        self, strategy_name: str,
            new_capital_value: float,
            date: datetime.datetime=arg_not_supplied
    ):

        self.db_capital_data.update_capital_value_for_strategy(
            strategy_name, new_capital_value, date=date
        )


