import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly_resampler import FigureResampler, FigureWidgetResampler
from omegaconf import DictConfig, OmegaConf
from pathlib import Path
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
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


class AppData:
    
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

    def get_dfs(self) -> dict:
        """
        Return the graphs used to make Dash app
        
        """
        data = {}
        instruments = self.system.get_instrument_list()
        to_dataframe = lambda x: pd.concat(x.values(), axis=1, keys=x.keys(), join = 'outer') 
        rule_list = list(self.cfg.trading_rules.keys())
        
         
        price_dict = {}
        comb_forecasts_dict = {}
        raw_forecasts_dict = {}
        forecast_scalars_dict = {}
        forecast_turnovers_dict = {}
        rule_weights_dict = {}
        correlation_dict = {}
        diversification_dict = {}
        notional_dict = {}
        position_dict = {}
        
        for instrument in instruments:
            price_dict[instrument] = self.system.data.get_raw_price(instrument)  # raw price
            comb_forecasts_dict[instrument] = self.system.combForecast.get_combined_forecast(instrument)  # comb forecasts
            
            raw_rule_forecast_dict = {}
            forecast_scalar_dict = {}
            forecast_turnover_dict = {}
            for rule in rule_list:
                raw_rule_forecast_dict[rule] = self.system.rules.get_raw_forecast(instrument, rule)
                forecast_scalar_dict[rule] = self.system.forecastScaleCap.get_forecast_scalar(instrument, rule).tail(1).iloc[0].item()
                forecast_turnover_dict[rule] = self.system.accounts.get_SR_cost_for_instrument_forecast(instrument, rule).item()
            raw_forecasts_dict[instrument] = to_dataframe(raw_rule_forecast_dict)
            forecast_scalars_dict[instrument] = forecast_scalar_dict.copy()
            correlation_dict[instrument] = self.system.combForecast.get_forecast_correlation_matrices(instrument).corr_list[-1].as_pd()  # instrument correlation array
             
            rule_weights_dict[instrument] = self.system.combForecast.get_forecast_weights(instrument)  # rule weights
            diversification_dict[instrument] = self.system.combForecast.get_forecast_diversification_multiplier(instrument)  # diversification values
            notional_dict[instrument] = self.system.portfolio.get_notional_position(instrument)
            position_dict[instrument] = self.system.positionSize.get_subsystem_position(instrument)
         
        price_df = to_dataframe(price_dict)
        comb_forecasts_df = to_dataframe(comb_forecasts_dict)
        rule_weights_df = to_dataframe(rule_weights_dict)
        diversification_df = to_dataframe(diversification_dict)
        notional_df = to_dataframe(notional_dict)
        position_df = to_dataframe(position_dict)

        data["prices"] = price_df
        data["comb_forecasts"] = comb_forecasts_df
        data["raw_forecasts"] = raw_forecasts_dict
        data["forecast_scalars"] = forecast_scalars_dict
        data["forecast_turnovers"] = forecast_turnovers_dict
        data["rule_weights"] = rule_weights_df
        data["correlation"] = correlation_dict
        data["diversification"] = diversification_df
        data["notional"] = notional_df
        data["position"] = position_df
        
        portfolio = self.system.accounts.portfolio()
        data["accumulated_returns"] = portfolio.percent.gross.curve()
        data["drawdown"] = portfolio.percent.drawdown()
        data["annualized_volatility"] = portfolio.percent.rolling_ann_std()
        
        return data


@hydra.main(config_path='pysystemtrade/examples/visualize/configs/.', config_name='system')
def run_app(cfg):
   

    data = AppData(cfg)
    dfs = data.get_dfs()
    instruments = data.system.get_instrument_list()
    rule_list = list(cfg.trading_rules.keys())
    portfolio = data.system.accounts.portfolio()
    stats = dict(portfolio.percent.stats()[0])
    
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    
    text_1 = f"""
    # Systematic Backtest
    
    This is a systematic backtest document to display the process used to make a rule based system.

    ## Summary
    The trading system has the following performance indicators:
    - Name: {cfg.name}
    - Vol target: {cfg.percentage_vol_target} %
    - Notional trading capital: {cfg.notional_trading_capital}
    - Base Currency: {cfg.base_currency}
    - Rules: {cfg.rule_variations}
    - Instruments: {cfg.instruments}
    
    The backtest has the following performance:
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

    ## Instruments
    
    The following instruments are used in this back-test
    """
    
    # Price dropdown plot
    @app.callback(
        Output(f"prices-plot", "figure"), 
        Input("price-ticker", "value"))
    def display_price_time_series(ticker):
        df = dfs["prices"] # replace with your own data source
        fig = px.line(df, y=ticker)
        fig = FigureResampler(fig)
        fig.update_layout(
            xaxis_title = 'Date',
            yaxis_title = 'Price'
        )
        # fig.update_xaxes(
        #     dtick="M3",
        #     tickformat="%Y"
        # )
        return fig
    
    text_2 = """
    
    ## Trading Rules and Forecasts
    
    The combined performance of each rule is based upon the diversification and forecast weights. The following is used here:
    - 1. Each rule's performance is back-tested on each instrument.
    - 2. Each forecast is scaled and capped based on turnover and cost
    - 3. Forecast weights are applied to each rule and instrument to maximize diversification. 
    - 4. The combined forecast is the position in each asset after applying weights and rescaling to a [-20, +20] range.
    
    """
    
    # Raw Forecast plot
    @app.callback(
        Output("raw_forecasts-plot", "figure"),
        [Input("raw_forecast-instrument", "value"),
         Input("raw_forecast-rule", "value")]
    )
    def display_raw_forecast(instrument, rule):
        df = dfs["raw_forecasts"][instrument]
        fig = px.line(df, y=rule)
        fig = FigureResampler(fig)
        fig.update_layout(
            xaxis_title = 'Date',
            yaxis_title = 'Return'
        ) 
        return fig
    
    # Make a markdown table of forecast scalars for rules and instruments 
    scalar_table = "| Instrument |"
    for rule in rule_list:
        scalar_table += f"{rule} |"
    scalar_table += "\n"
    for instrument in instruments:
        rule_substring= "| "
        rule_substring += f"**{instrument}** |"
        for rule in rule_list:
            rule_substring += f"{dfs['forecast_scalars'][instrument][rule]:.3f} |" 
        rule_substring += "\n"
        scalar_table += rule_substring
    scalar_table = scalar_table.split("\n", 1)
    seperator = "\n|"
    seperator += "---|"
    seperator += "\n"
    scalar_table = scalar_table[0] + seperator + scalar_table[1]
    
    # Make a markdown table of turnover for rules and instruments 
    turnover_table = "| Instrument |"
    for rule in rule_list:
        turnover_table += f"{rule} |"
    turnover_table += "\n"
    for instrument in instruments:
        rule_substring= "| "
        rule_substring += f"**{instrument}** |"
        for rule in rule_list:
            rule_substring += f"{dfs['forecast_turnovers'][instrument][rule]:.3f} |" 
        rule_substring += "\n"
        turnover_table += rule_substring
    turnover_table = turnover_table.split("\n", 1)
    seperator = "\n|"
    seperator += "---|"
    seperator += "\n"
    turnover_table = turnover_table[0] + seperator + turnover_table[1]
    
    # Rule Weight plot
    @app.callback(
        Output("rule_weights-plot", "figure"), 
        Input("weight-ticker", "value"))
    def display_rule_weights_time_series(ticker):
        df = dfs["rule_weights"] # replace with your own data source
        tick_data = df[ticker]
        fig = px.line(tick_data)
        fig = FigureResampler(fig)
        fig.update_layout(
            xaxis_title = 'Date',
            yaxis_title = 'Weight [-]'
        )
        return fig
    
    # Rule Correlations heatmap
    @app.callback(
        Output("rule_correlations-heatmap", "figure"),
        Input("correlation-ticker", "value")
    )
    def display_rule_correlation_heatmap(instrument):
        df = dfs["correlation"]
        c_data = df[instrument]
        fig = px.imshow(c_data, color_continuous_scale='Turbo')
        fig.update_layout(template="ggplot2")
        return fig
        
        
    # Diversification plot
    df = dfs["diversification"] # replace with your own data source
    diversification_plot = px.line(df)
    diversification_plot = FigureResampler(diversification_plot)
    diversification_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'IDF [-]'
    )
    
    # Combined Forecast plot
    @app.callback(
        Output("comb_forecasts-plot", "figure"), 
        Input("forecast-ticker", "value"))
    def display_comb_forecasts_time_series(ticker):
        df = dfs["comb_forecasts"] # replace with your own data source
        fig = px.line(df, y=ticker)
        fig = FigureResampler(fig)
        fig.update_layout(
            xaxis_title = 'Date',
            yaxis_title = 'Vol',
        )
        return fig
    
    text_3 = f"""
    
    ## Position Sizing and Portfolio
    
    The size of each position depends on the volatility and forecast from the last section:
    - Instrument position is the capital if all capital was invested into the specific instrument
    - Notional position is the actual capital from the rule
    
    """
    
    # Position plot
    df = dfs["position"]
    position_plot = px.line(df)
    position_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'Position'
    )
    
    # Notional plot
    df = dfs["notional"]
    notional_plot = px.line(df)
    notional_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'Notional'
    )
    
    text_4 = f"""
    
    # Performance
    
    The performance of the portfolio is displayed as:
    - Accumulated Returns
    - Rolling annualized standard deviation
    - Drawdown
    
    """
    
    # Returns
    df = dfs["accumulated_returns"]
    returns_plot = px.line(df)
    returns_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'Returns [%]',
        showlegend = False
    )
    
    # Ann_SD
    df = dfs["annualized_volatility"]
    annualized_volatility_plot = px.line(df)
    annualized_volatility_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'Annualized Vol [%]',
        showlegend = False
    )
    
    # Drawdown
    df = dfs["drawdown"]
    drawdown_plot = px.line(df)
    drawdown_plot.update_layout(
        xaxis_title = 'Date',
        yaxis_title = 'Drawdown [%]',
        showlegend = False
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
            return rule_content
        elif pathname == "/sizing":
            return sizing_content
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
            dbc.Col(dcc.Markdown(text_1))
        ])])
    
    instrument_content = dbc.Container([
        dbc.Row([
            html.H4("Instrument Prices"),
            dcc.Graph(id="prices-plot"),
            html.P("Select instrument:"),
            dcc.Dropdown(
                id="price-ticker",
                options=instruments,
                value=instruments[0],
                clearable=False
            ),
        ])
    ])
    
    rule_content = dbc.Container([
        dbc.Row([
            dbc.Col(dcc.Markdown(text_2))
        ]),
        
        dbc.Row([
            html.H4("Raw Forecasts"),
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
            )
        ]),
        dbc.Row([
            dbc.Col(dcc.Markdown("Scalar forecast for each rule and instrument"))
        ]),
        dbc.Row([
            dbc.Col(dcc.Markdown(scalar_table))
        ]),
        dbc.Row([
            dbc.Col(dcc.Markdown("SR cost for each instrument and rule"))
        ]),
        dbc.Row([
            dbc.Col(dcc.Markdown(turnover_table))
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
            ),
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
            ),
        ]),
        dbc.Row([
            html.H4("Diversification"),
            dcc.Graph(figure=diversification_plot)
        ]),
        dbc.Row([
            dbc.Col(dcc.Markdown("""Rule weights and diversification multiplier is used to calculate the combined forecast below"""))
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
            ),
        ])
    ])
    
    sizing_content = dbc.Container([
        dbc.Row([
            dbc.Col(dcc.Markdown(text_3))
        ]),
        dbc.Row([
            html.H4("Instrument Position"),
            dcc.Graph(figure=position_plot)
        ]),
        dbc.Row([
            html.H4("Notional Position"),
            dcc.Graph(figure=notional_plot)
        ])
    ])
    
    performance_content = dbc.Container([
        dbc.Row([
            dbc.Col(dcc.Markdown(text_4))
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
        ])
    ])
    # app.title = cfg.app.title
    app.run_server(host='0.0.0.0', port=8050)


if __name__=="__main__":
    run_app()