from systems.stage import SystemStage
from copy import copy

from syscore.objects import resolve_function
from syscore.pdutils import divide_df_single_column


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

    KEY INPUT: system.data.get_instrument_price(instrument_code)
               found in self.get_instrument_price

    KEY OUTPUTS: system.rawdata.... several

    Name: rawdata
    """

    def __init__(self):
        """
        Create a new stage: raw data object

        """

        setattr(self, "name", "rawdata")

    def get_instrument_price(self, instrument_code):
        """
        Gets the instrument price from the parent system.data object

        KEY INPUT

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.get_instrument_price("EDOLLAR").tail(2)
                               price
        2015-12-11 17:08:14  97.9675
        2015-12-11 19:33:39  97.9875
        """
        def _get_instrument_price(system, instrument_code):
            instrprice = system.data.get_instrument_price(instrument_code)
            return instrprice

        instrprice = self.parent.calc_or_cache("instrument_price",
                                               instrument_code,
                                               _get_instrument_price)

        return instrprice

    def daily_prices(self, instrument_code):
        """
        Gets daily prices

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()

        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_prices("EDOLLAR").tail(2)
                      price
        2015-12-10  97.8800
        2015-12-11  97.9875

        """
        def _daily_prices(system, instrument_code, this_stage):
            instrprice = this_stage.get_instrument_price(instrument_code)
            dailyprice = instrprice.resample("1B", how="last")
            return dailyprice

        dailyprice = self.parent.calc_or_cache(
            "daily_price", instrument_code, _daily_prices, self)

        return dailyprice

    def daily_denominator_price(self, instrument_code):
        """
        Gets daily prices for use with % volatility
        This won't always be the same as the normal 'price' which is normally a cumulated total return series

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()

        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_denominator_price("EDOLLAR").head(2)
                        price
        1983-09-26  71.241192
        1983-09-27  71.131192
        """
        def _daily_denominator_returns(system, instrument_code, this_stage):

            dem_returns = this_stage.daily_prices(instrument_code)
            return dem_returns

        dem_returns = self.parent.calc_or_cache(
            "daily_denominator_price", instrument_code, _daily_denominator_returns, self)

        return dem_returns

    def daily_returns(self, instrument_code):
        """
        Gets daily returns (not % returns)

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_returns("EDOLLAR").tail(2)
                     price
        2015-12-10 -0.0650
        2015-12-11  0.1075
        """
        def _daily_returns(system, instrument_code, this_stage):
            instrdailyprice = this_stage.daily_prices(instrument_code)
            dailyreturns = instrdailyprice.diff()
            return dailyreturns

        dailyreturns = self.parent.calc_or_cache(
            "daily_returns", instrument_code, _daily_returns, self)

        return dailyreturns

    def daily_returns_volatility(self, instrument_code):
        """
        Gets volatility of daily returns (not % returns)

        This is done using a user defined function

        We get this from:
          the configuration object
          or if not found, system.defaults.py

        The dict must contain func key; anything else is optional

        KEY OUTPUT

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> ## uses defaults
        >>> system.rawdata.daily_returns_volatility("EDOLLAR").tail(2)
                         vol
        2015-12-10  0.054145
        2015-12-11  0.058522
        >>>
        >>> from sysdata.configdata import Config
        >>> config=Config("systems.provided.example.exampleconfig.yaml")
        >>> system=System([rawdata], data, config)
        >>> system.rawdata.daily_returns_volatility("EDOLLAR").tail(2)
                         vol
        2015-12-10  0.054145
        2015-12-11  0.058522
        >>>
        >>> config=Config(dict(volatility_calculation=dict(func="syscore.algos.robust_vol_calc", days=200)))
        >>> system2=System([rawdata], data, config)
        >>> system2.rawdata.daily_returns_volatility("EDOLLAR").tail(2)
                         vol
        2015-12-10  0.057946
        2015-12-11  0.058626

        """
        def _daily_returns_volatility(system, instrument_code, this_stage):
            dailyreturns = this_stage.daily_returns(instrument_code)

            volconfig=system.config.dict_with_defaults('volatility_calculation', 
                ['func','days','min_periods','vol_abs_min','vol_floor','floor_min_quant',
                 'floor_min_periods','floor_days'])

            # volconfig contains 'func' and some other arguments
            # we turn func which could be a string into a function, and then
            # call it with the other ags
            volfunction = resolve_function(volconfig.pop('func'))
            vol = volfunction(dailyreturns, **volconfig)

            return vol

        vol = self.parent.calc_or_cache(
            "daily_returns_volatility", instrument_code, _daily_returns_volatility, self)

        return vol

    def get_daily_percentage_volatility(self, instrument_code):
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
        >>> system.rawdata.get_daily_percentage_volatility("EDOLLAR").tail(2)
                         vol
        2015-12-10  0.055281
        2015-12-11  0.059789
        """
        def _get_daily_percentage_volatility(
                system, instrument_code, this_stage):
            denom_price = this_stage.daily_denominator_price(instrument_code)
            return_vol = this_stage.daily_returns_volatility(instrument_code)
            perc_vol = 100.0 * \
                divide_df_single_column(return_vol, denom_price.shift(1))

            return perc_vol

        perc_vol = self.parent.calc_or_cache(
            "daily_percentage_volatility", instrument_code, _get_daily_percentage_volatility, self)
        return perc_vol


    def norm_returns(self, instrument_code):
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
        >>> system.rawdata.norm_returns("EDOLLAR").tail(2)
                    norm_return
        2015-12-10    -1.219510
        2015-12-11     1.985413
        """
        def _norm_returns(system, instrument_code, this_stage):
            returnvol = this_stage.daily_returns_volatility(
                instrument_code).shift(1)
            dailyreturns = this_stage.daily_returns(instrument_code)
            norm_return = divide_df_single_column(dailyreturns, returnvol)
            norm_return.columns = ["norm_return"]
            return norm_return

        norm_returns = self.parent.calc_or_cache(
            "_norm_return_dict", instrument_code, _norm_returns, self)

        return norm_returns


if __name__ == '__main__':
    import doctest
    doctest.testmod()
