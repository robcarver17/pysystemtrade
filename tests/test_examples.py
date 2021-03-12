from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysquant.estimators.vol import robust_vol_calc
from syscore.accounting import accountCurve
from systems.provided.example.rules import ewmac_forecast_with_defaults as ewmac
from systems.forecasting import Rules
from systems.basesystem import System
from systems.trading_rules import TradingRule
from sysdata.config.configdata import Config
from systems.forecast_scale_cap import ForecastScaleCap
from systems.forecast_combine import ForecastCombine
from systems.account import Account
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
import pytest
from systems.provided.example.simplesystem import simplesystem
from systems.provided.futures_chapter15.basesystem import futures_system as base_futures_system


class TestExamples:

    def test_simple_trading_rule(self):
        """
        This is (mostly) the code from 'examples.introduction.asimpletradingrule',
        but without graph plotting
        """
        # Get some data
        data = csvFuturesSimData()

        print(data)
        print(data.get_instrument_list())
        print(data.get_raw_price("EDOLLAR").tail(5))

        print(data["VIX"])
        print(data.keys())
        print(data.get_instrument_raw_carry_data("EDOLLAR").tail(6))

        instrument_code = "VIX"
        price = data.daily_prices(instrument_code)
        ewmac = self.calc_ewmac_forecast(price, 32, 128)
        ewmac2 = self.calc_ewmac_forecast(price, 16, 64)

        ewmac.columns = ["forecast"]
        print(ewmac.tail(5))

        account = accountCurve(price, forecast=ewmac)
        account2 = accountCurve(price, forecast=ewmac2)

        account.curve()
        account2.curve()

        print(account.percent().stats())
        print(account2.percent().stats())

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_simple_system(self):
        """
        This is (mostly) the code from 'examples.introduction.simplesystem',
        but without graph plotting
        """
        data = csvFuturesSimData()
        my_rules = Rules(ewmac)
        print(my_rules.trading_rules())

        my_rules = Rules(dict(ewmac=ewmac))
        print(my_rules.trading_rules())

        my_system = System([my_rules], data)
        print(my_system)
        print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac").tail(5))

        ewmac_rule = TradingRule(ewmac)
        my_rules = Rules(dict(ewmac=ewmac_rule))
        print(ewmac_rule)

        ewmac_8 = TradingRule((ewmac, [], dict(Lfast=8, Lslow=32)))
        ewmac_32 = TradingRule(
            dict(
                function=ewmac,
                other_args=dict(
                    Lfast=32,
                    Lslow=128)))
        my_rules = Rules(dict(ewmac8=ewmac_8, ewmac32=ewmac_32))
        print(my_rules.trading_rules()["ewmac32"])

        my_system = System([my_rules], data)
        my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5)

        my_config = Config()
        print(my_config)

        empty_rules = Rules()
        my_config.trading_rules = dict(ewmac8=ewmac_8, ewmac32=ewmac_32)
        my_system = System([empty_rules], data, my_config)
        my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5)

        # we can estimate these ourselves
        my_config.instruments = ["US10", "EDOLLAR", "CORN", "SP500"]
        my_config.use_forecast_scale_estimates = True

        fcs = ForecastScaleCap()
        my_system = System([fcs, my_rules], data, my_config)
        my_config.forecast_scalar_estimate["pool_instruments"] = False
        print(
            my_system.forecastScaleCap.get_forecast_scalar(
                "EDOLLAR",
                "ewmac32").tail(5))

        # or we can use the values from the book
        my_config.forecast_scalars = dict(ewmac8=5.3, ewmac32=2.65)
        my_config.use_forecast_scale_estimates = False
        fcs = ForecastScaleCap()
        my_system = System([fcs, my_rules], data, my_config)
        print(
            my_system.forecastScaleCap.get_capped_forecast(
                "EDOLLAR",
                "ewmac32").tail(5))

        # defaults
        combiner = ForecastCombine()
        my_system = System([fcs, my_rules, combiner], data, my_config)
        print(my_system.combForecast.get_forecast_weights("EDOLLAR").tail(5))
        print(my_system.combForecast.get_monthly_forecast_diversification_multiplier("EDOLLAR").tail(5))

        # estimates:
        my_account = Account()
        combiner = ForecastCombine()

        my_config.forecast_weight_estimate = dict(method="one_period")
        my_config.use_forecast_weight_estimates = True
        my_config.use_forecast_div_mult_estimates = True

        my_system = System([my_account, fcs, my_rules, combiner], data, my_config)

        # this is a bit slow, better to know what's going on
        my_system.set_logging_level("on")

        print(my_system.combForecast.get_forecast_weights("US10").tail(5))
        print(my_system.combForecast.get_monthly_forecast_diversification_multiplier("US10").tail(5))

        # fixed:
        my_config.forecast_weights = dict(ewmac8=0.5, ewmac32=0.5)
        my_config.forecast_div_multiplier = 1.1
        my_config.use_forecast_weight_estimates = False
        my_config.use_forecast_div_mult_estimates = False

        combiner = ForecastCombine()
        my_system = System(
            [fcs, empty_rules, combiner], data, my_config
        )  # no need for accounts if no estimation done
        my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5)

        # size positions
        possizer = PositionSizing()
        my_config.percentage_vol_target = 25
        my_config.notional_trading_capital = 500000
        my_config.base_currency = "GBP"

        my_system = System([fcs, my_rules, combiner, possizer], data, my_config)

        print(my_system.positionSize.get_price_volatility("EDOLLAR").tail(5))
        print(my_system.positionSize.get_block_value("EDOLLAR").tail(5))
        print(my_system.positionSize.get_instrument_sizing_data("EDOLLAR"))
        print(my_system.positionSize.get_instrument_value_vol("EDOLLAR").tail(5))
        print(my_system.positionSize.get_volatility_scalar("EDOLLAR").tail(5))
        print(my_system.positionSize.get_daily_cash_vol_target())
        print(my_system.positionSize.get_subsystem_position("EDOLLAR").tail(5))

        # portfolio - estimated
        portfolio = Portfolios()

        my_config.use_instrument_weight_estimates = True
        my_config.use_instrument_div_mult_estimates = True
        my_config.instrument_weight_estimate = dict(
            method="shrinkage", date_method="in_sample")

        my_system = System(
            [my_account, fcs, my_rules, combiner, possizer, portfolio], data, my_config
        )

        my_system.set_logging_level("on")

        print(my_system.portfolio.get_instrument_weights().tail(5))
        print(my_system.portfolio.get_instrument_diversification_multiplier().tail(5))

        # or fixed
        portfolio = Portfolios()
        my_config.use_instrument_weight_estimates = False
        my_config.use_instrument_div_mult_estimates = False
        my_config.instrument_weights = dict(US10=0.1, EDOLLAR=0.4, CORN=0.3, SP500=0.2)
        my_config.instrument_div_multiplier = 1.5

        my_system = System([fcs, my_rules, combiner, possizer,
                            portfolio], data, my_config)

        print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))

        my_system = System(
            [fcs, my_rules, combiner, possizer, portfolio, my_account], data, my_config
        )
        profits = my_system.accounts.portfolio()
        print(profits.percent().stats())

        # have costs data now
        print(profits.gross.percent().stats())
        print(profits.net.percent().stats())

        my_config = Config(
            dict(
                trading_rules=dict(ewmac8=ewmac_8, ewmac32=ewmac_32),
                instrument_weights=dict(US10=0.1, EDOLLAR=0.4, CORN=0.3, SP500=0.2),
                instrument_div_multiplier=1.5,
                forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65),
                forecast_weights=dict(ewmac8=0.5, ewmac32=0.5),
                forecast_div_multiplier=1.1,
                percentage_vol_target=25.00,
                notional_trading_capital=500000,
                base_currency="GBP"
            )
        )
        print(my_config)
        my_system = System(
            [
                Account(),
                Portfolios(),
                PositionSizing(),
                ForecastCombine(),
                ForecastScaleCap(),
                Rules()
            ],
            data,
            my_config,
        )
        print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))

        my_config = Config("systems.provided.example.simplesystemconfig.yaml")
        print(my_config)
        my_system = System(
            [
                Account(),
                Portfolios(),
                PositionSizing(),
                ForecastCombine(),
                ForecastScaleCap(),
                Rules()
            ],
            data,
            my_config,
        )
        print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac32").tail(5))
        print(my_system.rules.get_raw_forecast("EDOLLAR", "ewmac8").tail(5))
        print(
            my_system.forecastScaleCap.get_capped_forecast(
                "EDOLLAR",
                "ewmac32").tail(5))
        print(my_system.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac32"))
        print(my_system.combForecast.get_combined_forecast("EDOLLAR").tail(5))
        print(my_system.combForecast.get_forecast_weights("EDOLLAR").tail(5))

        print(my_system.positionSize.get_subsystem_position("EDOLLAR").tail(5))

        print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_prebaked_simple_system(self):
        """
        This is the simple system from 'examples.introduction.prebakedsimplesystems'
        """
        my_system = simplesystem(log_level="on")
        print(my_system)
        print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_prebaked_from_confg(self):
        """
        This is the config system from 'examples.introduction.prebakedsimplesystems'
        """
        my_config = Config("systems.provided.example.simplesystemconfig.yaml")
        my_data = csvFuturesSimData()
        my_system = simplesystem(config=my_config, data=my_data)
        print(my_system.portfolio.get_notional_position("EDOLLAR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_prebaked_chapter15(self):
        """
        This is (mostly) the chapter 15 system from 'examples.introduction.prebakedsimplesystems'
        but without graph plotting
        """
        system = base_futures_system(log_level="on")
        print(system.accounts.portfolio().sharpe())

    @staticmethod
    def calc_ewmac_forecast(price, Lfast, Lslow=None):
        """
        Calculate the ewmac trading fule forecast, given a price and EWMA speeds
        Lfast, Lslow and vol_lookback

        """
        # price: This is the stitched price series
        # We can't use the price of the contract we're trading, or the volatility
        # will be jumpy
        # And we'll miss out on the rolldown. See
        # https://qoppac.blogspot.com/2015/05/systems-building-futures-rolling.html

        price = price.resample("1B").last()

        if Lslow is None:
            Lslow = 4 * Lfast

        # We don't need to calculate the decay parameter, just use the span
        # directly
        fast_ewma = price.ewm(span=Lfast).mean()
        slow_ewma = price.ewm(span=Lslow).mean()
        raw_ewmac = fast_ewma - slow_ewma

        vol = robust_vol_calc(price.diff())
        return raw_ewmac / vol
