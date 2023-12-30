from copy import copy

import pandas as pd

from systems.stage import SystemStage
from syscore.objects import resolve_function
from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.genutils import list_intersection
from syscore.exceptions import missingData
from systems.system_cache import input, diagnostic, output

from sysdata.sim.futures_sim_data import futuresSimData
from sysdata.config.configdata import Config

from sysobjects.carry_data import rawCarryData



from syscore.dateutils import BUSINESS_DAYS_IN_YEAR
#from systems.rawdata_orig import RawData


class RawData(SystemStage):
    """
        A SystemStage that does some fairly common calculations before we do
        forecasting and which gives access to some widely used methods.

            This is optional; forecasts can go straight to system.data
            The advantages of using RawData are:
                   - preliminary calculations that are reused can be cached, to
                     save time (eg volatility)
                   - preliminary calculations are available for inspection when
                     diagnosing what is going on

    Name: rawdata
    """

    @property
    def name(self):
        return "rawdata"

    @property
    def data_stage(self) -> futuresSimData:
        return self.parent.data

    @property
    def config(self) -> Config:
        return self.parent.config

    @input
    def get_daily_prices(self, instrument_code) -> pd.Series:
        """
        Gets daily prices

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT
        """
        self.log.debug(
            "Calculating daily prices for %s" % instrument_code,
            instrument_code=instrument_code,
        )
        dailyprice = self.data_stage.daily_prices(instrument_code)

        if len(dailyprice) == 0:
            raise Exception(
                "Data for %s not found! Remove from instrument list, or add to config.ignore_instruments"
                % instrument_code
            )

        return dailyprice

    @input
    def get_natural_frequency_prices(self, instrument_code: str) -> pd.Series:
        self.log.debug(
            "Retrieving natural prices for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        natural_prices = self.data_stage.get_raw_price(instrument_code)

        if len(natural_prices) == 0:
            raise Exception(
                "Data for %s not found! Remove from instrument list, or add to config.ignore_instruments"
            )

        return natural_prices

    @input
    def get_hourly_prices(self, instrument_code: str) -> pd.Series:
        hourly_prices = self.data_stage.hourly_prices(instrument_code)

        return hourly_prices

    @output()
    def daily_returns(self, instrument_code: str) -> pd.Series:
        """
        Gets daily returns (not % returns)

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame


        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_returns("SOFR").tail(2)
                     price
        2015-12-10 -0.0650
        2015-12-11  0.1075
        """
        instrdailyprice = self.get_daily_prices(instrument_code)
        dailyreturns = instrdailyprice.diff()

        return dailyreturns

    @output()
    def hourly_returns(self, instrument_code: str) -> pd.Series:
        """
        Gets hourly returns (not % returns)

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame


        """
        hourly_prices = self.get_hourly_prices(instrument_code)
        hourly_returns = hourly_prices.diff()

        return hourly_returns

    @output()
    def annualised_returns_volatility(self, instrument_code: str) -> pd.Series:
        daily_returns_volatility = self.daily_returns_volatility(instrument_code)

        return daily_returns_volatility * ROOT_BDAYS_INYEAR

    @output()
    def daily_returns_volatility(self, instrument_code: str) -> pd.Series:
        """
        Gets volatility of daily returns (not % returns)

        This is done using a user defined function

        We get this from:
          the configuration object
          or if not found, system.defaults.py

        The dict must contain func key; anything else is optional

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> ## uses defaults
        >>> system.rawdata.daily_returns_volatility("SOFR").tail(2)
                         vol
        2015-12-10  0.054145
        2015-12-11  0.058522
        >>>
        >>> from sysdata.config.configdata import Config
        >>> config=Config("systems.provided.example.exampleconfig.yaml")
        >>> system=System([rawdata], data, config)
        >>> system.rawdata.daily_returns_volatility("SOFR").tail(2)
                         vol
        2015-12-10  0.054145
        2015-12-11  0.058522
        >>>
        >>> config=Config(dict(volatility_calculation=dict(func="sysquant.estimators.vol.robust_vol_calc", days=200)))
        >>> system2=System([rawdata], data, config)
        >>> system2.rawdata.daily_returns_volatility("SOFR").tail(2)
                         vol
        2015-12-10  0.057946
        2015-12-11  0.058626

        """
        self.log.debug(
            "Calculating daily volatility for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        volconfig = copy(self.config.volatility_calculation)

        which_returns = volconfig.pop("name_returns_attr_in_rawdata")
        returns_func = getattr(self, which_returns)
        price_returns = returns_func(instrument_code)

        # volconfig contains 'func' and some other arguments
        # we turn func which could be a string into a function, and then
        # call it with the other ags
        vol_multiplier = volconfig.pop("multiplier_to_get_daily_vol")

        volfunction = resolve_function(volconfig.pop("func"))
        raw_vol = volfunction(price_returns, **volconfig)

        vol = vol_multiplier * raw_vol

        return vol

    @output()
    def get_daily_percentage_returns(self, instrument_code: str) -> pd.Series:
        """
        Get percentage returns

        Useful statistic, also used for some trading rules

        This is an optional subsystem; forecasts can go straight to system.data
        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame
        """

        # UGLY
        denom_price = self.daily_denominator_price(instrument_code)
        num_returns = self.daily_returns(instrument_code)
        perc_returns = num_returns / denom_price.ffill()

        return perc_returns

    @output()
    def get_daily_percentage_volatility(self, instrument_code: str) -> pd.Series:
        """
        Get percentage returns normalised by recent vol

        Useful statistic, also used for some trading rules

        This is an optional subsystem; forecasts can go straight to system.data
        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.get_daily_percentage_volatility("SOFR").tail(2)
                         vol
        2015-12-10  0.055281
        2015-12-11  0.059789
        """
        denom_price = self.daily_denominator_price(instrument_code)
        return_vol = self.daily_returns_volatility(instrument_code)
        (denom_price, return_vol) = denom_price.align(return_vol, join="right")
        perc_vol = 100.0 * (return_vol / denom_price.ffill().abs())

        return perc_vol

    @diagnostic()
    def get_daily_vol_normalised_returns(self, instrument_code: str) -> pd.Series:
        """
        Get returns normalised by recent vol

        Useful statistic, also used for some trading rules

        This is an optional subsystem; forecasts can go straight to system.data
        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.get_daily_vol_normalised_returns("SOFR").tail(2)
                    norm_return
        2015-12-10    -1.219510
        2015-12-11     1.985413
        """
        self.log.debug(
            "Calculating normalised return for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        returnvol = self.daily_returns_volatility(instrument_code).shift(1)
        dailyreturns = self.daily_returns(instrument_code)
        norm_return = dailyreturns / returnvol

        return norm_return

    @diagnostic()
    def get_cumulative_daily_vol_normalised_returns(
        self, instrument_code: str
    ) -> pd.Series:
        """
        Returns a cumulative normalised return. This is like a price, but with equal expected vol
        Used for a few different trading rules

        :param instrument_code: str
        :return: pd.Series
        """

        self.log.debug(
            "Calculating cumulative normalised return for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        norm_returns = self.get_daily_vol_normalised_returns(instrument_code)

        cum_norm_returns = norm_returns.cumsum()

        return cum_norm_returns

    @diagnostic()
    def _aggregate_daily_vol_normalised_returns_for_list_of_instruments(
        self, list_of_instruments: list
    ) -> pd.Series:
        """
        Average normalised returns across an asset class

        :param asset_class: str
        :return: pd.Series
        """

        aggregate_returns_across_instruments_list = [
            self.get_daily_vol_normalised_returns(instrument_code)
            for instrument_code in list_of_instruments
        ]

        aggregate_returns_across_instruments = pd.concat(
            aggregate_returns_across_instruments_list, axis=1
        )

        # we don't ffill before working out the median as this could lead to
        # bad data
        median_returns = aggregate_returns_across_instruments.median(axis=1)

        return median_returns

    @diagnostic()
    def _daily_vol_normalised_price_for_list_of_instruments(
        self, list_of_instruments: list
    ) -> pd.Series:

        norm_returns = (
            self._aggregate_daily_vol_normalised_returns_for_list_of_instruments(
                list_of_instruments
            )
        )
        norm_price = norm_returns.cumsum()

        return norm_price

    @diagnostic()
    def _by_asset_class_daily_vol_normalised_price_for_asset_class(
        self, asset_class: str
    ) -> pd.Series:
        """
        Price for an asset class, built up from cumulative returns

        :param asset_class: str
        :return: pd.Series
        """

        instruments_in_asset_class = self.all_instruments_in_asset_class(asset_class)

        norm_price = self._daily_vol_normalised_price_for_list_of_instruments(
            instruments_in_asset_class
        )

        return norm_price

    @output()
    def normalised_price_for_asset_class(self, instrument_code: str) -> pd.Series:
        """

        :param instrument_code:
        :return:
        """

        asset_class = self.data_stage.asset_class_for_instrument(instrument_code)
        normalised_price_for_asset_class = (
            self._by_asset_class_daily_vol_normalised_price_for_asset_class(asset_class)
        )
        normalised_price_this_instrument = (
            self.get_cumulative_daily_vol_normalised_returns(instrument_code)
        )

        # Align for an easy life
        # As usual forward fill at last moment
        normalised_price_for_asset_class_aligned = (
            normalised_price_for_asset_class.reindex(
                normalised_price_this_instrument.index
            ).ffill()
        )

        return normalised_price_for_asset_class_aligned

    @diagnostic()
    def rolls_per_year(self, instrument_code: str) -> int:
        ## an input but we cache to avoid spamming with errors
        try:
            rolls_per_year = self.data_stage.get_rolls_per_year(instrument_code)
        except:
            self.log.warning(
                "No roll data for %s, this is fine for spot instruments but not for futures"
                % instrument_code
            )
            rolls_per_year = 0

        return rolls_per_year

    @input
    def get_instrument_raw_carry_data(self, instrument_code: str) -> rawCarryData:
        """
        Returns the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        KEY INPUT


        >>> from systems.tests.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([RawData()], data)
        >>> system.rawdata.get_instrument_raw_carry_data("SOFR").tail(2)
                               PRICE  CARRY CARRY_CONTRACT PRICE_CONTRACT
        2015-12-11 17:08:14  97.9675    NaN         201812         201903
        2015-12-11 19:33:39  97.9875    NaN         201812         201903
        """

        instrcarrydata = self.data_stage.get_instrument_raw_carry_data(instrument_code)
        if len(instrcarrydata) == 0:
            raise missingData(
                "Data for %s not found! Remove from instrument list, or add to config.ignore_instruments"
                % instrument_code
            )

        instrcarrydata = rawCarryData(instrcarrydata)

        return instrcarrydata

    @diagnostic()
    def raw_futures_roll(self, instrument_code: str) -> pd.Series:
        """
        Returns the raw difference between price and carry

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([RawData()], data)
        >>> system.rawdata.raw_futures_roll("SOFR").ffill().tail(2)
        2015-12-11 17:08:14   -0.07
        2015-12-11 19:33:39   -0.07
        dtype: float64
        """

        carrydata = self.get_instrument_raw_carry_data(instrument_code)
        raw_roll = carrydata.raw_futures_roll()

        return raw_roll

    @diagnostic()
    def roll_differentials(self, instrument_code: str) -> pd.Series:
        """
        Work out the annualisation factor

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([RawData()], data)
        >>> system.rawdata.roll_differentials("SOFR").ffill().tail(2)
        2015-12-11 17:08:14   -0.246407
        2015-12-11 19:33:39   -0.246407
        dtype: float64
        """
        carrydata = self.get_instrument_raw_carry_data(instrument_code)
        roll_diff = carrydata.roll_differentials()

        return roll_diff

    @diagnostic()
    def annualised_roll(self, instrument_code: str) -> pd.Series:
        """
        Work out annualised futures roll

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([RawData()], data)
        >>> system.rawdata.annualised_roll("SOFR").ffill().tail(2)
        2015-12-11 17:08:14    0.284083
        2015-12-11 19:33:39    0.284083
        dtype: float64
        >>> system.rawdata.annualised_roll("US10").ffill().tail(2)
        2015-12-11 16:06:35    2.320441
        2015-12-11 17:24:06    2.320441
        dtype: float64

        """

        rolldiffs = self.roll_differentials(instrument_code)
        rawrollvalues = self.raw_futures_roll(instrument_code)

        annroll = rawrollvalues / rolldiffs

        return annroll

    @diagnostic()
    def daily_annualised_roll(self, instrument_code: str) -> pd.Series:
        """
        Resample annualised roll to daily frequency

        We don't resample earlier, or we'll get bad data

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame



        >>> from systems.tests.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([RawData()], data)
        >>> system.rawdata.daily_annualised_roll("SOFR").ffill().tail(2)
        2015-12-10    0.284083
        2015-12-11    0.284083
        Freq: B, dtype: float64
        """

        annroll = self.annualised_roll(instrument_code)
        annroll = annroll.resample("1B").mean()

        return annroll

    @output()
    def raw_carry(self, instrument_code: str) -> pd.Series:
        """
        Returns the raw carry (annualised roll, divided by annualised vol)
        Only thing needed now is smoothing, that is done in the actual trading rule

        Added to rawdata to support relative carry trading rule

        :param instrument_code:

        :return: Tx1 pd.DataFrame
        """

        daily_ann_roll = self.daily_annualised_roll(instrument_code)
        vol = self.daily_returns_volatility(instrument_code)

        ann_stdev = vol * ROOT_BDAYS_INYEAR
        raw_carry = daily_ann_roll / ann_stdev

        return raw_carry

    @output()
    def smoothed_carry(self, instrument_code: str, smooth_days: int = 90) -> pd.Series:
        """
        Returns the smoothed raw carry
        Added to rawdata to support relative carry trading rule

        :param instrument_code:

        :return: Tx1 pd.DataFrame
        """

        raw_carry = self.raw_carry(instrument_code)
        smooth_carry = raw_carry.ewm(smooth_days).mean()

        return smooth_carry

    @diagnostic()
    def _by_asset_class_median_carry_for_asset_class(
        self, asset_class: str, smooth_days: int = 90
    ) -> pd.Series:
        """

        :param asset_class:
        :return:
        """

        instruments_in_asset_class = self.all_instruments_in_asset_class(asset_class)

        raw_carry_across_asset_class = [
            self.raw_carry(instrument_code)
            for instrument_code in instruments_in_asset_class
        ]

        raw_carry_across_asset_class_pd = pd.concat(
            raw_carry_across_asset_class, axis=1
        )

        smoothed_carrys_across_asset_class = raw_carry_across_asset_class_pd.ewm(
            smooth_days
        ).mean()

        # we don't ffill before working out the median as this could lead to
        # bad data
        median_carry = smoothed_carrys_across_asset_class.median(axis=1)

        return median_carry

    @output()
    def median_carry_for_asset_class(self, instrument_code: str) -> pd.Series:
        """
        Median carry for the asset class relating to a given instrument


        :param instrument_code: str
        :return: pd.Series
        """

        asset_class = self.data_stage.asset_class_for_instrument(instrument_code)
        median_carry = self._by_asset_class_median_carry_for_asset_class(asset_class)
        instrument_carry = self.raw_carry(instrument_code)

        # Align for an easy life
        # As usual forward fill at last moment
        median_carry = median_carry.reindex(instrument_carry.index).ffill()

        return median_carry

    # sys.data.get_instrument_asset_classes()

    @output()
    def daily_denominator_price(self, instrument_code: str) -> pd.Series:
        """
        Gets daily prices for use with % volatility
        This won't always be the same as the normal 'price'

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.tests.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([RawData()], data)
        >>>
        >>> system.rawdata.daily_denominator_price("SOFR").ffill().tail(2)
        2015-12-10    97.8800
        2015-12-11    97.9875
        Freq: B, Name: PRICE, dtype: float64
        """
        try:
            prices = self.get_instrument_raw_carry_data(instrument_code).PRICE
        except missingData:
            self.log.warning(
                "No carry data found for %s, using adjusted prices to calculate percentage returns"
                % instrument_code
            )
            return self.get_daily_prices(instrument_code)

        daily_prices = prices.resample("1B").last()

        return daily_prices

    def all_instruments_in_asset_class(self, asset_class: str) -> list:
        instruments_in_asset_class = self.data_stage.all_instruments_in_asset_class(
            asset_class
        )
        instrument_list = self.instrument_list()
        instruments_in_asset_class_and_master_list = list_intersection(
            instruments_in_asset_class, instrument_list
        )

        return instruments_in_asset_class_and_master_list

    def instrument_list(self) -> list:
        instrument_list = self.parent.get_instrument_list()
        return instrument_list
    # thisis where the original was
    """
    A SubSystem that does futures specific raw data calculations

    Name: rawdata
    """

    @output()
    def skew(self, instrument_code, lookback_days=365):
        """
        Return skew over a given time period
        :param instrument_code:
        :param lookback_days: int
        :return: rolling estimator of skew
        """
        lookback = "%dD" % lookback_days
        perc_returns = self.get_daily_percentage_returns(instrument_code)
        skew = perc_returns.rolling(lookback).skew()

        return skew

    @output()
    def neg_skew(self, instrument_code, lookback_days=365):
        """
        Return skew over a given time period
        :param instrument_code:
        :param lookback_days: int
        :return: rolling estimator of skew
        """
        skew = self.skew(instrument_code, lookback_days=lookback_days)

        return -skew

    @output()
    def kurtosis(self, instrument_code, lookback_days=365):
        """
        Returns kurtosis over historic period
        :param instrument_code: str
        :param lookback_days: int
        :return: rolling estimator of kurtosis
        """

        lookback = "%dD" % lookback_days
        perc_returns = self.get_daily_percentage_returns(instrument_code)
        kurtosis = perc_returns.rolling(lookback).kurt()

        return kurtosis

    @output()
    def get_factor_value_for_instrument(
        self, instrument_code, factor_name="skew", **kwargs
    ):
        """
        Returns the factor value for a given instrument
        :param instrument_code: str
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.Series
        """

        try:
            factor_method = getattr(self, factor_name)
        except:
            msg = "Factor %s is not a method in rawdata stage" % factor_name
            self.log.critical(msg)
            raise Exception(msg)

        factor_value = factor_method(instrument_code, **kwargs)

        return factor_value

    @output()
    def average_factor_value_for_instrument(
        self, instrument_code, factor_name="skew", **kwargs
    ):
        """
        Returns the average factor value for a given instrument
        :param instrument_code: str
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.DataFrame
        """
        # Hard coded otherwise **kwargs can get ugly
        span_years = 15
        factor_value = self.get_factor_value_for_instrument(
            instrument_code, factor_name=factor_name, **kwargs
        )
        average_factor_value = factor_value.ewm(
            BUSINESS_DAYS_IN_YEAR * span_years
        ).mean()

        return average_factor_value

    @diagnostic()
    def factor_values_over_instrument_list(
        self, instrument_list, factor_name="skew", **kwargs
    ):
        """
        Return a dataframe with all factor values in instrument list, useful for calculating averages
        :param instrument_list: list of str
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.DataFrame
        """

        all_factor_values = [
            self.get_factor_value_for_instrument(
                instrument_code, factor_name=factor_name, **kwargs
            )
            for instrument_code in instrument_list
        ]
        all_factor_values = pd.concat(all_factor_values, axis=1)
        all_factor_values.columns = instrument_list

        return all_factor_values

    @diagnostic()
    def factor_values_all_instruments(self, factor_name="skew", **kwargs):
        """
        Return a dataframe with all factor values in it, useful for calculating averages
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.DataFrame
        """

        instrument_list = self.parent.get_instrument_list()
        all_factor_values = self.factor_values_over_instrument_list(
            instrument_list, factor_name=factor_name, **kwargs
        )

        return all_factor_values

    @diagnostic()
    def current_average_factor_values_over_all_assets(
        self, factor_name="skew", **kwargs
    ):
        """
        Return the current average of a factor value
        Used for cross sectional averaging, plus also the long run average
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.DataFrame
        """

        all_factor_values = self.factor_values_all_instruments(
            factor_name=factor_name, **kwargs
        )
        cs_average_all_factors = all_factor_values.ffill().mean(axis=1)

        return cs_average_all_factors

    @diagnostic()
    def historic_average_factor_value_all_assets(self, factor_name="skew", **kwargs):
        """
        Average factor value over all assets
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.Series
        """

        # Hard coded otherwise ugly things can happen with **kwargs mismatch
        span_years = 15
        cs_average_all_factors = self.current_average_factor_values_over_all_assets(
            factor_name=factor_name, **kwargs
        )
        historic_average = cs_average_all_factors.ewm(
            BUSINESS_DAYS_IN_YEAR * span_years
        ).mean()

        return historic_average

    @diagnostic()
    def factor_values_over_asset_class(self, asset_class, factor_name="skew", **kwargs):
        """
        Factors value over an asset class
        :param asset_class: str
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.DataFrame
        """

        instrument_list = self.parent.data.all_instruments_in_asset_class(asset_class)
        all_factor_values = self.factor_values_over_instrument_list(
            instrument_list, factor_name=factor_name, **kwargs
        )

        return all_factor_values

    @diagnostic()
    def current_average_factor_value_over_asset_class(
        self, asset_class, factor_name="skew", **kwargs
    ):
        """
        Return the current average of a factor value in an asset class
        Used for cross sectional averaging
        :param asset_class: str
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.Series
        """

        all_factor_values = self.factor_values_over_asset_class(
            asset_class, factor_name=factor_name, **kwargs
        )
        cs_average_all_factors = all_factor_values.ffill().mean(axis=1)

        return cs_average_all_factors

    @diagnostic()
    def average_factor_value_in_asset_class_for_instrument(
        self, instrument_code, factor_name="skew", **kwargs
    ):
        """
        Return the current average of a factor value in an asset class
        Used for cross sectional averaging
        :param instrument_code: str
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.Series
        """

        asset_class = self.parent.data.asset_class_for_instrument(instrument_code)
        current_avg = self.current_average_factor_value_over_asset_class(
            asset_class, factor_name=factor_name, **kwargs
        )

        return current_avg

    @output()
    def get_demeanded_factor_value(
        self,
        instrument_code,
        factor_name="skew",
        demean_method="average_factor_value_for_instrument",
        **kwargs,
    ):
        """
        :param instrument_code: str
        :param factor_name: str
        :param demean_method: str
        :param kwargs: Arguments passed to factor method (directly and via demean method)
        :return: pd.Series
        """
        try:
            assert demean_method in [
                "current_average_factor_values_over_all_assets",
                "historic_average_factor_value_all_assets",
                "average_factor_value_for_instrument",
                "average_factor_value_in_asset_class_for_instrument",
            ]
        except:
            self.log.error("Demeanding method %s is not allowed")

        try:
            demean_function = getattr(self, demean_method)
        except:
            msg = (
                "Demeaning function %s does not exist in rawdata stage" % demean_method
            )
            self.log.critical(msg)
            raise Exception(msg)

        # Get demean value
        if demean_method in [
            "current_average_factor_values_over_all_assets",
            "historic_average_factor_value_all_assets",
        ]:
            # instrument code not needed
            demean_value = demean_function(factor_name=factor_name, **kwargs)
        else:
            demean_value = demean_function(
                instrument_code, factor_name=factor_name, **kwargs
            )

        # Get raw factor value
        factor_value = self.get_factor_value_for_instrument(
            instrument_code, factor_name=factor_name, **kwargs
        )

        # Line them up
        demean_value = demean_value.reindex(factor_value.index)
        demean_value = demean_value.ffill()

        demeaned_value = factor_value - demean_value

        return demeaned_value



if __name__ == "__main__":
    import doctest

    doctest.testmod()
