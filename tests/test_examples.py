from syscore.constants import arg_not_supplied
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysquant.estimators.vol import robust_vol_calc
from systems.provided.rules.ewmac import ewmac_forecast_with_defaults as ewmac
from systems.forecasting import Rules
from systems.basesystem import System
from systems.trading_rules import TradingRule
from sysdata.config.configdata import Config
from systems.forecast_scale_cap import ForecastScaleCap
from systems.forecast_combine import ForecastCombine
from systems.accounts.accounts_stage import Account
from systems.positionsizing import PositionSizing
from systems.rawdata import RawData
from systems.portfolio import Portfolios
import pytest
from systems.provided.example.simplesystem import simplesystem
from systems.provided.futures_chapter15.basesystem import (
    futures_system as base_futures_system,
)


@pytest.fixture()
def data():
    data = csvFuturesSimData()
    return data


@pytest.fixture()
def raw_data():
    return RawData()


@pytest.fixture()
def ewmac_8():
    return TradingRule((ewmac, [], dict(Lfast=8, Lslow=32)))


@pytest.fixture()
def ewmac_32():
    return TradingRule(dict(function=ewmac, other_args=dict(Lfast=32, Lslow=128)))


@pytest.fixture()
def my_rules(ewmac_8, ewmac_32):
    return Rules(dict(ewmac8=ewmac_8, ewmac32=ewmac_32))


@pytest.fixture()
def my_config(ewmac_8, ewmac_32):
    my_config = Config()
    my_config.trading_rules = dict(ewmac8=ewmac_8, ewmac32=ewmac_32)
    my_config.instruments = ["US10", "SOFR", "CORN", "SP500"]
    my_config.notional_trading_capital = 1000000
    my_config.exclude_instrument_lists = dict(
        ignore_instruments=["MILK"],
        trading_restrictions=["BUTTER"],
        bad_markets=["CHEESE"],
    )

    return my_config


@pytest.fixture()
def fcs():
    return ForecastScaleCap()


@pytest.fixture()
def combiner():
    return ForecastCombine()


@pytest.fixture()
def possizer():
    return PositionSizing()


@pytest.fixture()
def account():
    return Account()


@pytest.fixture()
def portfolio():
    return Portfolios()


class TestExamples:
    """
    This is (mostly) the code from 'examples.introduction.simplesystem',
    but without graph plotting
    """

    def test_simple_system_rules(self, data, raw_data):
        my_rules = Rules(ewmac)
        print(my_rules.trading_rules())

        my_rules = Rules(dict(ewmac=ewmac))
        print(my_rules.trading_rules())

        my_system = System([my_rules, raw_data], data)
        print(my_system)
        print(my_system.rules.get_raw_forecast("SOFR", "ewmac").tail(5))

    def test_simple_system_trading_rule(self, data, raw_data, ewmac_8, ewmac_32):
        ewmac_rule = TradingRule(ewmac)
        print(ewmac_rule)

        my_rules = Rules(dict(ewmac8=ewmac_8, ewmac32=ewmac_32))
        print(my_rules.trading_rules()["ewmac32"])

        my_system = System([my_rules, raw_data], data)
        my_system.rules.get_raw_forecast("SOFR", "ewmac32").tail(5)

    def test_simple_system_trading_rules_estimated(
        self, data, raw_data, ewmac_8, ewmac_32, fcs
    ):
        my_rules = Rules(dict(ewmac8=ewmac_8, ewmac32=ewmac_32))
        my_config = Config()
        print(my_config)

        empty_rules = Rules()
        my_config.trading_rules = dict(ewmac8=ewmac_8, ewmac32=ewmac_32)
        my_system = System([empty_rules, raw_data], data, my_config)
        my_system.rules.get_raw_forecast("SOFR", "ewmac32").tail(5)

        # we can estimate these ourselves
        my_config.instruments = ["US10", "SOFR", "CORN", "SP500"]
        my_config.use_forecast_scale_estimates = True

        my_system = System([fcs, my_rules, raw_data], data, my_config)
        my_config.forecast_scalar_estimate["pool_instruments"] = False
        print(my_system.forecastScaleCap.get_forecast_scalar("SOFR", "ewmac32").tail(5))

    def test_simple_system_trading_rules_fixed(self, data, my_rules, fcs):
        # or we can use the values from the book
        my_config = Config()
        my_config.trading_rules = dict(ewmac8=ewmac_8, ewmac32=ewmac_32)
        my_config.instruments = ["US10", "SOFR", "CORN", "SP500"]
        my_config.forecast_scalars = dict(ewmac8=5.3, ewmac32=2.65)
        my_config.use_forecast_scale_estimates = False

        my_system = System([fcs, my_rules], data, my_config)
        print(my_system.forecastScaleCap.get_capped_forecast("SOFR", "ewmac32").tail(5))

    def test_simple_system_combing_rules(
        self, data, raw_data, my_rules, my_config, fcs
    ):
        # defaults
        combiner = ForecastCombine()
        my_system = System([fcs, my_rules, combiner, raw_data], data, my_config)
        print(my_system.combForecast.get_forecast_weights("SOFR").tail(5))
        print(
            my_system.combForecast.get_forecast_diversification_multiplier("SOFR").tail(
                5
            )
        )

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_simple_system_combining_and_estimating(
        self, data, raw_data, my_rules, my_config, fcs, combiner, possizer, account
    ):
        # estimates:
        my_config.forecast_weight_estimate = dict(method="one_period")
        my_config.use_forecast_weight_estimates = True
        my_config.use_forecast_div_mult_estimates = True

        my_system = System(
            [account, fcs, my_rules, combiner, raw_data, possizer], data, my_config
        )

        print(my_system.combForecast.get_forecast_weights("US10").tail(5))
        print(
            my_system.combForecast.get_forecast_diversification_multiplier("US10").tail(
                5
            )
        )

    def test_simple_system_combining_fixed(self, data, raw_data, my_config, fcs):
        # fixed:
        my_config.forecast_weights = dict(ewmac8=0.5, ewmac32=0.5)
        my_config.forecast_div_multiplier = 1.1
        my_config.use_forecast_weight_estimates = False
        my_config.use_forecast_div_mult_estimates = False

        empty_rules = Rules()
        combiner = ForecastCombine()
        my_system = System(
            [fcs, empty_rules, combiner, raw_data], data, my_config
        )  # no need for accounts if no estimation done
        my_system.combForecast.get_combined_forecast("SOFR").tail(5)

    def test_simple_system_position_sizing(
        self, data, raw_data, my_rules, my_config, fcs, combiner, possizer
    ):
        # size positions
        my_config.percentage_vol_target = 25
        my_config.notional_trading_capital = 500000
        my_config.base_currency = "GBP"

        my_system = System(
            [fcs, my_rules, combiner, possizer, raw_data], data, my_config
        )

        print(my_system.positionSize.get_price_volatility("SOFR").tail(5))
        print(my_system.positionSize.get_block_value("SOFR").tail(5))
        print(my_system.positionSize.get_underlying_price("SOFR"))
        print(my_system.positionSize.get_instrument_value_vol("SOFR").tail(5))
        print(
            my_system.positionSize.get_average_position_at_subsystem_level("SOFR").tail(
                5
            )
        )
        print(my_system.positionSize.get_vol_target_dict())
        print(my_system.positionSize.get_subsystem_position("SOFR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_simple_system_portfolio_estimated(
        self, data, raw_data, my_rules, my_config, fcs, combiner, possizer, account
    ):
        # portfolio - estimated
        portfolio = Portfolios()

        my_config.use_instrument_weight_estimates = True
        my_config.use_instrument_div_mult_estimates = True
        my_config.instrument_weight_estimate = dict(
            method="shrinkage", date_method="in_sample"
        )

        my_system = System(
            [account, fcs, my_rules, combiner, possizer, portfolio, raw_data],
            data,
            my_config,
        )

        print(my_system.portfolio.get_instrument_weights().tail(5))
        print(my_system.portfolio.get_instrument_diversification_multiplier().tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_simple_system_portfolio_fixed(
        self, data, raw_data, my_rules, my_config, fcs, combiner, possizer, portfolio
    ):
        # or fixed
        my_config.use_instrument_weight_estimates = False
        my_config.use_instrument_div_mult_estimates = False
        my_config.instrument_weights = dict(US10=0.1, SOFR=0.4, CORN=0.3, SP500=0.2)
        my_config.instrument_div_multiplier = 1.5
        my_config.forecast_weights = dict(ewmac8=0.5, ewmac32=0.5)
        my_config.use_forecast_weight_estimates = False

        my_system = System(
            [fcs, my_rules, combiner, possizer, portfolio, raw_data], data, my_config
        )

        print(my_system.portfolio.get_notional_position("SOFR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_simple_system_costs(
        self,
        data,
        raw_data,
        my_rules,
        my_config,
        fcs,
        combiner,
        possizer,
        portfolio,
        account,
    ):
        my_config.forecast_weights = dict(ewmac8=0.5, ewmac32=0.5)
        my_config.instrument_weights = dict(US10=0.1, SOFR=0.4, CORN=0.3, SP500=0.2)

        my_system = System(
            [fcs, my_rules, combiner, possizer, portfolio, account, raw_data],
            data,
            my_config,
        )
        profits = my_system.accounts.portfolio()
        print(profits.percent.stats())

        # have costs data now
        print(profits.gross.percent.stats())
        print(profits.net.percent.stats())

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_simple_system_config_object(self, data, ewmac_8, ewmac_32):
        my_config = Config(
            dict(
                trading_rules=dict(ewmac8=ewmac_8, ewmac32=ewmac_32),
                instrument_weights=dict(US10=0.1, SOFR=0.4, CORN=0.3, SP500=0.2),
                instrument_div_multiplier=1.5,
                forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65),
                forecast_weights=dict(ewmac8=0.5, ewmac32=0.5),
                forecast_div_multiplier=1.1,
                percentage_vol_target=25.00,
                notional_trading_capital=500000,
                base_currency="GBP",
                exclude_instrument_lists=dict(
                    ignore_instruments=["MILK"],
                    trading_restrictions=["BUTTER"],
                    bad_markets=["CHEESE"],
                ),
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
                Rules(),
                RawData(),
            ],
            data,
            my_config,
        )
        print(my_system.portfolio.get_notional_position("SOFR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_simple_system_risk_overlay(self, data, ewmac_8, ewmac_32):
        my_config = Config(
            dict(
                trading_rules=dict(ewmac8=ewmac_8, ewmac32=ewmac_32),
                instrument_weights=dict(US10=0.1, SOFR=0.4, CORN=0.3, SP500=0.2),
                instrument_div_multiplier=1.5,
                forecast_scalars=dict(ewmac8=5.3, ewmac32=2.65),
                forecast_weights=dict(ewmac8=0.5, ewmac32=0.5),
                forecast_div_multiplier=1.1,
                percentage_vol_target=25.00,
                notional_trading_capital=500000,
                base_currency="GBP",
                risk_overlay=dict(
                    max_risk_fraction_normal_risk=1.4,
                    max_risk_fraction_stdev_risk=3.6,
                    max_risk_limit_sum_abs_risk=3.4,
                    max_risk_leverage=13.0,
                ),
                exclude_instrument_lists=dict(
                    ignore_instruments=["MILK"],
                    trading_restrictions=["BUTTER"],
                    bad_markets=["CHEESE"],
                ),
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
                Rules(),
                RawData(),
            ],
            data,
            my_config,
        )
        print(my_system.portfolio.get_notional_position("SOFR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_simple_system_config_import(self, data):
        my_config = Config("systems.provided.example.simplesystemconfig.yaml")
        my_config.exclude_instrument_lists = dict(
            ignore_instruments=["MILK"],
            trading_restrictions=["BUTTER"],
            bad_markets=["CHEESE"],
        )
        print(my_config)
        my_system = System(
            [
                Account(),
                Portfolios(),
                PositionSizing(),
                ForecastCombine(),
                ForecastScaleCap(),
                Rules(),
                RawData(),
            ],
            data,
            my_config,
        )
        print(my_system.rules.get_raw_forecast("SOFR", "ewmac32").tail(5))
        print(my_system.rules.get_raw_forecast("SOFR", "ewmac8").tail(5))
        print(my_system.forecastScaleCap.get_capped_forecast("SOFR", "ewmac32").tail(5))
        print(my_system.forecastScaleCap.get_forecast_scalar("SOFR", "ewmac32"))
        print(my_system.combForecast.get_combined_forecast("SOFR").tail(5))
        print(my_system.combForecast.get_forecast_weights("SOFR").tail(5))

        print(my_system.positionSize.get_subsystem_position("SOFR").tail(5))

        print(my_system.portfolio.get_notional_position("SOFR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_prebaked_simple_system(self):
        """
        This is the simple system from 'examples.introduction.prebakedsimplesystems'
        """
        my_system = simplesystem()
        print(my_system)
        print(my_system.portfolio.get_notional_position("SOFR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_prebaked_from_confg(self):
        """
        This is the config system from 'examples.introduction.prebakedsimplesystems'
        """
        my_config = Config("systems.provided.example.simplesystemconfig.yaml")
        my_data = csvFuturesSimData()
        my_system = simplesystem(config=my_config, data=my_data)
        print(my_system.portfolio.get_notional_position("SOFR").tail(5))

    @pytest.mark.slow  # will be skipped unless run with 'pytest --runslow'
    def test_prebaked_chapter15(self):
        """
        This is (mostly) the chapter 15 system from 'examples.introduction.prebakedsimplesystems'
        but without graph plotting
        """
        system = base_futures_system()
        print(system.accounts.portfolio().sharpe())

    @staticmethod
    def calc_ewmac_forecast(price, Lfast, Lslow=None):
        """
        Calculate the ewmac trading rule forecast, given a price and EWMA speeds
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
