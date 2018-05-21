"""

The starter system has the following features:

- single market
- binary forecast from simple MAV
- exit from trailing stop loss
- fixed positions once in trade

"""
from systems.defaults import system_defaults
from syscore.genutils import sign
from systems.provided.futures_chapter15.basesystem import *
from sysdata.configdata import Config
from systems.forecasting import TradingRule
from systems.positionsizing import PositionSizing
from systems.system_cache import input, dont_cache, diagnostic, output
from syscore.accounting import pandl_with_data

from copy import copy
import numpy as np
import pandas as pd

def simple_mav(price, short=10, long=40, forecast_fixed=10):
    """
    Simple moving average crossover

    :param price:
    :param short: days for short
    :param long: days for short
    :return: binary time series
    """

    short_mav = price.rolling(short, min_periods=1).mean()
    long_mav = price.rolling(long, min_periods=1).mean()

    signal = short_mav - long_mav

    binary = signal.apply(sign)
    binary_position = forecast_fixed * binary

    return binary_position

def stoploss(price, vol, position, Xfactor=4):
    """
    Apply trailing stoploss

    :param price:
    :param vol: eg system.rawdata.daily_returns_volatility("SP500")
    :param position: Raw position series, without stoploss or entry / exit logic
    :return: New position series
    """

    # assume all lined up
    current_position = 0.0
    previous_position = 0.0
    new_position=[]
    price_list_since_position_held=[]

    for iday in range(len(price)):
        current_price = price[iday]

        if current_position == 0.0:
            # no position, check for signal
            original_position_now = position[iday]
            if np.isnan(original_position_now):
                # no signal
                new_position.append(0.0)
                continue
            if original_position_now>0.0 or original_position_now<0.0:
                # potentially going long / short
                # check last position to avoid whipsaw
                if previous_position ==0.0 or sign(original_position_now)!=sign(previous_position):
                    # okay to do this - we don't want to enter a new position unless sign changed
                    # we set the position at the sized position at moment of inception
                    current_position = original_position_now
                    price_list_since_position_held.append(current_price)
                    new_position.append(current_position)
                    continue
            # if we've made it this far then:
            # no signal
            new_position.append(0.0)
            continue

        # already holding a position
        # calculate HWM
        sign_position = sign(current_position)
        price_list_since_position_held.append(current_price)
        current_vol = vol[iday]
        trailing_factor = current_vol * Xfactor

        if sign_position==1:
            # long
            hwm= np.nanmax(price_list_since_position_held)
            threshold = hwm - trailing_factor
            close_trade = current_price<threshold
        else:
            # short
            hwm = np.nanmin(price_list_since_position_held)
            threshold = hwm + trailing_factor
            close_trade = current_price>threshold

        if close_trade:
            previous_position = copy(current_position)
            current_position=0.0
            # note if we don't close the current position is maintained
            price_list_since_position_held=[]

        new_position.append(current_position)

    new_position = pd.DataFrame(new_position, price.index)

    return new_position

class PositionSizeWithStopLoss(PositionSizing):
    @diagnostic()
    def get_subsystem_position_preliminary(self, instrument_code):
        """
        Get scaled position (assuming for now we trade our entire capital for one instrument)

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

    @output()
    def get_subsystem_position(self, instrument_code):
        """
        Get scaled position (assuming for now we trade our entire capital for one instrument)

        """

        Xfactor = self.parent.config.Xfactor
        price = self.parent.rawdata.get_daily_prices(instrument_code)
        vol = self.parent.rawdata.daily_returns_volatility(instrument_code)
        raw_position=self.get_subsystem_position_preliminary(instrument_code)

        subsystem_position = stoploss(price,vol,raw_position,Xfactor)

        return subsystem_position[0]

# number of trades per year
def tradesperyear(x):
    y= x!=x.shift(1)
    totaly=y.sum().values[0]
    years = len(y)/250.0

    return totaly / years


simple_mav_rule=TradingRule(dict(function = simple_mav, other_args=dict(long=40, short=10)))


weights = dict(EDOLLAR=1.0)
config= Config(dict(trading_rules = dict(simple_mav=simple_mav_rule), Xfactor=4, instrument_weights=weights,
                    percentage_vol_target=16.0))

data = csvFuturesSimData()

system = System([
    Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
], data, config)

position=system.positionSize.get_subsystem_position("EDOLLAR")
price=price=system.rawdata.get_daily_prices("EDOLLAR")
#need to hack together another p&l function!!
pandl = system.accounts.pandl_for_subsystem("EDOLLAR")


