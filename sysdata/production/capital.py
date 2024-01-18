# FIXME RENAME 'capital.py' when original capital no longer needed for transfer purposes

from copy import copy
import datetime
import pandas as pd
import numpy as np

from syscore.exceptions import missingData
from syscore.constants import arg_not_supplied

from sysdata.base_data import baseData
from sysobjects.production.capital import (
    LIST_OF_COMPOUND_METHODS,
    totalCapitalUpdater,
)

GLOBAL_CAPITAL_DICT_KEY = "__global_capital"
CURRENT_CAPITAL_LABEL = "Actual"
MAX_CAPITAL_LABEL = "Max"
ACC_CAPITAL_LABEL = "Accumulated"
BROKER_CAPITAL_LABEL = "Broker"
ALL_LABELS = [
    CURRENT_CAPITAL_LABEL,
    MAX_CAPITAL_LABEL,
    ACC_CAPITAL_LABEL,
    BROKER_CAPITAL_LABEL,
]


class capitalData(baseData):
    ## TOTAL CAPITAL

    def get_current_total_capital(self) -> float:
        pd_series = self.get_total_capital_pd_series()
        return float(pd_series.iloc[-1])

    def get_current_broker_account_value(self) -> float:
        pd_series = self.get_broker_account_value_pd_series()

        return float(pd_series.iloc[-1])

    def get_current_maximum_capital_value(self) -> float:
        pd_series = self.get_maximum_account_value_pd_series()
        return float(pd_series.iloc[-1])

    def get_current_pandl_account(self) -> float:
        pd_series = self.get_profit_and_loss_account_pd_series()
        return float(pd_series.iloc[-1])

    def get_total_capital_pd_series(self) -> pd.Series:
        all_capital_series = self.get_df_of_all_global_capital()
        return all_capital_series[CURRENT_CAPITAL_LABEL]

    def get_broker_account_value_pd_series(self) -> pd.Series:
        all_capital_series = self.get_df_of_all_global_capital()
        return all_capital_series[BROKER_CAPITAL_LABEL]

    def get_maximum_account_value_pd_series(self) -> pd.Series:
        all_capital_series = self.get_df_of_all_global_capital()
        return all_capital_series[MAX_CAPITAL_LABEL]

    def get_profit_and_loss_account_pd_series(self) -> pd.Series:
        all_capital_series = self.get_df_of_all_global_capital()
        return all_capital_series[ACC_CAPITAL_LABEL]

    def add_global_capital_entries(
        self,
        total_current_capital: float = arg_not_supplied,
        acc_pandl: float = arg_not_supplied,
        broker_account_value: float = arg_not_supplied,
        maximum_capital: float = arg_not_supplied,
        date: datetime.datetime = arg_not_supplied,
    ):
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        ## use nans if not passed so forward filling works
        if total_current_capital is arg_not_supplied:
            total_current_capital = np.nan

        if maximum_capital is arg_not_supplied:
            maximum_capital = np.nan

        if broker_account_value is arg_not_supplied:
            broker_account_value = np.nan

        if acc_pandl is arg_not_supplied:
            acc_pandl = np.nan

        cap_entry_dict = {}
        cap_entry_dict[CURRENT_CAPITAL_LABEL] = total_current_capital
        cap_entry_dict[ACC_CAPITAL_LABEL] = acc_pandl
        cap_entry_dict[BROKER_CAPITAL_LABEL] = broker_account_value
        cap_entry_dict[MAX_CAPITAL_LABEL] = maximum_capital

        new_capital_row = pd.DataFrame(cap_entry_dict, index=[date])

        try:
            capital_df = self.get_df_of_all_global_capital()
        except missingData:
            raise Exception("Need to initialise capital first")

        updated_capital_df = pd.concat([capital_df, new_capital_row], axis=0)
        ffill_updated_capital_df = updated_capital_df.ffill()

        self.update_df_of_all_global_capital(ffill_updated_capital_df)

    def create_initial_capital(
        self,
        total_current_capital: float,
        broker_account_value: float,
        maximum_capital: float,
        acc_pandl: float = 0,
        date: datetime.datetime = arg_not_supplied,
    ):
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        cap_entry_dict = {}
        cap_entry_dict[CURRENT_CAPITAL_LABEL] = total_current_capital
        cap_entry_dict[ACC_CAPITAL_LABEL] = acc_pandl
        cap_entry_dict[BROKER_CAPITAL_LABEL] = broker_account_value
        cap_entry_dict[MAX_CAPITAL_LABEL] = maximum_capital

        new_capital_row = pd.DataFrame(cap_entry_dict, index=[date])

        self.update_df_of_all_global_capital(new_capital_row)

    def delete_recent_capital(self, last_date: datetime.datetime):
        self.delete_recent_capital_for_strategy(
            GLOBAL_CAPITAL_DICT_KEY, last_date=last_date
        )

    def delete_all_global_capital(self, are_you_really_sure=False):
        self.delete_all_capital_for_strategy(
            GLOBAL_CAPITAL_DICT_KEY, are_you_really_sure=are_you_really_sure
        )

    def get_df_of_all_global_capital(self) -> pd.DataFrame:
        ## ignore warning- for global we pass a Frame not a Series
        capital_df = self.get_capital_pd_df_for_strategy(GLOBAL_CAPITAL_DICT_KEY)

        return capital_df

    def update_df_of_all_global_capital(self, updated_capital_series: pd.DataFrame):
        ## ignore warning - for global we pass a Frame not a Series
        self.update_capital_pd_df_for_strategy(
            GLOBAL_CAPITAL_DICT_KEY, updated_capital_series
        )

    ## STRATEGY CAPITAL
    def get_current_capital_for_strategy(self, strategy_name: str) -> float:
        capital_series = self.get_capital_pd_df_for_strategy(strategy_name)
        return float(capital_series.iloc[-1, 0])

    def update_capital_value_for_strategy(
        self,
        strategy_name: str,
        new_capital_value: float,
        date: datetime.datetime = arg_not_supplied,
    ):
        assert strategy_name is not GLOBAL_CAPITAL_DICT_KEY

        if date is arg_not_supplied:
            date = datetime.datetime.now()

        try:
            capital_df = self.get_capital_pd_df_for_strategy(strategy_name)
        except missingData:
            capital_series = pd.Series(dtype=float)
        else:
            capital_series = df_to_series(capital_df)

        new_capital_item = pd.Series([new_capital_value], [date])
        updated_capital_series = pd.concat([capital_series, new_capital_item], axis=0)
        updated_capital_df = updated_capital_series.to_frame()

        self.update_capital_pd_df_for_strategy(strategy_name, updated_capital_df)

    def delete_recent_capital_for_strategy(
        self, strategy_name: str, last_date: datetime.datetime
    ):
        capital_series = self.get_capital_pd_df_for_strategy(strategy_name)
        updated_capital_series = capital_series[:last_date]

        self.update_capital_pd_df_for_strategy(strategy_name, updated_capital_series)

    def delete_all_capital_for_strategy(
        self, strategy_name: str, are_you_really_sure=False
    ):
        if are_you_really_sure:
            self._delete_all_capital_for_strategy_no_checking(strategy_name)
        else:
            raise Exception("Have to be sure to delete capital")

    def get_list_of_strategies_with_capital(self) -> list:
        list_of_strategies = self._get_list_of_strategies_with_capital_including_total()
        try:
            list_of_strategies.remove(GLOBAL_CAPITAL_DICT_KEY)
        except:
            pass

        return list_of_strategies

    def _get_list_of_strategies_with_capital_including_total(self) -> list:
        raise NotImplementedError

    def get_capital_pd_df_for_strategy(self, strategy_name: str) -> pd.DataFrame:
        raise NotImplementedError

    def _delete_all_capital_for_strategy_no_checking(self, strategy_name: str):
        raise NotImplementedError

    def update_capital_pd_df_for_strategy(
        self, strategy_name: str, updated_capital_df: pd.DataFrame
    ):
        raise NotImplementedError


def df_to_series(x: pd.DataFrame) -> pd.Series:
    if len(x) == 1:
        y = pd.Series(float(x.values[0]), index=x.index)
    else:
        y = x.squeeze()

    return y


class totalCapitalCalculationData(object):
    """
    This object allows us to calculate available total capital from previous capital and profits

    Three different compounding methods are available  ['full', 'half', 'fixed']

    """

    def __init__(self, capital_data: capitalData, calc_method="full"):
        """
        Calculation methods are: full- all profits and losses go to capital, half - profits past the HWM are not added,
           fixed - capital is unaffected by profits and losses (not reccomended!)

        :param capital_data: strategyCapitalData instance or something that inherits from it
        :param calc_method: method for going from profits to capital allocated
        """
        self._capital_data = capital_data

        try:
            assert calc_method in LIST_OF_COMPOUND_METHODS
        except BaseException:
            raise Exception(
                "Capital calculation %s has to be one of %s"
                % (calc_method, LIST_OF_COMPOUND_METHODS)
            )

        self._calc_method = calc_method

    @property
    def capital_data(self) -> capitalData:
        return self._capital_data

    @property
    def calc_method(self):
        return self._calc_method

    def __repr__(self):
        return "capitalCalculationData for %s" % self._capital_data

    def get_percentage_returns_as_pd(self) -> pd.DataFrame:
        total_capital = self.get_total_capital()
        daily_returns = self.get_daily_returns()
        daily_capital = total_capital.reindex(daily_returns.index).ffill()

        perc_returns = daily_returns / daily_capital

        return perc_returns

    def get_daily_returns(self) -> pd.Series:
        daily_pandl = self.get_daily_profit_and_loss()
        daily_returns = daily_pandl.diff()
        return daily_returns

    def get_daily_profit_and_loss(self) -> pd.Series:
        pandl = self.get_profit_and_loss_account()
        daily_pandl = pandl.resample("1B").last()

        return daily_pandl

    def check_for_total_capital_data(self) -> bool:
        try:
            all_global_capital = self.get_df_of_all_global_capital()
            if len(all_global_capital) == 0:
                raise Exception
            return True
        except:
            return False

    def get_current_total_capital(self):
        return self.capital_data.get_current_total_capital()

    def get_current_broker_account(self) -> float:
        return self.capital_data.get_current_broker_account_value()

    def get_current_maximum_capital(self) -> float:
        return self.capital_data.get_current_maximum_capital_value()

    def get_total_capital(self) -> pd.Series:
        return self.capital_data.get_total_capital_pd_series()

    def get_current_accumulated_pandl(self) -> float:
        return self.capital_data.get_current_pandl_account()

    def get_profit_and_loss_account(self) -> pd.Series:
        return self.capital_data.get_profit_and_loss_account_pd_series()

    def get_maximum_account(self) -> pd.Series:
        return self.capital_data.get_maximum_account_value_pd_series()

    def get_df_of_all_global_capital(self) -> pd.DataFrame:
        return self.capital_data.get_df_of_all_global_capital()

    def update_and_return_total_capital_with_new_broker_account_value(
        self, broker_account_value: float, check_limit=0.1
    ) -> float:
        """
        does everything you'd expect when a new broker account value arrives:
           - add on to broker account value series
           - get p&l since last broker
            - call capital calculation function, which will update

        If the change in broker account value is greater than check_limit then do not update capital
        You will have to check and do a manual update if it's correct

        :param value: float
        :param check_limit: float
        :return: current total capital
        """
        # Compare broker account value to previous

        capital_updater = self._init_capital_updater(broker_account_value)
        capital_updater.check_pandl_size(check_limit=check_limit)

        capital_updater.calculate_new_total_and_max_capital_given_pandl()

        self._update_capital_data_after_pandl_event(capital_updater)

        return capital_updater.new_total_capital

    def _init_capital_updater(
        self, new_broker_account_value: float
    ) -> totalCapitalUpdater:
        calc_method = self.calc_method
        try:
            prev_broker_account_value = self._get_prev_broker_account_value()
        except missingData:
            raise Exception("No previous broker account value can't update capital")

        prev_maximum_capital = self.capital_data.get_current_maximum_capital_value()
        prev_total_capital = self.capital_data.get_current_total_capital()
        prev_pandl_cum_acc = self.capital_data.get_current_pandl_account()

        capital_updater = totalCapitalUpdater(
            new_broker_account_value=new_broker_account_value,
            prev_total_capital=prev_total_capital,
            prev_maximum_capital=prev_maximum_capital,
            prev_broker_account_value=prev_broker_account_value,
            calc_method=calc_method,
            prev_pandl_cum_acc=prev_pandl_cum_acc,
        )

        return capital_updater

    def _get_prev_broker_account_value(self) -> float:
        prev_broker_account_value = self.capital_data.get_current_broker_account_value()

        return prev_broker_account_value

    def _update_capital_data_after_pandl_event(
        self, capital_updater: totalCapitalUpdater
    ):
        # Update broker account value and add p&l entry with synched dates
        date = datetime.datetime.now()

        new_total_capital = capital_updater.new_total_capital
        new_maximum_capital = capital_updater.new_maximum_capital
        new_broker_account_value = capital_updater.new_broker_account_value
        new_acc_pandl = capital_updater.new_acc_pandl

        self.modify_account_values(
            broker_account_value=new_broker_account_value,
            total_capital=new_total_capital,
            maximum_capital=new_maximum_capital,
            acc_pandl=new_acc_pandl,
            date=date,
            are_you_sure=True,
        )

    def adjust_broker_account_for_delta(self, delta_value: float):
        """
        If you have changed broker account value, for example because of a withdrawal, but don't want this to
        affect capital calculations

        A negative delta_value indicates a withdrawal (capital value falling) and vice versa

        :param value: change in account value to be ignore, a minus figure is a withdrawal, positive is deposit
        :return: None
        """

        try:
            prev_broker_account_value = (
                self.capital_data.get_current_broker_account_value()
            )
        except missingData:
            self._capital_data.log.warning(
                "Can't apply a delta to broker account value, since no value in data"
            )
            raise

        broker_account_value = prev_broker_account_value + delta_value

        # Update broker account value
        self.modify_account_values(
            broker_account_value=broker_account_value, are_you_sure=True
        )

    def modify_account_values(
        self,
        broker_account_value: float = arg_not_supplied,
        total_capital: float = arg_not_supplied,
        maximum_capital: float = arg_not_supplied,
        acc_pandl: float = arg_not_supplied,
        date: datetime.datetime = arg_not_supplied,
        are_you_sure: bool = False,
    ):
        """
        Allow any account valuation to be modified
        Be careful! Only use if you really know what you are doing

        :param value: new_maximum_account_value
        :return: None
        """
        if not are_you_sure:
            self.capital_data.log.warning("You need to be sure to modify capital!")
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        self.capital_data.add_global_capital_entries(
            total_current_capital=total_capital,
            maximum_capital=maximum_capital,
            acc_pandl=acc_pandl,
            broker_account_value=broker_account_value,
            date=date,
        )

    def create_initial_capital(
        self,
        broker_account_value: float,
        total_capital: float = arg_not_supplied,
        maximum_capital: float = arg_not_supplied,
        acc_pandl: float = arg_not_supplied,
        are_you_really_sure: bool = False,
    ):
        """

        Used to create the initial capital series

        Will delete capital! So be careful

        If broker_account_value passed and total_capital not passed, then use maximum_capital

        acc_pandl defaults to zero if not passed

        Default is to start at HWM with broker account value, but you can modify this

        :return: None
        """
        self.delete_all_global_capital(are_you_really_sure=are_you_really_sure)

        if total_capital is arg_not_supplied:
            total_capital = broker_account_value

        if maximum_capital is arg_not_supplied:
            maximum_capital = total_capital

        if acc_pandl is arg_not_supplied:
            acc_pandl = 0

        date = datetime.datetime.now()

        self.capital_data.create_initial_capital(
            total_current_capital=total_capital,
            maximum_capital=maximum_capital,
            acc_pandl=acc_pandl,
            broker_account_value=broker_account_value,
            date=date,
        )

    def delete_recent_capital(
        self, last_date: datetime.datetime, are_you_sure: bool = False
    ):
        """
        Delete all capital entries on or after start date

        :param start_date: pd.datetime
        :return:
        """
        if not are_you_sure:
            self._capital_data.log.warning("You have to be sure to delete capital")
            raise Exception("You have to be sure!")

        self.capital_data.delete_recent_capital(last_date=last_date)

    def delete_all_global_capital(self, are_you_really_sure: bool = False):
        self.capital_data.delete_all_global_capital(
            are_you_really_sure=are_you_really_sure
        )
