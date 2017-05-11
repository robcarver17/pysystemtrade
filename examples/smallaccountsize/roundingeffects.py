"""
rounding effects
"""

# Need a binary / thresholder

from systems.portfolio import PortfoliosFixed
from systems.forecast_combine import ForecastCombineFixed, apply_cap, multiply_df
import pandas as pd
from sysdata.csvdata import csvFuturesData


class ForecastWithBinary(ForecastCombineFixed):
    def get_combined_forecast(self, instrument_code):
        def _get_combined_forecast(system, instrument_code, this_stage):
            this_stage.log.msg(
                "Calculating combined forecast for %s" % (instrument_code),
                instrument_code=instrument_code)

            forecast_weights = this_stage.get_forecast_weights(instrument_code)
            rule_variation_list = list(forecast_weights.columns)

            forecasts = this_stage.get_all_forecasts(instrument_code,
                                                     rule_variation_list)
            forecast_div_multiplier = this_stage.get_forecast_diversification_multiplier(
                instrument_code)
            forecast_cap = this_stage.get_forecast_cap()

            # multiply weights by forecasts
            combined_forecast = multiply_df(forecast_weights, forecasts)

            # sum
            combined_forecast = combined_forecast.sum(
                axis=1).to_frame("comb_forecast")

            # apply fdm
            # (note in this simple version we aren't adjusting FDM if forecast_weights change)
            forecast_div_multiplier = forecast_div_multiplier.reindex(
                forecasts.index, method="ffill")
            raw_combined_forecast = multiply_df(combined_forecast,
                                                forecast_div_multiplier)

            combined_forecast = apply_cap(raw_combined_forecast, forecast_cap)

            combined_forecast[combined_forecast > 0.0] = 10.0
            combined_forecast[combined_forecast < 0.0] = 10.0

            return combined_forecast

        combined_forecast = self.parent.calc_or_cache(
            'get_combined_forecast', instrument_code, _get_combined_forecast,
            self)
        return combined_forecast


class ForecastWithThreshold(ForecastCombineFixed):
    def get_combined_forecast(self, instrument_code):
        def _get_combined_forecast(system, instrument_code, this_stage):
            this_stage.log.msg(
                "Calculating combined forecast for %s" % (instrument_code),
                instrument_code=instrument_code)

            forecast_weights = this_stage.get_forecast_weights(instrument_code)
            rule_variation_list = list(forecast_weights.columns)

            forecasts = this_stage.get_all_forecasts(instrument_code,
                                                     rule_variation_list)
            forecast_div_multiplier = this_stage.get_forecast_diversification_multiplier(
                instrument_code)
            forecast_cap = this_stage.get_forecast_cap()

            # multiply weights by forecasts
            combined_forecast = multiply_df(forecast_weights, forecasts)

            # sum
            combined_forecast = combined_forecast.sum(
                axis=1).to_frame("comb_forecast")

            # apply fdm
            # (note in this simple version we aren't adjusting FDM if forecast_weights change)
            forecast_div_multiplier = forecast_div_multiplier.reindex(
                forecasts.index, method="ffill")
            raw_combined_forecast = multiply_df(combined_forecast,
                                                forecast_div_multiplier)

            def map_forecast_value(x):
                x = float(x)
                if x < -20.0:
                    return -30.0
                if x >= -20.0 and x < -10.0:
                    return -(abs(x) - 10.0) * 3
                if x >= -10.0 and x <= 10.0:
                    return 0.0
                if x > 10.0 and x <= 20.0:
                    return (abs(x) - 10.0) * 3
                return 30.0

            combined_forecast = pd.DataFrame(
                [map_forecast_value(x)
                 for x in combined_forecast.values], combined_forecast.index)

            return combined_forecast

        combined_forecast = self.parent.calc_or_cache(
            'get_combined_forecast', instrument_code, _get_combined_forecast,
            self)
        return combined_forecast


'''
Created on 4 Mar 2016

@author: rob
'''

from systems.provided.futures_chapter15.estimatedsystem import PortfoliosEstimated
from systems.provided.futures_chapter15.basesystem import *
from syscore.correlations import get_avg_corr
from copy import copy
import numpy as np

data = csvFuturesData()
all_instruments = data.keys()

config = Config("examples.smallaccountsize.smallaccount.yaml")

all_accounts = []
for instrument_code in all_instruments:

    config.instruments = [instrument_code]

    system1 = System([
        Account(), PortfoliosEstimated(), PositionSizing(), FuturesRawData(),
        ForecastCombineFixed(), ForecastScaleCapFixed(), Rules()
    ], csvFuturesData(), config)

    system1.set_logging_level("on")

    max_position = float(
        system1.positionSize.get_volatility_scalar(instrument_code).mean() *
        2.0)

    original_capital = system1.config.notional_trading_capital

    accounts_this_instr = []
    for target_max in [1.0, 2.0, 3.0, 4.0]:

        # reset trading capital
        config = system1.config
        config.use_SR_costs = False
        config.notional_trading_capital = original_capital * target_max / max_position

        system1 = System([
            Account(), PortfoliosFixed(), PositionSizing(), FuturesRawData(),
            ForecastCombineFixed(), ForecastScaleCapFixed(), Rules()
        ], csvFuturesData(), config)

        system1.set_logging_level("on")

        system1_rounded = system1.accounts.portfolio(roundpositions=True)
        system1_unrounded = system1.accounts.portfolio(roundpositions=False)

        system2 = System([
            Account(), PortfoliosFixed(), PositionSizing(), FuturesRawData(),
            ForecastWithBinary(), ForecastScaleCapFixed(), Rules()
        ], csvFuturesData(), config)

        system2.set_logging_level("on")

        system2_rounded = system2.accounts.portfolio(roundpositions=True)
        system2_unrounded = system2.accounts.portfolio(roundpositions=False)

        system3 = System([
            Account(), PortfoliosFixed(), PositionSizing(), FuturesRawData(),
            ForecastWithThreshold(), ForecastScaleCapFixed(), Rules()
        ], csvFuturesData(), config)

        system3.set_logging_level("on")

        system3_rounded = system3.accounts.portfolio(roundpositions=True)
        system3_unrounded = system3.accounts.portfolio(roundpositions=False)

        accounts_this_instr.append([
            system1_rounded, system1_unrounded, system2_rounded,
            system2_unrounded, system3_rounded, system3_unrounded
        ])

    all_accounts.append(accounts_this_instr)

targetref = 2  # 0 is 1.0 target_max etc

acc_names = [
    "Arbitrary, unrounded", "Binary, unrounded", "Threshold, unrounded",
    "Arbitrary, round", "Binary, round", "Threshold, round"
]

allaccresults = dict(gross=[], net=[], costs=[], vol=[], SR=[], maxstd=[])
allstackresults = dict(gross=[], net=[], costs=[], vol=[], SR=[])

for accref in [1, 3, 5, 0, 2, 4]:  # 0 is system1_rounded and so on

    allresults_gross = []
    allresults_net = []
    allresults_costs = []
    allresults_vol = []
    allresults_sr = []
    allresults_max_std = []

    allstacknet = []
    allstackcosts = []
    allstackgross = []

    for (instridx, instrument_code) in enumerate(all_instruments):
        allresults_gross.append(
            all_accounts[instridx][targetref][accref].gross.weekly.ann_mean())
        allresults_net.append(
            all_accounts[instridx][targetref][accref].net.weekly.ann_mean())
        allresults_costs.append(
            all_accounts[instridx][targetref][accref].costs.weekly.ann_mean())
        allresults_vol.append(
            all_accounts[instridx][targetref][accref].net.weekly.ann_std())
        allresults_max_std.append(
            float(
                pd.rolling_std(
                    all_accounts[instridx][targetref][accref]
                    .net.weekly.as_df(),
                    26,
                    min_periods=4,
                    center=True).max()) * (52**.5))

        try:
            sharpe = all_accounts[instridx][targetref][
                accref].net.weekly.ann_mean() / all_accounts[instridx][
                    targetref][accref].net.weekly.ann_std()

        except ZeroDivisionError:
            sharpe = np.nan

        allresults_sr.append(sharpe)

        allstacknet.append(
            list(all_accounts[instridx][targetref][accref]
                 .net.weekly.iloc[:, 0].values))
        allstackcosts.append(
            list(all_accounts[instridx][targetref][accref]
                 .costs.weekly.iloc[:, 0].values))
        allstackgross.append(
            list(all_accounts[instridx][targetref][accref]
                 .gross.weekly.iloc[:, 0].values))

    allstacknet = sum(allstacknet, [])
    allstackgross = sum(allstackgross, [])
    allstackcosts = sum(allstackcosts, [])

    allaccresults['gross'].append(np.mean(allresults_gross))
    allaccresults['net'].append(np.mean(allresults_net))
    allaccresults['costs'].append(np.mean(allresults_costs))
    allaccresults['vol'].append(np.mean(allresults_vol))
    allaccresults['SR'].append(np.nanmean(allresults_sr))
    allaccresults['maxstd'].append(np.nanmean(allresults_max_std))

    #allstacknet=[x for x in allstacknet if not x==0.0]
    #allstackgross=[x for x in allstacknet if not x==0.0]
    #allstackcosts=[x for x in allstackcosts if not x==0.0]

    allstackresults['gross'].append(np.nanmean(allstackgross) * 52)
    allstackresults['net'].append(np.nanmean(allstacknet) * 52)
    allstackresults['costs'].append(np.nanmean(allstackcosts) * 52)
    allstackresults['vol'].append(np.nanstd(allstacknet) * (52**.5))
    allstackresults['SR'].append(
        np.nanmean(allstacknet) * (52**.5) / np.nanstd(allstacknet))
