import wandb
import pandas as pd
import plotly.express as px
from omegaconf import DictConfig, OmegaConf
from pathlib import Path
import hydra

from typing import List

from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.forecast_scale_cap import ForecastScaleCap
from systems.rawdata import RawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.accounts.accounts_stage import Account

def make_px_line_plot(data: pd.core.frame.DataFrame, title: str, yaxis_title: str):
    
    plot = px.line(data, title=title)
    plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = yaxis_title,
        showlegend=False
    )
    
    return plot

def make_px_ncg_bar(data: pd.core.frame.DataFrame, title: str, yaxis_title: str):
    
    data['costs'] = 1.0 * data['costs']
    plot = px.bar(data, y=["gross", "costs"], title=title)
    plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = yaxis_title,
        showlegend=False
    )
    
    return plot

class Workspace:
    
    def __init__(self, cfg):
        
        # Setup dir configs
        self.work_dir = Path.cwd()
        self.log_dir = cfg.log_dir
        self.cfg = cfg

        # Make system and load data
        rules_config = OmegaConf.to_container(self.cfg.trading_rules)
        rules = Rules(rules_config)
        data = csvFuturesSimData()
        dict_config = OmegaConf.to_container(self.cfg)
        config = Config(dict_config)
        
        self.system = System(
            [
                Account(),
                Portfolios(),
                PositionSizing(),
                RawData(),
                ForecastCombine(),
                ForecastScaleCap(),
                rules,
            ],
            data,
            config
        )
        
        if self.cfg.use_wandb:
            wandb.init(
                project="SystemTrade",
                name="server/system-test",
                config=self.system.config.as_dict()
            )
        
    def backtest(self):
        
        # -- Breakdown of portfolio --
        
        # Forecast Variability
        comb_forecasts = {}
        for instrument in self.system.get_instrument_list():
            comb_forecasts[instrument] = self.system.combForecast.get_combined_forecast(instrument)
        comb_forecasts_df = pd.concat(comb_forecasts.values(), axis=1, keys=comb_forecasts.keys(), join='inner')
        comb_forecast_plot = make_px_line_plot(data=comb_forecasts_df, title='Combined Expected Variability', yaxis_title='Variability [-]')
        if self.cfg.use_wandb:
            wandb.log({"forecast/comb_forecast": wandb.Plotly(comb_forecast_plot)})
        
        
        # -- Volatility targeting --
        # Rule weight estimates
        for instrument in self.system.get_instrument_list():
            rule_weights = self.system.combForecast.get_forecast_weights(instrument)
            weights_plot = make_px_line_plot(data=rule_weights, title=f'{instrument} Rule Weights', yaxis_title='Weight Fraction [-]')
            if self.cfg.use_wandb:
                wandb.log({"forecast/rule_weights": wandb.Plotly(weights_plot)}) 
            
        # Instrument diversification estimates
        diversification = {}
        for instrument in self.system.get_instrument_list():
            rule_weights = self.system.combForecast.get_forecast_diversification_multiplier(instrument)
            diversification[instrument] = rule_weights
        diversification_df = pd.concat(diversification.values(), axis=1, keys=diversification.keys(), join = 'inner')
        diversification_plot = make_px_line_plot(diversification_df, title='Instrument Diversification', yaxis_title='IDF [-]')
        if self.cfg.use_wandb:
            wandb.log({"forecast/diversification": wandb.Plotly(diversification_plot)})
        
        # -- Position sizing --
        # Size of each instrument
        # Plot positions and notional 
        
        notional_positions = {}
        position_sizes = {}
        for instrument in self.system.get_instrument_list():
            notional_positions[instrument] = self.system.portfolio.get_notional_position(instrument)
            position_sizes[instrument] = self.system.positionSize.get_subsystem_position(instrument)

        notional_df = pd.concat(notional_positions.values(), axis=1, keys=notional_positions.keys(), join = 'inner')
        notional_plot = make_px_line_plot(data=notional_df, title='Notional Positions', yaxis_title='Notional Position [USD]')
        if self.cfg.use_wandb:
            wandb.log({"portfolio/notional_plot": wandb.Plotly(notional_plot)})
        
        position_df = pd.concat(position_sizes.values(), axis=1, keys=position_sizes.keys(), join = 'inner') 
        position_plot = make_px_line_plot(data=position_df, title='Position for subsystem', yaxis_title='Position [USD]')
        if self.cfg.use_wandb:
            wandb.log({"portfolio/position_plot": wandb.Plotly(position_plot)})
        
        # Instrument weights
        weights = self.system.accounts.instrument_weights()
        weights_plot = make_px_line_plot(weights, title='System Weights', yaxis_title='[-]')
        if self.cfg.use_wandb:
            wandb.log({"portfolio/instrument_weights": wandb.Plotly(weights_plot)})
        
        # Rule weights
        
        # -- Generalized run performance --
        # Summary statistics for portfolio
        portfolio = self.system.accounts.portfolio()
        summary_stats = portfolio.percent.stats()
        for stat in summary_stats[0]:
            if self.cfg.use_wandb:
                wandb.run.summary[stat[0]] = stat[1]
        
        roll_ann_plot = make_px_line_plot(portfolio.percent.rolling_ann_std(), title='Rolling Annualized Volatility', yaxis_title='Vol [%]')
        gross_plot = make_px_line_plot(portfolio.percent.gross.curve(), title='Gross', yaxis_title='Profit [%]')
        drawdown_plot = make_px_line_plot(portfolio.percent.drawdown(), title='Drawdown', yaxis_title='Drawdown [%]')
        
        if self.cfg.use_wandb:
            wandb.log({"portfolio/rolling_ann_std": wandb.Plotly(roll_ann_plot),
                    "portfolio/accumulated_returns": wandb.Plotly(gross_plot),
                    "portfolio/drawdown": wandb.Plotly(drawdown_plot)})
        
        # Log trading rule performance across all instruments
        # What does each rule do in this portfolio?
        rule_performance = self.system.accounts.pandl_for_all_trading_rules()
        for key in self.system.config.trading_rules.keys():
            ncg = rule_performance[key].percent.annual.to_ncg_frame()
            ncg_plot = make_px_ncg_bar(ncg, title=key, yaxis_title='%')
            if self.cfg.use_wandb:
                wandb.log({f"rule/{key}": wandb.Plotly(ncg_plot)})
        
        # Log portfolio contribution of each instrument
        # What does this instrument do?
        for instrument in self.system.get_instrument_list():
            price = self.system.data.get_raw_price(instrument)
            price_plot = make_px_line_plot(price, title=f'{instrument}', yaxis_title='Price')
            if self.cfg.use_wandb:
                wandb.log({f"prices/{instrument}": wandb.Plotly(price_plot)})
            acc_curve = self.system.accounts.pandl_for_instrument(instrument)
            ncg = acc_curve.percent.annual.to_ncg_frame()
            ncg_plot = make_px_ncg_bar(ncg, title='Net/Cost/Gross', yaxis_title='%')
            if self.cfg.use_wandb:
                wandb.log({f"instrument/{instrument}": wandb.Plotly(ncg_plot)})
        
        # Log isolated instrument/rules, mainly to understand what each rule is upto 
        # How do each of the rules behave?
        
        if self.cfg.use_wandb:
            wandb.finish()


@hydra.main(config_path='pysystemtrade/examples/visualize/configs/.', config_name='system')
def main(cfg):
    from system.wandbtest import Workspace as W
    workspace = W(cfg)
    workspace.backtest()
    

if __name__=="__main__":
    main()