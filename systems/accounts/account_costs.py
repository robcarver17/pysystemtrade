import pandas as pd

from syscore.maths import calculate_weighted_average_with_nans
from syscore.genutils import str2Bool
from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.pandas.strategy_functions import turnover

from sysquant.estimators.turnover import turnoverDataForTradingRule

from systems.system_cache import diagnostic, input
from systems.accounts.account_inputs import accountInputs


class accountCosts(accountInputs):
    @diagnostic()
    def get_SR_cost_for_instrument_forecast(
        self, instrument_code: str, rule_variation_name: str
    ) -> float:
        """
        Get the SR cost for a forecast/rule combination

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float

        KEY OUTPUT
        """
        ## Calculate holding and transaction separately, as the former could be pooled
        transaction_cost = self.get_SR_transaction_cost_for_instrument_forecast(
            instrument_code=instrument_code, rule_variation_name=rule_variation_name
        )
        holding_cost = self.get_SR_holding_cost_only(instrument_code)

        return transaction_cost + holding_cost

    @diagnostic()
    def get_SR_transaction_cost_for_instrument_forecast(
        self, instrument_code: str, rule_variation_name: str
    ) -> float:
        """
        Get the SR cost for a forecast/rule combination

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float

        KEY OUTPUT
        """

        use_pooled_costs = str2Bool(
            self.config.forecast_cost_estimates["use_pooled_costs"]
        )

        if use_pooled_costs:
            SR_cost = self._get_SR_transaction_costs_for_rule_with_pooled_costs(
                instrument_code, rule_variation_name
            )

        else:
            SR_cost = self._get_SR_transaction_cost_of_rule_for_individual_instrument(
                instrument_code, rule_variation_name
            )
        return SR_cost

    @input
    def _get_SR_transaction_costs_for_rule_with_pooled_costs(
        self, instrument_code: str, rule_variation_name: str
    ) -> float:
        instrument_code_list = self.has_same_rules_as_code(instrument_code)
        SR_cost = self._get_SR_transaction_cost_instr_forecast_for_list(
            instrument_code_list, rule_variation_name
        )

        return SR_cost

    @diagnostic()
    def _get_SR_transaction_cost_instr_forecast_for_list(
        self, instrument_code_list: list, rule_variation_name: str
    ) -> float:
        """
        Get the SR cost for a forecast/rule combination, averaged across multiple instruments

        :param instrument_code_list: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float


        """

        list_of_SR_cost = [
            self._get_SR_transaction_cost_of_rule_for_individual_instrument(
                instrument_code, rule_variation_name
            )
            for instrument_code in instrument_code_list
        ]

        # weight by length
        cost_weightings = self._get_forecast_length_weighting_for_list_of_instruments(
            instrument_code_list, rule_variation_name
        )

        weighted_SR_costs = [
            SR_cost * weight
            for SR_cost, weight in zip(list_of_SR_cost, cost_weightings)
        ]

        avg_SR_cost = sum(weighted_SR_costs)

        return avg_SR_cost

    @diagnostic()
    def _get_forecast_length_weighting_for_list_of_instruments(
        self, instrument_code_list: list, rule_variation_name: str
    ) -> list:
        forecast_lengths = [
            self._get_forecast_length_for_instrument_rule(
                instrument_code, rule_variation_name
            )
            for instrument_code in instrument_code_list
        ]
        total_length = float(sum(forecast_lengths))

        weights = [
            forecast_length / total_length for forecast_length in forecast_lengths
        ]

        return weights

    @diagnostic()
    def _get_forecast_length_for_instrument_rule(
        self, instrument_code: str, rule_variation_name: str
    ) -> int:
        forecast = self.get_capped_forecast(instrument_code, rule_variation_name)
        return len(forecast)

    @diagnostic()
    def _get_SR_transaction_cost_of_rule_for_individual_instrument(
        self, instrument_code: str, rule_variation_name: str
    ) -> float:
        # note the turnover may still be pooled..
        turnover = self.forecast_turnover(instrument_code, rule_variation_name)

        # holding costs calculated elsewhere
        SR_cost_trading = self.get_SR_trading_cost_only_given_turnover(
            instrument_code, turnover
        )

        return SR_cost_trading

    @diagnostic()
    def get_SR_cost_given_turnover(
        self, instrument_code: str, turnover: float
    ) -> float:
        SR_cost_trading = self.get_SR_trading_cost_only_given_turnover(
            instrument_code, turnover
        )
        SR_cost_holding = self.get_SR_holding_cost_only(instrument_code)
        SR_cost = SR_cost_holding + SR_cost_trading

        return SR_cost

    def get_SR_trading_cost_only_given_turnover(
        self, instrument_code: str, turnover: float
    ) -> float:
        cost_per_trade = self.get_SR_cost_per_trade_for_instrument(instrument_code)

        SR_cost_trading = turnover * cost_per_trade

        return SR_cost_trading

    def get_SR_holding_cost_only(self, instrument_code: str) -> float:
        cost_per_trade = self.get_SR_cost_per_trade_for_instrument(instrument_code)
        hold_turnovers = self.get_rolls_per_year(instrument_code) * 2.0

        ## Assumes no benefit from spread trades i.e. do two separate trades
        SR_cost_holding = hold_turnovers * cost_per_trade

        return SR_cost_holding

    @diagnostic()
    def get_turnover_for_forecast_combination(
        self, codes_to_use: list, rule_variation_name: str
    ) -> turnoverDataForTradingRule:
        turnover_as_list = self._forecast_turnover_for_list_by_instrument(
            codes_to_use, rule_variation_name=rule_variation_name
        )
        turnover_as_dict = dict(
            [
                (instrument_code, turnover)
                for (instrument_code, turnover) in zip(codes_to_use, turnover_as_list)
            ]
        )

        turnover_data_for_trading_rule = turnoverDataForTradingRule(turnover_as_dict)

        return turnover_data_for_trading_rule

    @diagnostic()
    def forecast_turnover(
        self, instrument_code: str, rule_variation_name: str
    ) -> float:
        use_pooled_turnover = str2Bool(
            self.config.forecast_cost_estimates["use_pooled_turnover"]
        )

        if use_pooled_turnover:
            turnover = self._forecast_turnover_pooled(
                instrument_code, rule_variation_name
            )
        else:
            turnover = self._forecast_turnover_for_individual_instrument(
                instrument_code, rule_variation_name
            )

        return turnover

    @diagnostic()
    def _forecast_turnover_pooled(
        self, instrument_code: str, rule_variation_name: str
    ) -> float:
        instrument_code_list = self.has_same_rules_as_code(instrument_code)
        turnover_for_SR = self._forecast_turnover_for_list(
            instrument_code_list, rule_variation_name=rule_variation_name
        )

        return turnover_for_SR

    @diagnostic()
    def _forecast_turnover_for_list(
        self, instrument_code_list: list, rule_variation_name: str
    ) -> float:
        """
        Get the average turnover for a rule, over instrument_code_list

        :param instrument_code_list: instruments to get values for
        :type instrument_code_list: list of str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float

        """

        turnovers = self._forecast_turnover_for_list_by_instrument(
            codes_to_use=instrument_code_list, rule_variation_name=rule_variation_name
        )

        # weight by length
        weights = self._get_forecast_length_weighting_for_list_of_instruments(
            instrument_code_list, rule_variation_name
        )

        avg_turnover = calculate_weighted_average_with_nans(weights, turnovers)

        return avg_turnover

    @diagnostic()
    def _forecast_turnover_for_list_by_instrument(
        self, codes_to_use: list, rule_variation_name: str
    ) -> list:
        turnovers = [
            self._forecast_turnover_for_individual_instrument(
                instrument_code, rule_variation_name
            )
            for instrument_code in codes_to_use
        ]

        return turnovers

    @diagnostic()
    def _forecast_turnover_for_individual_instrument(
        self, instrument_code: str, rule_variation_name: str
    ) -> float:
        forecast = self.get_capped_forecast(instrument_code, rule_variation_name)

        average_forecast_for_turnover = self.average_forecast()

        annual_turnover_for_forecast = turnover(forecast, average_forecast_for_turnover)

        return annual_turnover_for_forecast

    @diagnostic()
    def get_SR_cost_per_trade_for_instrument(self, instrument_code: str) -> float:
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
        >>> system.accounts.get_SR_cost_per_trade_for_instrument("EDOLLAR")
        0.0065584086244069775
        """

        raw_costs = self.get_raw_cost_data(instrument_code)
        block_price_multiplier = self.get_value_of_block_price_move(instrument_code)
        notional_blocks_traded = 1
        average_price = self._recent_average_price(instrument_code)
        ann_stdev_price_units = self._recent_average_annual_price_vol(instrument_code)

        SR_cost = raw_costs.calculate_sr_cost(
            block_price_multiplier=block_price_multiplier,
            ann_stdev_price_units=ann_stdev_price_units,
            blocks_traded=notional_blocks_traded,
            price=average_price,
        )

        return SR_cost

    @diagnostic()
    def _recent_average_annual_price_vol(self, instrument_code: str) -> float:
        average_vol = self._recent_average_daily_vol(instrument_code)

        avg_annual_vol = average_vol * ROOT_BDAYS_INYEAR

        return avg_annual_vol

    @diagnostic()
    def _recent_average_daily_vol(self, instrument_code: str) -> float:
        daily_vol = self.get_daily_returns_volatility(instrument_code)
        start_date = self._date_one_year_before_end_of_price_index(instrument_code)
        average_vol = float(daily_vol[start_date:].mean())

        return average_vol

    @diagnostic()
    def _recent_average_price(self, instrument_code: str) -> float:
        daily_price = self.get_daily_prices(instrument_code)
        start_date = self._date_one_year_before_end_of_price_index(instrument_code)
        average_price = float(daily_price[start_date:].mean())

        return average_price

    @diagnostic()
    def _date_one_year_before_end_of_price_index(self, instrument_code: str):
        daily_price = self.get_instrument_prices_for_position_or_forecast(
            instrument_code
        )

        last_date = daily_price.index[-1]
        start_date = last_date - pd.DateOffset(years=1)

        return start_date

    @property
    def use_SR_costs(self) -> bool:
        return str2Bool(self.config.use_SR_costs)
