import datetime

import pandas as pd

from syscore.dateutils import n_days_ago
from syscore.objects import arg_not_supplied, missing_data, body_text
from sysdata.data_blob import dataBlob

from sysproduction.data.prices import diagPrices
from sysproduction.data.positions import annonate_df_index_with_positions_held
from sysproduction.reporting.reporting_functions import header, table

from sysproduction.utilities.costs import get_table_of_SR_costs, get_combined_df_of_costs
from sysproduction.utilities.trades import get_recent_broker_orders, create_raw_slippage_df, create_cash_slippage_df, \
    create_vol_norm_slippage_df, get_stats_for_slippage_groups, create_delay_df, get_recent_trades_from_db_as_terse_df, get_broker_trades_as_terse_df
from sysproduction.utilities.positions import get_optimal_positions, get_my_positions, get_broker_positions, \
    get_position_breaks
from sysproduction.utilities.risk_metrics import \
    get_correlation_matrix_all_instruments, get_instrument_risk_table, \
    get_portfolio_risk_for_all_strategies, get_portfolio_risk_across_strategies
from sysproduction.utilities.rolls import get_roll_data_for_instrument, ALL_ROLL_INSTRUMENTS
from sysproduction.utilities.volume import get_liquidity_data_df


class reportingApi(object):
    def __init__(self, data: dataBlob,
                        calendar_days_back: int = 250,
                        end_date: datetime.datetime = arg_not_supplied,
                        start_date: datetime.datetime = arg_not_supplied):

        self._data = data
        self._calendar_days_back = calendar_days_back
        self._passed_start_date = start_date
        self._passed_end_date = end_date

    def std_header(self, report_name: str):
        start_date = self.start_date
        end_date = self.end_date
        std_header = header("%s report produced on %s from %s to %s" %
               (report_name,
                   str(datetime.datetime.now()),
                str(start_date),
               str(end_date)))

        return std_header

    def terse_header(self, report_name: str):
        terse_header = header("%s report produced on %s" %
               (report_name,
                   str(datetime.datetime.now())))

        return terse_header

    def footer(self):
        return header("END OF REPORT")

    #### ROLL REPORT ####
    def table_of_roll_data(self, instrument_code: str = ALL_ROLL_INSTRUMENTS):
        result_pd = self._roll_data_as_pd(instrument_code)
        table_result = table("Status and time to roll in days", result_pd)

        return table_result

    def _roll_data_as_pd(self, instrument_code: str = ALL_ROLL_INSTRUMENTS):
        roll_data_dict = self.roll_data_dict_for_instrument_code(instrument_code)

        result_pd = pd.DataFrame(roll_data_dict)
        result_pd = result_pd.transpose()

        result_pd = result_pd.sort_values("roll_expiry")

        return result_pd


    def roll_data_dict_for_instrument_code(self, instrument_code: str = ALL_ROLL_INSTRUMENTS):
        roll_data_dict = self.roll_data_dict
        if instrument_code is ALL_ROLL_INSTRUMENTS:
            return roll_data_dict
        else:
            return {instrument_code: roll_data_dict[instrument_code]}

    @property
    def roll_data_dict(self):
        roll_data_dict = getattr(self, "_roll_data_dict", missing_data)
        if roll_data_dict is missing_data:
            roll_data_dict = self._roll_data_dict = self._get_roll_data_dict()

        return roll_data_dict


    def _get_roll_data_dict(self):
        list_of_instruments = self._list_of_all_instruments()
        data = self.data

        roll_data_dict = {}
        for instrument_code in list_of_instruments:
            roll_data = get_roll_data_for_instrument(instrument_code, data)
            roll_data_dict[instrument_code] = roll_data

        return roll_data_dict

    def _list_of_all_instruments(self):
        diag_prices = diagPrices(self.data)
        list_of_instruments = diag_prices.get_list_of_instruments_in_multiple_prices()

        return list_of_instruments


    #### RISK REPORT ####
    def table_of_correlations(self):
        corr_data = get_correlation_matrix_all_instruments(self.data)
        corr_data = corr_data.as_pd().round(2)
        table_corr = table("Correlations", corr_data)

        return table_corr

    def table_of_instrument_risk(self):
        instrument_risk_data = self.instrument_risk_data
        instrument_risk_data_rounded = instrument_risk_data.round(2)
        table_instrument_risk = table("Instrument risk", instrument_risk_data_rounded)
        return table_instrument_risk


    def table_of_strategy_risk(self):
        strategy_risk = get_portfolio_risk_across_strategies(self.data)
        strategy_risk = strategy_risk*100.0
        strategy_risk = strategy_risk.round(1)
        table_strategy_risk = table("Risk per strategy, annualised percentage", strategy_risk)

        return table_strategy_risk

    def body_text_portfolio_risk_total(self):
        portfolio_risk_total = get_portfolio_risk_for_all_strategies(self.data)
        portfolio_risk_total = portfolio_risk_total*100.0
        portfolio_risk_total = portfolio_risk_total.round(1)
        portfolio_risk_total_text = body_text("Total risk across all strategies, annualised percentage %.1f" % portfolio_risk_total)

        return portfolio_risk_total_text

    def body_text_abs_total_all_risk_perc_capital(self):
        instrument_risk_data =self.instrument_risk_data
        all_risk_perc_capital = instrument_risk_data.exposure_held_perc_capital
        abs_total_all_risk_perc_capital = all_risk_perc_capital.abs().sum()

        return body_text("Sum of abs(notional exposure %% capital) %.1f" %
                         abs_total_all_risk_perc_capital)

    def body_text_abs_total_all_risk_annualised(self):
        instrument_risk_data = self.instrument_risk_data
        all_risk_annualised = instrument_risk_data.annual_risk_perc_capital
        abs_total_all_risk_annualised = all_risk_annualised.abs().sum()

        return body_text("Sum of abs(annualised risk %% capital) %.1f" %
                         abs_total_all_risk_annualised)

    def body_text_net_total_all_risk_annualised(self):
        instrument_risk_data = self.instrument_risk_data
        all_risk_annualised = instrument_risk_data.annual_risk_perc_capital
        net_total_all_risk_annualised = all_risk_annualised.sum()

        return body_text("Net sum of annualised risk %% capital %.1f " %
                         net_total_all_risk_annualised)

    @property
    def instrument_risk_data(self):
        instrument_risk = getattr(self, "_instrument_risk", missing_data)
        if instrument_risk is missing_data:
            instrument_risk = self._instrument_risk = self._get_instrument_risk()

        return instrument_risk

    def _get_instrument_risk(self):
        instrument_risk_data = get_instrument_risk_table(self.data)
        return instrument_risk_data

    ##### RECONCILE #####
    def table_of_optimal_positions(self):
        positions_optimal = get_optimal_positions(self.data)
        table_positions_optimal = table("Optimal versus actual positions", positions_optimal)
        return table_positions_optimal

    def table_of_my_positions(self):
        positions_mine = get_my_positions(self.data)
        table_positions_mine = table("Positions in DB",positions_mine)

        return table_positions_mine

    def table_of_ib_positions(self):
        positions_ib = get_broker_positions(self.data)
        table_positions_ib = table("Positions broker", positions_ib)

        return table_positions_ib

    def body_text_position_breaks(self):
        position_breaks = get_position_breaks(self.data)
        text_position_breaks = body_text(position_breaks)

        return text_position_breaks

    def table_of_my_recent_trades_from_db(self):
        trades_mine = get_recent_trades_from_db_as_terse_df(self.data)
        table_trades_mine = table("Trades in DB", trades_mine)

        return table_trades_mine

    def table_of_recent_ib_trades(self):
        trades_ib = get_broker_trades_as_terse_df(self.data)
        table_trades_ib = table("Trades from broker", trades_ib)

        return table_trades_ib


    ##### LIQUIDITY ######
    def table_of_liquidity_contract_sort(self) -> table:
        all_liquidity_df = self.liquidity_data
        all_liquidity_df = all_liquidity_df.sort_values("contracts")
        table_liquidity = table(" Sorted by contracts: Less than 100 contracts a day is a problem",
                                all_liquidity_df)

        return table_liquidity

    def table_of_liquidity_risk_sort(self) -> table:
        all_liquidity_df = self.liquidity_data
        all_liquidity_df = all_liquidity_df.sort_values("risk")
        table_liquidity = table("Sorted by risk: Less than $1.5 million of risk per day is a problem",
                                all_liquidity_df)

        return table_liquidity

    @property
    def liquidity_data(self) -> pd.DataFrame:
        liquidity = getattr(self, "_liquidity_data", missing_data)
        if liquidity is missing_data:
            liquidity = self._liquidity_data = self._get_liquidity_data()

        return liquidity

    def _get_liquidity_data(self) -> pd.DataFrame:
        return get_liquidity_data_df(self.data)

    ##### COSTS ######
    def table_of_sr_costs(self):
        table_of_sr_costs = get_table_of_SR_costs_as_formatted_table(self.data)

        return table_of_sr_costs

    def table_of_slippage_comparison(self):
        table_of_slippage = get_combined_df_of_costs_as_table(self.data,
                                                              start_date=self.start_date,
                                                              end_date=self.end_date)

        return table_of_slippage


    ##### TRADES ######

    def table_of_orders_overview(self):
        broker_orders = self.broker_orders
        if len(broker_orders)==0:
            return body_text("No trades")

        overview = broker_orders[
            [
                "instrument_code",
                "strategy_name",
                "contract_date",
                "fill_datetime",
                "fill",
                "filled_price",
            ]
        ]
        overview = overview.sort_values("instrument_code")
        overview_table = table("Broker orders", overview)

        return overview_table

    def table_of_order_delays(self):
        broker_orders = self.broker_orders
        if len(broker_orders)==0:
            return body_text("No trades")

        delays = create_delay_df(broker_orders)

        table_of_delays = table("Delays", delays)

        return table_of_delays

    def table_of_raw_slippage(self):
        raw_slippage = self.raw_slippage
        if len(raw_slippage)==0:
            return body_text("No trades")

        table_of_raw_slippage = table("Slippage (ticks per lot)", raw_slippage)

        return table_of_raw_slippage

    def table_of_vol_slippage(self):
        raw_slippage = self.raw_slippage
        if len(raw_slippage)==0:
            return body_text("No trades")

        vol_slippage = create_vol_norm_slippage_df(raw_slippage, self.data)
        table_of_vol_slippage = table(
            "Slippage (normalised by annual vol, BP of annual SR)",
            vol_slippage)

        return table_of_vol_slippage

    def list_of_cash_summary_text(self) -> list:
        cash_slippage = self.cash_slippage
        if len(cash_slippage)==0:
            return [body_text("No trades")]

        item_list = [
            "delay_cash",
            "bid_ask_cash",
            "execution_cash",
            "versus_limit_cash",
            "versus_parent_limit_cash",
            "total_trading_cash",
        ]
        detailed_cash_results = get_stats_for_slippage_groups(
            cash_slippage, item_list)

        list_of_summary_results = [body_text("%s\n%s" % (key, str(value))) \
                                   for key,value in detailed_cash_results.items()]

        return list_of_summary_results

    def table_of_cash_slippage(self):
        cash_slippage = self.cash_slippage
        if len(cash_slippage)==0:
            return body_text("No trades")

        table_slippage = table("Slippage (In base currency)", cash_slippage)

        return table_slippage

    @property
    def cash_slippage(self) -> pd.DataFrame:
        cash_slippage = getattr(self, "_cash_slippage", missing_data)
        if cash_slippage is missing_data:
            cash_slippage = self._cash_slippage = self._get_cash_slippage()

        return cash_slippage

    def _get_cash_slippage(self) -> pd.DataFrame:
        raw_slippage = self.raw_slippage
        if len(raw_slippage)==0:
            return pd.DataFrame()

        cash_slippage = create_cash_slippage_df(raw_slippage, self.data)

        return cash_slippage

    @property
    def raw_slippage(self) -> pd.DataFrame:
        raw_slippage = getattr(self, "_raw_slippage", missing_data)
        if raw_slippage is missing_data:
            raw_slippage = self._raw_slippage = self._get_raw_slippage()

        return raw_slippage

    def _get_raw_slippage(self) -> pd.DataFrame:
        broker_orders = self.broker_orders
        if len(broker_orders)==0:
            return pd.DataFrame()
        raw_slippage = create_raw_slippage_df(broker_orders)

        return raw_slippage

    @property
    def broker_orders(self) -> pd.DataFrame:
        broker_orders = getattr(self, "_broker_orders", missing_data)
        if broker_orders is missing_data:
            broker_orders = self._broker_orders = self._get_broker_orders()

        return broker_orders

    def _get_broker_orders(self) -> pd.DataFrame:
        broker_orders = get_recent_broker_orders(self.data,
                                                 start_date = self.start_date,
                                                 end_date = self.end_date)
        return broker_orders

    ##### DATA AND DATES #####

    @property
    def data(self) -> dataBlob:
        return self._data

    @property
    def start_date(self) -> datetime.datetime:
        start_date = getattr(self, "_start_date", missing_data)
        if start_date is missing_data:
            start_date = self._start_date = self._calculate_start_date()

        return start_date

    def _calculate_start_date(self) -> datetime.datetime:
        start_date = self._passed_start_date
        if start_date is arg_not_supplied:
            calendar_days_back = self._calendar_days_back
            end_date = self.end_date
            start_date = n_days_ago(calendar_days_back, date_ref=end_date)

        return start_date

    @property
    def end_date(self) -> datetime.datetime:
        end_date = getattr(self, "_end_date", missing_data)
        if end_date is missing_data:
            end_date = self._end_date = self._calculate_end_date()

        return end_date

    def _calculate_end_date(self) -> datetime.datetime:
        end_date = self._passed_end_date
        if end_date is arg_not_supplied:
            end_date = datetime.datetime.now()

        return end_date

def get_combined_df_of_costs_as_table(data: dataBlob,
                                      start_date: datetime.datetime,
                                      end_date: datetime.datetime):

    combined_df_costs = get_combined_df_of_costs(data,
                                                 start_date=start_date,
                                                 end_date=end_date)
    combined_df_costs = combined_df_costs.round(6)
    combined_df_costs = annonate_df_index_with_positions_held(data=data,
                                                              pd_df=combined_df_costs)

    combined_df_costs_as_formatted_table = table("Check of slippage", combined_df_costs)

    return combined_df_costs_as_formatted_table

def get_table_of_SR_costs_as_formatted_table(data):
    table_of_SR_costs = get_table_of_SR_costs(data)
    table_of_SR_costs = table_of_SR_costs.round(5)
    table_of_SR_costs = annonate_df_index_with_positions_held(data=data,
                                                              pd_df=table_of_SR_costs)
    formatted_table = \
        table("SR costs (using stored slippage): more than 0.01 means panic", table_of_SR_costs)

    return formatted_table


def get_liquidity_report_data(data: dataBlob) -> pd.DataFrame:
    all_liquidity_df = get_liquidity_data_df(data)
    all_liquidity_df = annonate_df_index_with_positions_held(data, all_liquidity_df)

    return all_liquidity_df