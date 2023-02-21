import pandas as pd


from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.constants import missing_data

from sysdata.config.configdata import Config
from sysdata.sim.sim_data import simData
from sysquant.estimators.vol import robust_vol_calc

from systems.buffering import (
    calculate_buffers,
    calculate_actual_buffers,
    apply_buffers_to_position,
)
from systems.stage import SystemStage
from systems.system_cache import input, diagnostic, output
from systems.forecast_combine import ForecastCombine
from systems.rawdata import RawData


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

    @property
    def name(self):
        return "positionSize"

    @output()
    def get_buffers_for_subsystem_position(self, instrument_code: str) -> pd.Series:
        """
        Get buffers for subsystem

        """

        position = self.get_subsystem_position(instrument_code)
        buffer = self.get_subsystem_buffers(instrument_code)

        pos_buffers = apply_buffers_to_position(position=position, buffer=buffer)

        return pos_buffers

    @diagnostic()
    def get_subsystem_buffers(self, instrument_code: str) -> pd.Series:

        position = self.get_subsystem_position(instrument_code)

        vol_scalar = self.get_volatility_scalar(instrument_code)
        log = self.log
        config = self.config

        buffer = calculate_buffers(
            instrument_code=instrument_code,
            position=position,
            log=log,
            config=config,
            vol_scalar=vol_scalar,
        )

        return buffer

    @output()
    def get_subsystem_position(self, instrument_code: str) -> pd.Series:
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
            instrument_code=instrument_code,
        )
        """
        We don't allow this to be changed in config
        """

        avg_abs_forecast = self.avg_abs_forecast()
        vol_scalar = self.get_volatility_scalar(instrument_code)
        forecast = self.get_combined_forecast(instrument_code)

        vol_scalar = vol_scalar.reindex(forecast.index, method="ffill")

        subsystem_position_raw = vol_scalar * forecast / avg_abs_forecast
        subsystem_position = self._apply_long_only_constraint_to_position(
            position=subsystem_position_raw, instrument_code=instrument_code
        )

        return subsystem_position

    def _apply_long_only_constraint_to_position(
        self, position: pd.Series, instrument_code: str
    ) -> pd.Series:
        instrument_long_only = self._is_instrument_long_only(instrument_code)
        if instrument_long_only:
            position[position < 0.0] = 0.0

        return position

    @diagnostic()
    def _is_instrument_long_only(self, instrument_code: str) -> bool:
        list_of_long_only_instruments = self._get_list_of_long_only_instruments()

        return instrument_code in list_of_long_only_instruments

    @diagnostic()
    def _get_list_of_long_only_instruments(self) -> list:
        config = self.config
        long_only = config.get_element_or_missing_data("long_only_instruments")
        if long_only is missing_data:
            return []

        return long_only

    def avg_abs_forecast(self) -> float:
        return self.config.average_absolute_forecast

    @property
    def config(self) -> Config:
        return self.parent.config

    @diagnostic()
    def get_volatility_scalar(self, instrument_code: str) -> pd.Series:
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
            instrument_code=instrument_code,
        )

        instr_value_vol = self.get_instrument_value_vol(instrument_code)
        cash_vol_target = self.get_daily_cash_vol_target()

        vol_scalar = cash_vol_target / instr_value_vol

        return vol_scalar

    @diagnostic()
    def get_instrument_value_vol(self, instrument_code: str) -> pd.Series:
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
            instrument_code=instrument_code,
        )

        instr_ccy_vol = self.get_instrument_currency_vol(instrument_code)
        fx_rate = self.get_fx_rate(instrument_code)

        fx_rate = fx_rate.reindex(instr_ccy_vol.index, method="ffill")

        instr_value_vol = instr_ccy_vol.ffill() * fx_rate

        return instr_value_vol

    @diagnostic()
    def get_instrument_currency_vol(self, instrument_code: str) -> pd.Series:
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
            instrument_code=instrument_code,
        )

        block_value = self.get_block_value(instrument_code)
        daily_perc_vol = self.get_price_volatility(instrument_code)

        ## FIXME WHY NOT RESAMPLE?
        (block_value, daily_perc_vol) = block_value.align(daily_perc_vol, join="inner")

        instr_ccy_vol = block_value.ffill() * daily_perc_vol

        return instr_ccy_vol

    @diagnostic()
    def get_block_value(self, instrument_code: str) -> pd.Series:
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

        underlying_price = self.get_underlying_price(instrument_code)
        value_of_price_move = self.parent.data.get_value_of_block_price_move(
            instrument_code
        )

        block_value = underlying_price.ffill() * value_of_price_move * 0.01

        return block_value

    @diagnostic()
    def get_underlying_price(self, instrument_code: str) -> pd.Series:
        """
        Get various things from data and rawdata to calculate position sizes

        KEY INPUT

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame: underlying price [as used to work out % volatility],

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> ans=system.positionSize.get_underlying_price("EDOLLAR")
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
        >>> ans=system.positionSize.get_underlying_price("EDOLLAR")
        >>> ans[0].tail(2)
                      price
        2015-12-10  97.8800
        2015-12-11  97.9875
        >>>
        >>> ans[1]
        2500


        """
        rawdata = self.rawdata_stage
        if rawdata is missing_data:
            underlying_price = self.data.daily_prices(instrument_code)
        else:
            underlying_price = self.rawdata_stage.daily_denominator_price(
                instrument_code
            )

        return underlying_price

    @property
    def rawdata_stage(self) -> RawData:
        rawdata_stage = getattr(self.parent, "rawdata", missing_data)

        return rawdata_stage

    @property
    def data(self) -> simData:
        return self.parent.data

    @input
    def get_price_volatility(self, instrument_code: str) -> pd.Series:
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

        daily_perc_vol = self.rawdata_stage.get_daily_percentage_volatility(
            instrument_code
        )

        return daily_perc_vol

    @diagnostic()
    def get_vol_target_dict(self) -> dict:
        # FIXME UGLY REPLACE WITH COMPONENTS
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
        >>> system.positionSize.get_vol_target_dict()['base_currency']
        'GBP'
        >>>
        >>> ## from defaults
        >>> del(config.base_currency)
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> system.positionSize.get_vol_target_dict()['base_currency']
        'USD'
        >>>

        """

        self.log.msg("Getting vol target")

        percentage_vol_target = self.get_percentage_vol_target()

        notional_trading_capital = self.get_notional_trading_capital()

        base_currency = self.get_base_currency()

        annual_cash_vol_target = self.annual_cash_vol_target()
        daily_cash_vol_target = self.get_daily_cash_vol_target()

        vol_target_dict = dict(
            base_currency=base_currency,
            percentage_vol_target=percentage_vol_target,
            notional_trading_capital=notional_trading_capital,
            annual_cash_vol_target=annual_cash_vol_target,
            daily_cash_vol_target=daily_cash_vol_target,
        )

        return vol_target_dict

    @diagnostic()
    def get_daily_cash_vol_target(self) -> float:
        annual_cash_vol_target = self.annual_cash_vol_target()
        daily_cash_vol_target = annual_cash_vol_target / ROOT_BDAYS_INYEAR

        return daily_cash_vol_target

    @diagnostic()
    def annual_cash_vol_target(self) -> float:
        notional_trading_capital = self.get_notional_trading_capital()
        percentage_vol_target = self.get_percentage_vol_target()

        annual_cash_vol_target = (
            notional_trading_capital * percentage_vol_target / 100.0
        )

        return annual_cash_vol_target

    @diagnostic()
    def get_notional_trading_capital(self) -> float:
        notional_trading_capital = float(self.config.notional_trading_capital)
        return notional_trading_capital

    @diagnostic()
    def get_percentage_vol_target(self):
        return float(self.config.percentage_vol_target)

    @diagnostic()
    def get_base_currency(self) -> str:
        base_currency = self.config.base_currency
        return base_currency

    @input
    def get_fx_rate(self, instrument_code: str) -> pd.Series:
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

        base_currency = self.get_base_currency()
        fx_rate = self.data.get_fx_for_instrument(instrument_code, base_currency)

        return fx_rate

    @input
    def get_combined_forecast(self, instrument_code: str) -> pd.Series:
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

        return self.comb_forecast_stage.get_combined_forecast(instrument_code)

    @property
    def comb_forecast_stage(self) -> ForecastCombine:
        return self.parent.combForecast


if __name__ == "__main__":
    import doctest

    doctest.testmod()
