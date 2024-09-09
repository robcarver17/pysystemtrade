import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly_resampler import FigureResampler, FigureWidgetResampler
from plotly.subplots import make_subplots
from omegaconf import DictConfig, OmegaConf
from pathlib import Path
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import hydra

from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.provided.attenuate_vol.vol_attenuation_forecast_scale_cap import volAttenForecastScaleCap
from systems.provided.rob_system.rawdata import myFuturesRawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.provided.dynamic_small_system_optimise.optimised_positions_stage import optimisedPositions
from systems.risk import Risk
from systems.accounts.accounts_stage import Account
from systems.provided.dynamic_small_system_optimise.accounts_stage import accountForOptimisedStage


class AppData:
    
    def __init__(self, cfg):
        
        # Setup dir and configs
        self.work_dir = Path.cwd()
        self.cfg = cfg

        
        # Make system and load data
        rules_config = OmegaConf.to_container(self.cfg.trading_rules)
        rules = Rules(rules_config)
        data = csvFuturesSimData()
        dict_config = OmegaConf.to_container(self.cfg)
        config = Config(dict_config)

        self.system = System(
            [
                Risk(),
                accountForOptimisedStage(),
                optimisedPositions(),
                Portfolios(),
                PositionSizing(),
                myFuturesRawData(),
                ForecastCombine(),
                volAttenForecastScaleCap(),
                rules,
            ],
            data,
            config,
        )
        
        if self.cfg.load_model:
            print(f"Loading pickled model from {self.cfg.model_loc}")
            self.system.cache.unpickle(f"{self.cfg.model_loc}.pck")
        
        if self.cfg.save_model:
            print(f"Are we caching?: {self.system.cache.are_we_caching()}")
        
    def get_data(self) -> dict:
        
        """
        Return data used to make dash page
        """
        
        data = {}
        self.system.accounts.portfolio().sharpe()
        instruments = self.system.get_instrument_list()
        rule_list = list(self.cfg.trading_rules.keys())
        to_dataframe = lambda x: pd.concat(x.values(), axis=1, keys=x.keys(), join="outer")
        
        price_dict = {}
        raw_forecast_dict = {}
        position_dict = {}
        correlation_dict = {}
        rule_weight_dict = {}
        diversification_dict = {}
        comb_forecasts_dict = {}
        
        forecast_scalar_dict = {}
        forecast_turnover_dict = {}

        
        for instrument in instruments:
            
            price_dict[instrument] = self.system.data.get_raw_price(instrument)
            
            raw_rule_forecast_dict = {}
            forecast_scalar_dict = {}
            forecast_turnover_dict = {}
            
            for rule in rule_list:
                raw_rule_forecast_dict[rule] = self.system.rules.get_raw_forecast(instrument, rule)
                forecast_scalar_dict[rule] = self.system.forecastScaleCap.get_forecast_scalar(instrument, rule).tail(1).iloc[0].item()
                forecast_turnover_dict[rule] = self.system.accounts.get_SR_cost_for_instrument_forecast(instrument, rule).item()    
            raw_forecast_dict[instrument] = raw_rule_forecast_dict
            forecast_scalar_dict[instrument] = forecast_scalar_dict.copy()
            forecast_turnover_dict[instrument] = forecast_scalar_dict.copy()

            correlation_dict[instrument] = self.system.combForecast.get_forecast_correlation_matrices(instrument).corr_list[-1].as_pd()
            rule_weight_dict[instrument] = self.system.combForecast.get_forecast_weights(instrument)
            diversification_dict[instrument] = self.system.combForecast.get_forecast_diversification_multiplier(instrument)
            comb_forecasts_dict[instrument] = self.system.combForecast.get_combined_forecast(instrument) 
            
            position_dict[instrument] = self.system.accounts.get_actual_position(instrument)
        
        # Instruments
        price_df = to_dataframe(price_dict)
        data["prices"] = price_df
        
        # Rules and weights
        data["raw_forecast"] = raw_forecast_dict
        data["forecast_scalars"] = forecast_scalar_dict
        data["forecast_turnovers"] = forecast_turnover_dict
        
        data["correlation"] = correlation_dict
        rule_weight_df = to_dataframe(rule_weight_dict)
        data["rule_weights"] = rule_weight_df
        diversification_df = to_dataframe(diversification_dict)
        data["diversification"] = diversification_df
        comb_forecasts_df = to_dataframe(comb_forecasts_dict)
        data["comb_forecasts"] = comb_forecasts_df
        
        # Positions
        position_df = to_dataframe(position_dict)
        data["positions"] = position_df
        
        # Portfolio performance
        portfolio = self.system.accounts.portfolio()
        data["accumulated_returns"] = portfolio.percent.gross.curve()
        data["drawdown"] = portfolio.percent.drawdown()
        data["annualized_volatility"] = portfolio.percent.rolling_ann_std()
        
        # Save model
        if self.cfg.save_model:
            self.system.cache.pickle(f"{self.cfg.model_loc}.pck")
        
        return data


@hydra.main(config_path='pysystemtrade/examples/visualize/configs/.', config_name='futures_system')
def run_app(cfg):
    
    app_data = AppData(cfg)
    data = app_data.get_data()
    instruments = app_data.system.get_instrument_list()
    rule_list = list(cfg.trading_rules.keys())
    portfolio = app_data.system.accounts.portfolio()
    stats = dict(portfolio.percent.stats()[0])
    
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    
    ############------------ Instruments ------------############
    
    # Price dropdown plot
    @app.callback(
        Output(f"prices-plot", "figure"), 
        Input("price-instrument", "value"))
    def display_price_time_series(instrument):
        df = data["prices"][instrument].dropna() # replace with your own data source
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df,
                marker=dict(color='blue')
            )
        )
        fig = FigureResampler(fig)
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Price',
            template='plotly_white'
        )
        fig = FigureResampler(fig)
        return fig
    
    ############------------ Rules and Forecasts ------------############
    
    # Raw Forecast plot
    @app.callback(
        Output("raw_forecasts-plot", "figure"),
        [Input("raw_forecast-instrument", "value"),
         Input("raw_forecast-rule", "value")]
    )
    def display_raw_forecast(instrument, rule):
        df = data["raw_forecast"][instrument][rule]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df,
                marker=dict(color='blue')
            )
        )
        fig = FigureResampler(fig)
        fig.update_layout(
            xaxis_title = 'Date',
            yaxis_title = 'Return',
            template='plotly_white'
        ) 
        return fig
    
    # print(data["forecast_scalars"])
    # print(data["forecast_turnovers"])
    
    # Rule Weights plot
    @app.callback(
        Output("rule_weights-plot", "figure"),
        Input("weight-ticker", "value")
    )
    def display_rule_weights_time_series(instrument):
        df = data["rule_weights"][instrument]
        df = df.dropna()
        fig = go.Figure()
        for rule in df.keys():
            fig.add_trace(
                go.Scatter(
                    x=df[rule].index,
                    y=df[rule],
                    mode='lines',
                    name=rule
                )
            )
            
        fig.update_layout(
            xaxis_title = 'Date',
            yaxis_title = 'Weight',
            template = 'plotly_white'
        )
        return fig
    
    # Rule Correlations heatmap
    @app.callback(
        Output("rule_correlations-heatmap", "figure"),
        Input("correlation-ticker", "value")
    )
    def display_rule_correlation_heatmap(instrument):
        df = data["correlation"]
        c_data = df[instrument]
        fig = px.imshow(c_data, color_continuous_scale='Turbo')
        fig.update_layout(template="ggplot2")
        return fig
    
    # Diversification plot
    diversification_plot = go.Figure()
    diversification_df = data["diversification"]
    for instrument in instruments:
        diversification_plot.add_trace(
            go.Scatter(
                x=diversification_df.index,
                y=diversification_df[instrument],
                mode='lines',
                name=instrument
            )
        )
    diversification_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'IDF [-]',
        template='plotly_white'
    )
    # diversification_plot = FigureResampler(diversification_plot)
    
    # Combined Forecast plot
    @app.callback(
        Output("comb_forecasts-plot", "figure"),
        Input("forecast-ticker", "value")
    )
    def display_comb_forecasts_time_series(instrument):
        df = data["comb_forecasts"][instrument]
        df = df.dropna()
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df,
                marker=dict(color='black')
            )
        )
        fig = FigureResampler(fig)
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Level',
            template='plotly_white'
        )
        fig = FigureResampler(fig)
        return fig
        
    
    ############------------ Position Sizing ------------############
    # Price dropdown plot
    @app.callback(
        Output(f"positions-plot", "figure"), 
        Input("position-instrument", "value"))
    def display_position_time_series(instrument):
        position_df = data["positions"][instrument].dropna()
        price_df = data["prices"][instrument].dropna()
        price_df.index = price_df.index.date
        merged_df = pd.merge(price_df.rename('price'), position_df.rename('position'), left_index=True, right_index=True, how='left')
        # merged_df['position'] = merged_df['position'].fillna(method='ffill')
        merged_df['buy_signal'] = (merged_df['position'].shift(1) <= 1.0) & (merged_df['position'] > 1.0)
        merged_df['sell_signal'] = (merged_df['position'].shift(1) > -1.0) & (merged_df['position'] <= -1.0)
        
        fig = make_subplots(
            rows=2, cols=1,
            # subplot_titles=('Prices', 'Positions'),
            row_heights=[0.7, 0.3],
            shared_xaxes=True
        )
        
        fig.add_trace(
            go.Scatter(
                x=merged_df.index, 
                y=merged_df['price'], 
                mode='lines', 
                name='Price', 
                marker=dict(color='black')
            ),
            row=1,
            col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=merged_df.index[merged_df['buy_signal']],
                y=merged_df['price'][merged_df['buy_signal']],
                mode='markers',
                marker=dict(symbol='triangle-up', color='green', size=10),
                name='Buy Signal'
            ),
            row=1,
            col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=merged_df.index[merged_df['sell_signal']],
                y=merged_df['price'][merged_df['sell_signal']],
                mode='markers',
                marker=dict(symbol='triangle-down', color='red', size=10),
                name='Sell Signal'
            ),
            row=1,
            col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=position_df.index,
                y=position_df,
                mode='lines',
                marker=dict(color='grey'),
                name='Position'
            ),
            row=2,
            col=1
        )
        
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Price',
            template='plotly_white'
        )
        fig = FigureResampler(fig)
        return fig
    
    ############------------ Performance ------------############
    
    # Accumulated returns
    returns_plot = go.Figure()
    returns_df = data["accumulated_returns"]
    returns_plot.add_trace(
        go.Scatter(
            x=returns_df.index, 
            y=returns_df, 
            mode='lines',
            marker=dict(color='black')
        )
    )
    returns_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'Returns [%]',
        showlegend = False,
        template='plotly_white'
    )
    
    # Rolling annualized standard deviation
    annualized_volatility_plot = go.Figure()
    vol_df = data["annualized_volatility"]
    annualized_volatility_plot.add_trace(
        go.Scatter(
            x=vol_df.index,
            y=vol_df[0],
            mode='lines',
            marker=dict(color='black')
        )
    )
    annualized_volatility_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'Annualized Vol [%]',
        showlegend = False,
        template='plotly_white'
    )
    
    # Drawdown
    drawdown_plot = go.Figure()
    drawdown_df = data["drawdown"]
    drawdown_plot.add_trace(
        go.Scatter(
            x=drawdown_df.index,
            y=drawdown_df,
            mode='lines',
            marker=dict(color='black')
        )
    )
    drawdown_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'Drawdown [%]',
        showlegend = False,
        template='plotly_white'
    )
    
    SIDEBAR_STYLE = {
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
    }
    
    CONTENT_STYLE = {
        "margin-left": "18rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
    }
    
    sidebar = html.Div(
        [
            html.H2("Backtest", className="display-4"),
            html.Hr(),
            html.P(
                "Stages of Backtest", className="lead"
            ),
            dbc.Nav(
                [
                    dbc.NavLink("Summary", href="/", active="exact"),
                    dbc.NavLink("Instruments", href="/instruments", active="exact"),
                    dbc.NavLink("Rules and Forecasts", href="/rules", active="exact"),
                    dbc.NavLink("Position Sizing", href="/sizing", active="exact"),
                    dbc.NavLine("Risk", href="/risk", active="exact"),
                    dbc.NavLink("Performance", href="/performance", active="exact"),
                ],
                vertical=True,
                pills=True,
            ),
        ],
        style=SIDEBAR_STYLE
    )
    
    content = html.Div(id="page-content", style=CONTENT_STYLE)
    app.layout = html.Div([dcc.Location(id="url"), sidebar, content])
    
    @app.callback(Output("page-content", "children"), [Input("url", "pathname")])
    def render_page_content(pathname):
        if pathname == "/":
            return summary_content
        elif pathname == "/instruments":
            return instrument_content
        elif pathname == "/rules":
            return rules_content
        elif pathname == "/sizing":
            return sizing_content
        elif pathname == "/risk":
            return None
        elif pathname == "/performance":
            return performance_content
        else: 
            html.Div(
                [
                    html.H1("404: Not Found", className="text-danger"),
                    html.Hr(),
                    html.P(f"The pathname {pathname} was not recognized..."),  
                ],
                className="p-3 bg-light rounded-3",
            )
    
    summary_content = dbc.Container([
        dbc.Row([
            dcc.Markdown(
                f"""
                
                # Summary
                
                This is a backtest of a systematic trading system with the following parameters:
                - Name: {cfg.name}
                - Vol target: {cfg.percentage_vol_target} %
                - Notional trading capital: {cfg.notional_trading_capital}
                - Base Currency: {cfg.base_currency}
                - Rules: {cfg.trading_rules.keys()}
                - Instruments: {instruments}
                
                In a backtest this system achieves the following performance:
                - Worst year: {stats['min']} %
                - Best year: {stats['max']} %
                - Median: {stats['median']} %
                - Mean: {stats['mean']} %
                - Std: {stats['std']} %
                - Skew: {stats['skew']} %
                - Annualized mean: {stats['ann_mean']} %
                - Annualized standard Deviation: {stats['ann_std']} %
                - Sharpe: {stats['sharpe']}
                - Sortino ratio: {stats['sortino']}
                - Average drawdown: {stats['avg_drawdown']} %
                - Time in drawdown: {stats['time_in_drawdown']} years
                - Calmar: {stats['calmar']}
                - Average return to drawdown: {stats['avg_return_to_drawdown']} %
                - Average loss: {stats['avg_loss']} %
                - Average gain: {stats['avg_gain']} %
                - Gain to loss ratio: {stats['gaintolossratio']}
                - Profit factor: {stats['profitfactor']}
                - Hit rate: {stats['hitrate']}
                - t-statistic: {stats['t_stat']}
                - p-value: {stats['p_value']}
                
                """
            )
        ]),
    ])
    
    instrument_content = dbc.Container([
        dbc.Row([
            dcc.Markdown("Futures Contract instruments for each asset considered")
        ]),
        dbc.Row([
            html.H4("Instrument Prices"),
            dcc.Graph(id="prices-plot"),
            html.P("Select instrument:"),
            dcc.Dropdown(
                id="price-instrument",
                options=instruments,
                value=instruments[0],
                clearable=False
            )
        ]),
    ])
    
    rules_content = dbc.Container([
        
        dbc.Row([
            html.H4("Raw Forecast"),
            dcc.Graph(id="raw_forecasts-plot"),
            html.P("Select instrument:"),
            dcc.Dropdown(
                id="raw_forecast-instrument",
                options=instruments,
                value=instruments[0],
                clearable=False
            ),
            html.Br(),
            html.P("Select rule:"),
            dcc.Dropdown(
                id="raw_forecast-rule",
                options=rule_list,
                value=rule_list[0],
                clearable=False
            ), 
        ]),
        
        dbc.Row([
            html.H4("Rule Weights"),
            dcc.Graph(id="rule_weights-plot"),
            html.P("Select instrument:"),
            dcc.Dropdown(
                id="weight-ticker",
                options=instruments,
                value=instruments[0],
                clearable=False
            )
        ]),
        dbc.Row([
            html.H4("Rule Correlation"),
            dcc.Graph(id="rule_correlations-heatmap"),
            html.P("Select instrument:"),
            dcc.Dropdown(
                id="correlation-ticker",
                options=instruments,
                value=instruments[0],
                clearable=False
            )
        ]),
        dbc.Row([
            html.H4("Diversification"),
            dcc.Graph(figure=diversification_plot)
        ]),
        dbc.Row([
            html.H4("Combined Forecasts"),
            dcc.Graph(id="comb_forecasts-plot"),
            html.P("Select instrument:"),
            dcc.Dropdown(
                id="forecast-ticker",
                options=instruments,
                value=instruments[0],
                clearable=False
            )
        ])
    ])
    
    sizing_content = dbc.Container([
        dbc.Row([
            dcc.Markdown("Positions actually held and in which size")
        ]),
        dbc.Row([
            html.H4("Position Plots"),
            dcc.Graph(id="positions-plot"),
            html.P("Select instrument:"),
            dcc.Dropdown(
                id="position-instrument",
                options=instruments,
                value=instruments[0],
                clearable=False
            )
        ])
    ])
    
    performance_content = dbc.Container([
        dbc.Row([
            dbc.Col(dcc.Markdown("Plots comparing the performance of this trading system"))
        ]),
        dbc.Row([
            html.H4("Accumulated Returns"),
            dcc.Graph(figure=returns_plot)
        ]),
        dbc.Row([
            html.H4("Rolling annualized standard deviation"),
            dcc.Graph(figure=annualized_volatility_plot)
        ]),
        dbc.Row([
            html.H4("Drawdown"),
            dcc.Graph(figure=drawdown_plot)
        ]),
    ])
    
    app.run_server(host='0.0.0.0', port=8050)

    
if __name__=="__main__":
    run_app()