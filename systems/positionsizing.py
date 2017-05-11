from systems.defaults import system_defaults
from systems.stage import SystemStage
from systems.basesystem import ALL_KEYNAME
from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.algos import robust_vol_calc
from systems.system_cache import input, dont_cache, diagnostic, output


class PositionSizing(SystemStage):
    """
    Stage for position sizing (take combined forecast; turn into subsystem positions)

    KEY INPUTS: a) system.combForecast.get_combined_forecast(instrument_code)
                 found in self.get_combined_forecast

                b) system.rawdata.get_daily_percentage_volatility(instrument_code)
                 found in self.get_price_volatility(instrument_code)

                 If not found, uses system.data.daily_prices to calculate

                c) system.rawdata.daily_denominator_price((instrument_code)
                 found in self.get_instrument_sizing_data(instrument_code)

                If not found, uses system.data.daily_prices

                d)  system.data.get_value_of_block_price_move(instrument_code)
                 found in self.get_instrument_sizing_data(instrument_code)

                e)  system.data.get_fx_for_instrument(instrument_code, base_currency)
                   found in self.get_fx_rate(instrument_code)


    KEY OUTPUT: system.positionSize.get_subsystem_position(instrument_code)

    Name: positionSize
    """

    def _name(self):
        return "positionSize"

    @input
    def get_combined_forecast(self, instrument_code):
        """
        Get the combined forecast from previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system.positionSize.get_combined_forecast("EDOLLAR").tail(2)
                    comb_forecast
        2015-12-10       1.619134
        2015-12-11       2.462610
        """

        return self.parent.combForecast.get_combined_forecast(instrument_code)

    @diagnostic()
    def get_price_volatility(self, instrument_code):
        """
        Get the daily % volatility; If a rawdata stage exists from there; otherwise work it out

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        Note as an exception to the normal rule we cache this, as it sometimes comes from data

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system.positionSize.get_price_volatility("EDOLLAR").tail(2)
                         vol
        2015-12-10  0.055281
        2015-12-11  0.059789
        >>>
        >>> system2=System([ rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system2.positionSize.get_price_volatility("EDOLLAR").tail(2)
                         vol
        2015-12-10  0.055318
        2015-12-11  0.059724
        """
        system = self.parent
        if hasattr(system, "rawdata"):
            daily_perc_vol = system.rawdata.get_daily_percentage_volatility(
                instrument_code)
        else:
            price = system.data.daily_prices(instrument_code)
            return_vol = robust_vol_calc(price.diff())
            daily_perc_vol = 100.0 * return_vol / price

        return daily_perc_vol

    @diagnostic()
    def get_instrument_sizing_data(self, instrument_code):
        """
        Get various things from data and rawdata to calculate position sizes

        KEY INPUT

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: tuple (Tx1 pd.DataFrame: underlying price [as used to work out % volatility],
                              float: value of price block move)

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> ans=system.positionSize.get_instrument_sizing_data("EDOLLAR")
        >>> ans[0].tail(2)
                      price
        2015-12-10  97.8800
        2015-12-11  97.9875
        >>>
        >>> ans[1]
        2500
        >>>
        >>> system=System([rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> ans=system.positionSize.get_instrument_sizing_data("EDOLLAR")
        >>> ans[0].tail(2)
                      price
        2015-12-10  97.8800
        2015-12-11  97.9875
        >>>
        >>> ans[1]
        2500


        """

        if hasattr(self.parent, "rawdata"):
            underlying_price = self.parent.rawdata.daily_denominator_price(
                instrument_code)

        else:
            underlying_price = self.parent.data.daily_prices(instrument_code)

        value_of_price_move = self.parent.data.get_value_of_block_price_move(
            instrument_code)

        return (underlying_price, value_of_price_move)

    @diagnostic()
    def get_daily_cash_vol_target(self):
        """
        Get the daily cash vol target

        Requires: percentage_vol_target, notional_trading_capital, base_currency

        To find these, look in (a) in system.config.parameters...
                (b).... if not found, in systems.get_defaults.py


        :Returns: tuple (str, float): str is base_currency, float is value

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> ## from config
        >>> system.positionSize.get_daily_cash_vol_target()['base_currency']
        'GBP'
        >>>
        >>> ## from defaults
        >>> del(config.base_currency)
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> system.positionSize.get_daily_cash_vol_target()['base_currency']
        'USD'
        >>>

        """

        self.log.msg("Getting vol target")

        system = self.parent
        percentage_vol_target = float(system.config.percentage_vol_target)

        notional_trading_capital = float(
            system.config.notional_trading_capital)

        base_currency = system.config.base_currency

        annual_cash_vol_target = notional_trading_capital * percentage_vol_target / 100.0
        daily_cash_vol_target = annual_cash_vol_target / ROOT_BDAYS_INYEAR

        # FIXME this thing ain't too pretty
        vol_target_dict = dict(
            base_currency=base_currency,
            percentage_vol_target=percentage_vol_target,
            notional_trading_capital=notional_trading_capital,
            annual_cash_vol_target=annual_cash_vol_target,
            daily_cash_vol_target=daily_cash_vol_target)

        return vol_target_dict

    @input
    def get_fx_rate(self, instrument_code):
        """
        Get FX rate to translate instrument volatility into same currency as account value.

        KEY INPUT

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame: fx rate

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system.positionSize.get_fx_rate("EDOLLAR").tail(2)
                          fx
        2015-12-09  0.664311
        2015-12-10  0.660759

        """

        base_currency = self.get_daily_cash_vol_target()['base_currency']
        fx_rate = self.parent.data.get_fx_for_instrument(
            instrument_code, base_currency)

        return fx_rate

    @diagnostic()
    def get_block_value(self, instrument_code):
        """
        Calculate block value for instrument_code

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system.positionSize.get_block_value("EDOLLAR").tail(2)
                       bvalue
        2015-12-10  2447.0000
        2015-12-11  2449.6875
        >>>
        >>> system=System([rules, fcs, comb, PositionSizing()], data, config)
        >>> system.positionSize.get_block_value("EDOLLAR").tail(2)
                       bvalue
        2015-12-10  2447.0000
        2015-12-11  2449.6875

        """

        (underlying_price, value_of_price_move
         ) = self.get_instrument_sizing_data(instrument_code)
        block_value = 0.01 * underlying_price * value_of_price_move
        block_value.columns = ["bvalue"]

        return block_value

    @diagnostic()
    def get_instrument_currency_vol(self, instrument_code):
        """
        Get value of volatility of instrument in instrument's own currency

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system.positionSize.get_instrument_currency_vol("EDOLLAR").tail(2)
                           icv
        2015-12-10  135.272415
        2015-12-11  146.464756
        >>>
        >>> system2=System([ rules, fcs, comb, PositionSizing()], data, config)
        >>> system2.positionSize.get_instrument_currency_vol("EDOLLAR").tail(2)
                           icv
        2015-12-10  135.362246
        2015-12-11  146.304072

        """

        self.log.msg(
            "Calculating instrument currency vol for %s" % instrument_code,
            instrument_code=instrument_code)

        block_value = self.get_block_value(instrument_code)
        daily_perc_vol = self.get_price_volatility(instrument_code)

        (block_value, daily_perc_vol) = block_value.align(
            daily_perc_vol, join="inner")

        instr_ccy_vol = block_value * daily_perc_vol

        return instr_ccy_vol

    @diagnostic()
    def get_instrument_value_vol(self, instrument_code):
        """
        Get value of volatility of instrument in base currency (used for account value)

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system.positionSize.get_instrument_value_vol("EDOLLAR").tail(2)
                          ivv
        2015-12-10  89.382530
        2015-12-11  96.777975
        >>>
        >>> system2=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> system2.positionSize.get_instrument_value_vol("EDOLLAR").tail(2)
                          ivv
        2015-12-10  89.382530
        2015-12-11  96.777975

        """

        self.log.msg(
            "Calculating instrument value vol for %s" % instrument_code,
            instrument_code=instrument_code)

        instr_ccy_vol = self.get_instrument_currency_vol(instrument_code)
        fx_rate = self.get_fx_rate(instrument_code)

        (instr_ccy_vol, fx_rate) = instr_ccy_vol.align(fx_rate)

        instr_value_vol = instr_ccy_vol * fx_rate

        return instr_value_vol

    @diagnostic()
    def get_volatility_scalar(self, instrument_code):
        """
        Get ratio of required volatility vs volatility of instrument in instrument's own currency

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system.positionSize.get_volatility_scalar("EDOLLAR").tail(2)
                    vol_scalar
        2015-12-10   11.187869
        2015-12-11   10.332930
        >>>
        >>> ## without raw data
        >>> system2=System([ rules, fcs, comb, PositionSizing()], data, config)
        >>> system2.positionSize.get_volatility_scalar("EDOLLAR").tail(2)
                    vol_scalar
        2015-12-10   11.180444
        2015-12-11   10.344278
        """

        self.log.msg(
            "Calculating volatility scalar for %s" % instrument_code,
            instrument_code=instrument_code)

        instr_value_vol = self.get_instrument_value_vol(instrument_code)
        cash_vol_target = self.get_daily_cash_vol_target()[
            'daily_cash_vol_target']

        vol_scalar = cash_vol_target / instr_value_vol

        return vol_scalar

    @output()
    def get_subsystem_position(self, instrument_code):
        """
        Get scaled position (assuming for now we trade our entire capital for one instrument)

        KEY OUTPUT

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> system.positionSize.get_subsystem_position("EDOLLAR").tail(2)
                    ss_position
        2015-12-10     1.811465
        2015-12-11     2.544598
        >>>
        >>> system2=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> system2.positionSize.get_subsystem_position("EDOLLAR").tail(2)
                    ss_position
        2015-12-10     1.811465
        2015-12-11     2.544598

        """
        self.log.msg(
            "Calculating subsystem position for %s" % instrument_code,
            instrument_code=instrument_code)
        """
        We don't allow this to be changed in config
        """
        avg_abs_forecast = system_defaults['average_absolute_forecast']

        vol_scalar = self.get_volatility_scalar(instrument_code)
        forecast = self.get_combined_forecast(instrument_code)

        vol_scalar = vol_scalar.reindex(forecast.index).ffill()

        subsystem_position = vol_scalar * forecast / avg_abs_forecast

        return subsystem_position


if __name__ == '__main__':
    import doctest
    doctest.testmod()
