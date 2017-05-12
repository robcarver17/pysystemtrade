'''
Created on 30 Nov 2015

@author: rob
'''
import unittest
from systems.provided.example.rules import ewmac_forecast_with_defaults
from systems.forecasting import TradingRule, Rules, process_trading_rules, create_variations, create_variations_oneparameter
from systems.basesystem import System
from systems.rawdata import RawData
from systems.futures.rawdata import FuturesRawData
from systems.provided.futures_chapter15.rules import carry
from sysdata.configdata import Config
from sysdata.csvdata import csvFuturesData
import matplotlib.pyplot as plt


class Test(unittest.TestCase):
    def testRules(self):

        # config=Config(dict(trading_rules=dict(ewmac=dict(function="systems.provided.example.rules.ewmac_forecast_with_defaults"))))
        data = csvFuturesData("sysdata.tests")

        rules = Rules(
            dict(
                function=
                "systems.provided.example.rules.ewmac_forecast_with_defaults"))
        system = System([rules], data)

        ans = system.rules.get_raw_forecast("EDOLLAR", "rule0")
        self.assertAlmostEqual(ans.tail(1).values[0], 2.1384223788141838, 5)

        config = Config(
            dict(trading_rules=dict(ewmac=dict(
                function=
                "systems.provided.example.rules.ewmac_forecast_with_defaults"))
                 ))
        rules = Rules()
        system = System([rules], data, config)
        ans = system.rules.get_raw_forecast("EDOLLAR", "ewmac")
        self.assertAlmostEqual(ans.tail(1).values[0], 2.1384223788141838, 5)

        config = Config("systems.provided.example.exampleconfig.yaml")
        rawdata = RawData()

        rules = Rules()
        system = System([rules, rawdata], data, config)
        ans = system.rules.get_raw_forecast("EDOLLAR", "ewmac8")
        self.assertAlmostEqual(ans.tail(1).values[0], 0.16438313875, 5)

    def testinitTradingRules(self):
        rule = TradingRule((ewmac_forecast_with_defaults, [], {}))
        assert rule.function == ewmac_forecast_with_defaults
        rule2 = TradingRule(rule)

        assert (rule.function, rule.data, rule.other_args) == (
            rule2.function, rule2.data, rule2.other_args)

        rule3 = TradingRule(ewmac_forecast_with_defaults,
                            ["data.get_instrument_price"],
                            dict(Lfast=50, Lslow=200))

        assert rule3.data == ["data.get_instrument_price"]

        rule4 = TradingRule(ewmac_forecast_with_defaults,
                            "data.get_instrument_price",
                            dict(Lfast=50, Lslow=200))

        assert rule4.data == ["data.get_instrument_price"]

        try:
            rule4 = TradingRule(ewmac_forecast_with_defaults,
                                "data.get_instrument_price")
            rule5 = TradingRule((ewmac_forecast_with_defaults, ))

            raise Exception("Should have failed with 2 tuple")
        except:
            pass

        rule7 = TradingRule(
            "systems.provided.example.rules.ewmac_forecast_with_defaults", [],
            dict(Lfast=50, Lslow=200))
        assert rule7.function == rule.function

        try:
            rule8 = TradingRule(
                "not.a.real.rule.just.a.string.of.arbitrary.text", [],
                dict(Lfast=50, Lslow=200))
            raise Exception("Should have failed with non existent rule")
        except:
            pass

        rule9 = TradingRule(dict(function=ewmac_forecast_with_defaults))

        try:
            rule10 = TradingRule(
                dict(functionette=ewmac_forecast_with_defaults))
            raise Exception("Should have failed with no function keyword")
        except:
            pass

        rule11 = TradingRule(
            dict(
                function=
                "systems.provided.example.rules.ewmac_forecast_with_defaults",
                other_args=dict(Lfast=50),
                data=[]))

        rule12 = TradingRule(
            ewmac_forecast_with_defaults, other_args=dict(Lfast=30))
        rule13 = TradingRule(
            "systems.provided.example.rules.ewmac_forecast_with_defaults",
            data="data.get_pricedata")
        assert rule13.data == ["data.get_pricedata"]

        rule14 = TradingRule(ewmac_forecast_with_defaults)

        try:
            rule15 = TradingRule(set())
            raise Exception("Should have failed with other data type")
        except:
            pass

    def testCallingTradingRule(self):

        # config=Config(dict(trading_rules=dict(ewmac=dict(function="systems.provided.example.rules.ewmac_forecast_with_defaults"))))
        data = csvFuturesData("sysdata.tests")

        rawdata = RawData()
        rules = Rules()
        system = System([rawdata, rules], data)

        # Call with default data and config
        rule = TradingRule(ewmac_forecast_with_defaults)
        ans = rule.call(system, "EDOLLAR")
        self.assertAlmostEqual(ans.tail(1).values[0], 2.1384223788141838, 5)

        # Change the data source
        rule = TradingRule((
            "systems.provided.example.rules.ewmac_forecast_with_defaults_no_vol",
            ["rawdata.get_daily_prices",
             "rawdata.daily_returns_volatility"], dict()))

        ans = rule.call(system, "EDOLLAR")
        self.assertAlmostEqual(ans.tail(1).values[0], 0.029376, 5)

        rule = TradingRule(
            dict(
                function=
                "systems.provided.example.rules.ewmac_forecast_with_defaults_no_vol",
                data=[
                    "rawdata.get_daily_prices",
                    "rawdata.daily_returns_volatility"
                ],
                other_args=dict(Lfast=50, Lslow=200)))
        ans = rule.call(system, "EDOLLAR")
        self.assertAlmostEqual(ans.tail(1).values[0], 3.84426755)

    def testCarryRule(self):
        data = csvFuturesData("sysdata.tests")

        rawdata = FuturesRawData()
        rules = Rules()
        system = System([rawdata, rules], data)
        rule = TradingRule(
            carry, [
                "rawdata.daily_annualised_roll",
                "rawdata.daily_returns_volatility"
            ],
            dict(smooth_days=90))
        ans = rule.call(system, "EDOLLAR")
        self.assertAlmostEqual(ans.tail(1).values[0], 0.411686026, 5)

    def testProcessTradingRuleSpec(self):

        ruleA = TradingRule(ewmac_forecast_with_defaults)
        ruleB = TradingRule(
            dict(
                function=
                "systems.provided.example.rules.ewmac_forecast_with_defaults_no_vol",
                data=
                ["rawdata.daily_prices", "rawdata.daily_returns_volatility"],
                other_args=dict(Lfast=50, Lslow=200)))

        trading_rules = dict(ruleA=ruleA, ruleB=ruleB)
        ans = process_trading_rules(trading_rules)
        assert "ruleA" in ans.keys()
        assert "ruleB" in ans.keys()

        trading_rules = [ruleA, ruleB]
        ans = process_trading_rules(trading_rules)
        assert "rule1" in ans.keys()

        ans = process_trading_rules(ruleA)
        assert ans['rule0'].function == ewmac_forecast_with_defaults

        ans = process_trading_rules(ewmac_forecast_with_defaults)
        assert ans['rule0'].function == ewmac_forecast_with_defaults

        ans = process_trading_rules([
            dict(
                function=
                "systems.provided.example.rules.ewmac_forecast_with_defaults_no_vol",
                data=[
                    "rawdata.daily_prices", "rawdata.daily_returns_volatility"
                ],
                other_args=dict(Lfast=50, Lslow=200))
        ])
        assert ans['rule0'].other_args['Lfast'] == 50


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testTradingRules']
    unittest.main()
