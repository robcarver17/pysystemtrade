
from syscore.genutils import str2Bool

from syscore.pdutils import turnover

from systems.system_cache import  diagnostic

from systems.accounts.account_inputs import accountInputs

class accountCosts(accountInputs):
    @diagnostic()
    def get_SR_cost_for_instrument_forecast(
            self, instrument_code: str,
            rule_variation_name: str) -> float:
        """
        Get the SR cost for a forecast/rule combination

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float

        KEY OUTPUT
        """

        use_pooled_costs = str2Bool(self.parent.config.forecast_cost_estimates[
                                        "use_pooled_costs"
                                    ])

        if use_pooled_costs:
            SR_cost = self.get_SR_cost_for_pooled_costs(instrument_code=instrument_code,
                                                        rule_variation_name=rule_variation_name)

        else:
            SR_cost = self.get_SR_cost_for_individual_instrument(instrument_code=instrument_code,
                                                                 rule_variation_name=rule_variation_name)
        return SR_cost

    @input
    def get_SR_cost_for_pooled_costs(self, instrument_code: str,
                                     rule_variation_name: str) -> float:
        instrument_code_list = self.has_same_rules_as_code(instrument_code)
        SR_cost = self.get_SR_cost_instr_forecast_for_list(
            instrument_code_list, rule_variation_name
        )

        return SR_cost

    @diagnostic()
    def get_SR_cost_instr_forecast_for_list(
            self, instrument_code_list: list,
            rule_variation_name: str
    ) -> float:
        """
        Get the SR cost for a forecast/rule combination, averaged across multiple instruments

        :param instrument_code_list: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float


        """

        list_of_SR_cost = [self.get_SR_cost_for_individual_instrument(instrument_code,
                                                                      rule_variation_name=rule_variation_name)
                           for instrument_code in instrument_code_list]

        # weight by length
        cost_weightings = self.get_forecast_length_weighting_for_list_of_instruments(instrument_code_list,
                                                                                     rule_variation_name=rule_variation_name)

        weighted_SR_costs = [SR_cost * weight for SR_cost, weight in
                             zip(list_of_SR_cost, cost_weightings)
                             ]

        avg_SR_cost = sum(weighted_SR_costs)

        return avg_SR_cost

    @diagnostic()
    def get_forecast_length_weighting_for_list_of_instruments(self, instrument_code_list: list,
                                                              rule_variation_name: str) -> list:

        forecast_lengths = [self.get_forecast_length_for_instrument_rule(instrument_code,
                                                                         rule_variation_name=rule_variation_name)
                            for instrument_code in instrument_code_list]
        total_length = float(sum(forecast_lengths))

        weights = [forecast_length / total_length for forecast_length in forecast_lengths]

        return weights

    @diagnostic()
    def get_forecast_length_for_instrument_rule(self, instrument_code: str,
                                                rule_variation_name: str) -> int:
        forecast = self.get_capped_forecast(instrument_code, rule_variation_name)
        return len(forecast)

    def get_SR_cost_for_individual_instrument(self, instrument_code: str,
                                              rule_variation_name: str) -> float:

        # note the turnover may still be pooled..
        turnover = self.forecast_turnover(
            instrument_code, rule_variation_name
        )
        cost_per_turnover = self.get_SR_cost(instrument_code)

        SR_cost = turnover * cost_per_turnover

        return SR_cost

    def forecast_turnover(self, instrument_code: str,
                          rule_variation_name: str) -> float:
        use_pooled_turnover = str2Bool(
            self.parent.config.forecast_cost_estimates["use_pooled_turnover"]
        )

        if use_pooled_turnover:

        else:
            instrument_code_list = [instrument_code]


        return turnover_for_SR

    @diagnostic
    def forecast_turnover_pooled(self, instrument_code: str,
                                 rule_variation_name: str) -> float:

        instrument_code_list = self.has_same_rules_as_code(instrument_code)
        turnover_for_SR = self.forecast_turnover_for_list(
            instrument_code_list, rule_variation_name
        )

        return  turnover_for_SR

    @diagnostic()
    def forecast_turnover_for_list(
            self,
            instrument_code_list,
            rule_variation_name):
        """
        Get the average turnover for a rule, over instrument_code_list

        :param instrument_code_list: instruments to get values for
        :type instrument_code_list: list of str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float

        """

        forecast_list = [
            self.get_capped_forecast(instrument_code, rule_variation_name)
            for instrument_code in instrument_code_list
        ]

        turnovers = self._forecast_turnover_for_individual_instrument(instrument_code_list,
                                                                      rule_variation_name)
        if len(instrument_code_list) == 1:
            return turnovers[0]

        # weight by length
        forecast_lengths = [len(forecast.index) for forecast in forecast_list]
        total_length = sum(forecast_lengths)
        weighted_turnovers = [
            tover * fc_length / total_length
            for (tover, fc_length) in zip(turnovers, forecast_lengths)
        ]

        avg_turnover = sum(weighted_turnovers)

        return avg_turnover



    @diagnostic()
    def _forecast_turnover_for_individual_instrument(
            self,
            instrument_code_list,
            rule_variation_name):

        forecast_list = [
            self.get_capped_forecast(instrument_code, rule_variation_name)
            for instrument_code in instrument_code_list
        ]

        config = self.parent.config ## FIX ME CHANGE
        average_forecast_for_turnover = config.average_absolute_forecast


        turnovers = [
            turnover(forecast, average_forecast_for_turnover)
            for forecast in forecast_list
        ]

        return turnovers



    @diagnostic()
    def get_SR_cost(self, instrument_code):
        """
        Get the vol normalised SR costs for an instrument

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: float

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_SR_cost("EDOLLAR")
        0.0065584086244069775
        """

        raw_costs = self.get_raw_cost_data(instrument_code)
        block_value = self.get_value_of_price_move(instrument_code)

        daily_price = self.get_daily_price(instrument_code)

        last_date = daily_price.index[-1]
        start_date = last_date - pd.DateOffset(years=1)
        average_price = float(daily_price[start_date:].mean())

        # Cost in Sharpe Ratio terms
        # First work out costs in percentage terms
        value_per_block = average_price * block_value
        cost_in_currency_terms = raw_costs.calculate_cost_instrument_currency(1, value_per_block = value_per_block)
        cost_in_percentage_terms = cost_in_currency_terms / value_per_block

        daily_vol = self.get_daily_returns_volatility(instrument_code)
        average_vol = float(daily_vol[start_date:].mean())
        avg_annual_vol = average_vol * ROOT_BDAYS_INYEAR
        avg_annual_vol_perc = avg_annual_vol / average_price

        SR_cost = 2.0 * cost_in_percentage_terms / avg_annual_vol_perc

        return SR_cost