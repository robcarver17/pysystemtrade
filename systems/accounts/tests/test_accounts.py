import pytest
from pytest import approx

from sysdata.sim.csv_futures_sim_test_data import CsvFuturesSimTestData
from sysdata.config.configdata import Config
from systems.provided.futures_chapter15.basesystem import futures_system


@pytest.fixture(scope="module")
def system():
    """test fixture creates a system with start and end dates"""
    system = futures_system(
        data=CsvFuturesSimTestData(),
        config=Config("systems.provided.futures_chapter15.futuresconfig.yaml"),
    )

    # speed things up
    system.config.forecast_weight_estimate["method"] = "shrinkage"
    system.config.forecast_weight_estimate["date_method"] = "in_sample"
    system.config.instrument_weight_estimate["date_method"] = "in_sample"
    system.config.instrument_weight_estimate["method"] = "shrinkage"

    return system


@pytest.mark.skip
class TestAccounts:
    def test_costs_per_trade(self, system):
        self.assert_per_trade_cost(system, "EDOLLAR", 0.010989)
        self.assert_per_trade_cost(system, "US10", 0.00660)
        self.assert_per_trade_cost(system, "BTP", 0.001013)

        self.assert_per_trade_cost(system, "MXP", 0.002429)
        self.assert_per_trade_cost(system, "NZD", 0.003268)

        self.assert_per_trade_cost(system, "CORN", 0.005704)
        self.assert_per_trade_cost(system, "PLAT", 0.002774)

        self.assert_per_trade_cost(system, "EUROSTX", 0.002768)
        self.assert_per_trade_cost(system, "VIX", 0.004431)

    def test_costs_percent(self, system):
        self.assert_percentage_cost(system, "BUND", 4.0376e-5)
        self.assert_percentage_cost(system, "US5", 4.3924e-5)
        self.assert_percentage_cost(system, "OAT", 4.3061e-5)

        self.assert_percentage_cost(system, "AUD", 1.05303e-4)
        self.assert_percentage_cost(system, "JPY", 7.15712e-5)

        self.assert_percentage_cost(system, "CRUDE_W", 3.8117e-4)
        self.assert_percentage_cost(system, "COPPER", 2.3302e-4)

        self.assert_percentage_cost(system, "SMI", 1.40067e-4)
        self.assert_percentage_cost(system, "CAC", 9.06113e-5)
        self.assert_percentage_cost(system, "V2X", 4.2191e-3)

    def test_cost_of_rule(self, system):
        self.assert_rule_cost(system, "EDOLLAR", "ewmac2_8", 1.025049)
        self.assert_rule_cost(system, "EDOLLAR", "ewmac8_32", 0.286303)
        self.assert_rule_cost(system, "EDOLLAR", "ewmac32_128", 0.113658)
        self.assert_rule_cost(system, "EDOLLAR", "carry", 0.035958)

        self.assert_rule_cost(system, "CORN", "ewmac4_16", 0.269535)
        self.assert_rule_cost(system, "CORN", "ewmac16_64", 0.078757)
        self.assert_rule_cost(system, "CORN", "ewmac64_256", 0.037261)
        self.assert_rule_cost(system, "CORN", "carry", 0.010109)

    def test_costs_holding(self, system):
        self.assert_holding_cost(system, "BOBL", 0.009903)
        self.assert_holding_cost(system, "US2", 0.023439)
        self.assert_holding_cost(system, "SHATZ", 0.028115)

        self.assert_holding_cost(system, "EUR", 0.003261)
        self.assert_holding_cost(system, "GBP", 0.004076)

        self.assert_holding_cost(system, "WHEAT", 0.002518)
        self.assert_holding_cost(system, "PALLAD", 0.008138)

        self.assert_holding_cost(system, "AEX", 0.009141)
        self.assert_holding_cost(system, "SP500", 0.000924)
        self.assert_holding_cost(system, "NASDAQ", 0.000575)

    def test_costs_total(self, system):
        self.assert_total_cost(system, "KR10", 5.7, 0.02553)
        self.assert_total_cost(system, "VIX", 2.8, 0.038997)

        self.assert_total_cost(system, "MXP", 6.0, 0.019435)
        self.assert_total_cost(system, "JPY", 3.9, 0.010811)

        self.assert_total_cost(system, "COPPER", 4.2, 0.012725)
        self.assert_total_cost(system, "SOYBEAN", 5.7, 0.032369)

        self.assert_total_cost(system, "KOSPI", 3.1, 0.018728)
        self.assert_total_cost(system, "SMI", 4.4, 0.008252)

    @staticmethod
    def assert_per_trade_cost(system, instr: str, expected: float):
        actual = system.accounts.get_SR_cost_per_trade_for_instrument(instr)
        assert actual == approx(expected, rel=1e-3)

    @staticmethod
    def assert_percentage_cost(system, instr: str, expected: float):
        actual = system.accounts.get_SR_cost_per_trade_for_instrument_percentage(instr)
        assert actual == approx(expected, rel=1e-3)

    @staticmethod
    def assert_rule_cost(system, instr: str, rule: str, expected: float):
        actual = (
            system.accounts._get_SR_transaction_cost_of_rule_for_individual_instrument(
                instr, rule
            )
        )
        assert actual == approx(expected, rel=1e-3)

    @staticmethod
    def assert_holding_cost(system, instr: str, expected: float):
        actual = system.accounts.get_SR_holding_cost_only(instr)
        assert actual == approx(expected, rel=1e-3)

    @staticmethod
    def assert_total_cost(system, instr: str, turnover: float, expected: float):
        actual = system.accounts.get_SR_cost_given_turnover(instr, turnover)
        assert actual == approx(expected, rel=1e-3)
