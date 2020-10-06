import numpy as np
import pandas as pd

from systems.rawdata import RawData
from syscore.dateutils import expiry_diff
from syscore.pdutils import uniquets
from systems.system_cache import input, diagnostic, output
from syscore.dateutils import ROOT_BDAYS_INYEAR, BUSINESS_DAYS_IN_YEAR


class FuturesRawData(RawData):
    """
    A SubSystem that does futures specific raw data calculations

    Name: rawdata
    """

    def __init__(self):
        """
        Create a futures raw data subsystem

        >>> FuturesRawData()
        SystemStage 'rawdata' futures Try objectname.methods()
        """
        super(FuturesRawData, self).__init__()

        setattr(self, "description", "futures")

    @input
    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        KEY INPUT


        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.get_instrument_raw_carry_data("EDOLLAR").tail(2)
                               PRICE  CARRY CARRY_CONTRACT PRICE_CONTRACT
        2015-12-11 17:08:14  97.9675    NaN         201812         201903
        2015-12-11 19:33:39  97.9875    NaN         201812         201903
        """

        instrcarrydata = self.parent.data.get_instrument_raw_carry_data(
            instrument_code)
        return instrcarrydata

    @diagnostic()
    def raw_futures_roll(self, instrument_code):
        """
        Returns the raw difference between price and carry

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.raw_futures_roll("EDOLLAR").ffill().tail(2)
        2015-12-11 17:08:14   -0.07
        2015-12-11 19:33:39   -0.07
        dtype: float64
        """

        carrydata = self.get_instrument_raw_carry_data(instrument_code)
        raw_roll = carrydata.PRICE - carrydata.CARRY

        raw_roll[raw_roll == 0] = np.nan

        raw_roll = uniquets(raw_roll)

        return raw_roll

    @diagnostic()
    def roll_differentials(self, instrument_code):
        """
        Work out the annualisation factor

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.roll_differentials("EDOLLAR").ffill().tail(2)
        2015-12-11 17:08:14   -0.246407
        2015-12-11 19:33:39   -0.246407
        dtype: float64
        """
        carrydata = self.get_instrument_raw_carry_data(instrument_code)
        roll_diff = carrydata.apply(expiry_diff, 1)

        roll_diff = uniquets(roll_diff)

        return roll_diff

    @diagnostic()
    def annualised_roll(self, instrument_code):
        """
        Work out annualised futures roll

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.annualised_roll("EDOLLAR").ffill().tail(2)
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
    def daily_annualised_roll(self, instrument_code):
        """
        Resample annualised roll to daily frequency

        We don't resample earlier, or we'll get bad data

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame



        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.daily_annualised_roll("EDOLLAR").ffill().tail(2)
        2015-12-10    0.284083
        2015-12-11    0.284083
        Freq: B, dtype: float64
        """

        annroll = self.annualised_roll(instrument_code)
        annroll = annroll.resample("1B").mean()
        return annroll

    @output()
    def raw_carry(self, instrument_code):
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
    def smoothed_carry(self, instrument_code, smooth_days=90):
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
    def _by_asset_class_median_carry_for_asset_class(self, asset_class):
        """

        :param asset_class:
        :return:
        """

        instruments_in_asset_class = self.parent.data.all_instruments_in_asset_class(
            asset_class)

        smoothed_carry_across_asset_class = [
            self.smoothed_carry(instrument_code)
            for instrument_code in instruments_in_asset_class
        ]

        smoothed_carry_across_asset_class = pd.concat(
            smoothed_carry_across_asset_class, axis=1
        )

        # we don't ffill before working out the median as this could lead to
        # bad data
        median_carry = smoothed_carry_across_asset_class.median(axis=1)

        return median_carry

    @output()
    def median_carry_for_asset_class(self, instrument_code):
        """
        Median carry for the asset class relating to a given instrument


        :param instrument_code: str
        :return: pd.Series
        """

        asset_class = self.parent.data.asset_class_for_instrument(
            instrument_code)
        median_carry = self._by_asset_class_median_carry_for_asset_class(
            asset_class)
        instrument_carry = self.smoothed_carry(instrument_code)

        # Align for an easy life
        # As usual forward fill at last moment
        median_carry = median_carry.reindex(instrument_carry.index).ffill()

        return median_carry

    # sys.data.get_instrument_asset_classes()

    @output()
    def daily_denominator_price(self, instrument_code):
        """
        Gets daily prices for use with % volatility
        This won't always be the same as the normal 'price'

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>>
        >>> system.rawdata.daily_denominator_price("EDOLLAR").ffill().tail(2)
        2015-12-10    97.8800
        2015-12-11    97.9875
        Freq: B, Name: PRICE, dtype: float64
        """
        prices = self.get_instrument_raw_carry_data(instrument_code).PRICE
        daily_prices = prices.resample("1B").last()
        return daily_prices

    @output()
    def skew(self, instrument_code, lookback_days=365):
        """
        Return skew over a given time period


        :param instrument_code:
        :param lookback_days: int
        :return: rolling estimator of skew
        """
        lookback = "%dD" % lookback_days
        perc_returns = self.get_percentage_returns(instrument_code)
        skew = perc_returns.rolling(lookback).skew()

        return skew

    @output()
    def neg_skew(self, instrument_code, lookback_days=365):
        """
        Return negative skew over a given time period


        :param instrument_code:
        :param lookback_days: int
        :return: rolling estimator of skew
        """
        skew = self.skew(instrument_code, lookback_days=lookback_days)
        neg_skew = -skew

        return neg_skew

    @output()
    def kurtosis(self, instrument_code, lookback_days=365):
        """
        Returns kurtosis over historic period

        :param instrument_code: str
        :param lookback_days: int
        :return: rolling estimator of kurtosis
        """

        lookback = "%dD" % lookback_days
        perc_returns = self.get_percentage_returns(instrument_code)
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
        except BaseException:
            self.log.error("Factor %s is not a method in rawdata stage")

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
    def historic_average_factor_value_all_assets(
            self, factor_name="skew", **kwargs):
        """
        Average factor value over all assets

        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.Series
        """

        # Hard coded otherwise ugly things can happen with **kwargs mismatch
        span_years = 15
        cs_average_all_factors = self.current_average_factor_values_over_all_assets(
            factor_name=factor_name, **kwargs)
        historic_average = cs_average_all_factors.ewm(
            BUSINESS_DAYS_IN_YEAR * span_years
        ).mean()

        return historic_average

    @diagnostic()
    def factor_values_over_asset_class(
            self,
            asset_class,
            factor_name="skew",
            **kwargs):
        """
        Factors value over an asset class

        :param asset_class: str
        :param factor_name: str, points to method in rawdata
        :param **kwargs: passed to factor_name method
        :return: pd.DataFrame
        """

        instrument_list = self.parent.data.all_instruments_in_asset_class(
            asset_class)
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

        asset_class = self.parent.data.asset_class_for_instrument(
            instrument_code)
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
        **kwargs
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
        except BaseException:
            self.log.error("Demeanding method %s is not allowed")

        try:
            demean_function = getattr(self, demean_method)
        except BaseException:
            self.log.error(
                "Demeaning function %s does not exist in rawdata stage")

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
