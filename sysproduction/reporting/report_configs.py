from copy import copy

from sysobjects.production.roll_state import ALL_ROLL_INSTRUMENTS


class reportConfig(object):
    def __init__(self, title, function, output="console", **kwargs):
        assert output in ["console", "email", "file", "emailfile"]
        self.title = title
        self.function = function
        self.output = output
        self.kwargs = kwargs

    def __repr__(self):
        return "%s %s %s %s" % (
            self.title,
            self.function,
            self.output,
            str(self.kwargs),
        )

    def new_config_with_modified_output(self, output):
        new_config = copy(self)
        new_config.output = output

        return new_config

    def new_config_with_modify_kwargs(self, **kwargs):
        new_config = copy(self)
        new_config.modify_kwargs(**kwargs)

        return new_config

    def modify_kwargs(self, **kwargs):
        for key in kwargs.keys():
            self.kwargs[key] = kwargs[key]

        return self


status_report_config = reportConfig(
    title="Status report",
    function="sysproduction.reporting.status_report.status_report",
    output="email",
)

roll_report_config = reportConfig(
    title="Roll report",
    function="sysproduction.reporting.roll_report.roll_report",
    instrument_code=ALL_ROLL_INSTRUMENTS,
    output="email",
)

daily_pandl_report_config = reportConfig(
    title="P&L report",
    function="sysproduction.reporting.pandl_report.pandl_report",
    calendar_days_back=1,
    output="email",
)

reconcile_report_config = reportConfig(
    title="Reconcile report",
    function="sysproduction.reporting.reconcile_report.reconcile_report",
    output="email",
)

trade_report_config = reportConfig(
    title="Trade report",
    function="sysproduction.reporting.trades_report.trades_report",
    calendar_days_back=1,
    output="email",
)

strategy_report_config = reportConfig(
    title="Strategy report",
    function="sysproduction.reporting.strategies_report.strategy_report",
    output="email",
)

risk_report_config = reportConfig(
    title="Risk report",
    function="sysproduction.reporting.risk_report.risk_report",
    output="email",
)

liquidity_report_config = reportConfig(
    title="Liquidity report",
    function="sysproduction.reporting.liquidity_report.liquidity_report",
    output="email",
)

costs_report_config = reportConfig(
    title="Costs report",
    function="sysproduction.reporting.costs_report.costs_report",
    output="email",
    calendar_days_back=250,
)

slippage_report_config = reportConfig(
    title="Slippage report",
    function="sysproduction.reporting.slippage_report.slippage_report",
    calendar_days_back=250,
    output="email",
)

commission_report_config = reportConfig(
    title="Commission report",
    function="sysproduction.reporting.commissions_report.commissions_report",
    output="email",
)

instrument_risk_report_config = reportConfig(
    title="Instrument risk report",
    function="sysproduction.reporting.instrument_risk_report.instrument_risk_report",
    output="email",
)

min_capital_report_config = reportConfig(
    title="Minimum capital report",
    function="sysproduction.reporting.minimum_capital_report.minimum_capital_report",
    output="email",
)

duplicate_market_report_config = reportConfig(
    title="Duplicate markets report",
    function="sysproduction.reporting.duplicate_market_report.duplicate_market_report",
    output="email",
)

remove_markets_report_config = reportConfig(
    title="Remove markets report",
    function="sysproduction.reporting.remove_markets_report.remove_markets_report",
    output="email",
)

market_monitor_report_config = reportConfig(
    title="Market monitor report",
    function="sysproduction.reporting.market_monitor_report.market_monitor_report",
    output="email",
)

account_curve_report_config = reportConfig(
    title="Account curve report",
    function="sysproduction.reporting.account_curve_report.account_curve_report",
    output="email",
)

## The reports will be run in this order
report_config_defaults = dict(
    slippage_report=slippage_report_config,
    costs_report=costs_report_config,
    roll_report=roll_report_config,
    daily_pandl_report=daily_pandl_report_config,
    reconcile_report=reconcile_report_config,
    trade_report=trade_report_config,
    strategy_report=strategy_report_config,
    risk_report=risk_report_config,
    status_report=status_report_config,
    liquidity_report=liquidity_report_config,
    instrument_risk_report=instrument_risk_report_config,
    min_capital=min_capital_report_config,
    duplicate_market=duplicate_market_report_config,
    remove_markets_report=remove_markets_report_config,
    market_monitor_report=market_monitor_report_config,
    account_curve_report=account_curve_report_config,
    commission_report=commission_report_config,
)
