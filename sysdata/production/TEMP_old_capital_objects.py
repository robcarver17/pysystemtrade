from copy import copy
import datetime
import pandas as pd

from syscore.exceptions import missingData
from syscore.constants import arg_not_supplied, failure
from syscore.pandas.pdutils import uniquets

from sysdata.data_blob import dataBlob
from sysdata.production.capital import capitalEntry, capitalForStrategy
from sysdata.production.timed_storage import listOfEntriesData

from sysobjects.production.capital import (
    LIST_OF_COMPOUND_METHODS,
    totalCapitalUpdater,
)


## All capital is stored by strategy, but some 'strategies' actually relate to the total global account

GLOBAL_STRATEGY = "_GLOBAL"
BROKER_ACCOUNT_VALUE = "_BROKER"
MAXIMUM_ACCOUNT_VALUE = "_MAX"
ACC_PROFIT_VALUES = "_PROFIT"

SPECIAL_NAMES = [
    GLOBAL_STRATEGY,
    BROKER_ACCOUNT_VALUE,
    MAXIMUM_ACCOUNT_VALUE,
    ACC_PROFIT_VALUES,
]


class capitalData(listOfEntriesData):
    """
    Store and retrieve the capital assigned to a particular strategy

    A separate process is required to map from account value to strategy capital

    We also store the total account value (GLOBAL STRATEGY), broker account value (BROKER_ACCOUNT_VALUE),
       and for half compounding purposes MAXIMUM_ACCOUNT_VALUE
    """

    def _data_class_name(self) -> str:
        return "sysdata.production.TEMP_old_capital_objects.capitalForStrategy"

    def get_total_capital_pd_series(self) -> pd.Series:
        return self.get_capital_pd_series_for_strategy(GLOBAL_STRATEGY)

    def get_broker_account_value_pd_series(self) -> pd.Series:
        return self.get_capital_pd_series_for_strategy(BROKER_ACCOUNT_VALUE)

    def get_maximum_account_value_pd_series(self) -> pd.Series:
        return self.get_capital_pd_series_for_strategy(MAXIMUM_ACCOUNT_VALUE)

    def get_profit_and_loss_account_pd_series(self) -> pd.Series:
        return self.get_capital_pd_series_for_strategy(ACC_PROFIT_VALUES)

    def get_capital_pd_series_for_strategy(self, strategy_name: str) -> pd.Series:
        capital_series = self.get_capital_series_for_strategy(strategy_name)
        pd_series = capital_series.as_pd_df()
        pd_series = uniquets(pd_series).squeeze()
        return pd_series

    def get_capital_series_for_strategy(self, strategy_name: str) -> capitalForStrategy:
        capital_series = self._get_series_for_args_dict(
            dict(strategy_name=strategy_name)
        )

        return capital_series

    def get_current_total_capital(self) -> float:
        return self.get_current_capital_for_strategy(GLOBAL_STRATEGY)

    def get_broker_account_value(self) -> float:
        return self.get_current_capital_for_strategy(BROKER_ACCOUNT_VALUE)

    def get_current_maximum_account_value(self) -> float:
        return self.get_current_capital_for_strategy(MAXIMUM_ACCOUNT_VALUE)

    def get_current_pandl_account(self) -> float:
        return self.get_current_capital_for_strategy(ACC_PROFIT_VALUES)

    def get_current_capital_for_strategy(self, strategy_name: str) -> float:
        current_capital_entry = self.get_last_entry_for_strategy(strategy_name)

        capital_value = current_capital_entry.capital_value

        return capital_value

    def get_date_of_last_entry_for_strategy(
        self, strategy_name: str
    ) -> datetime.datetime:
        current_capital_entry = self.get_last_entry_for_strategy(strategy_name)
        entry_date = current_capital_entry.date

        return entry_date

    def get_last_entry_for_strategy(self, strategy_name: str) -> capitalEntry:
        current_capital_entry = self._get_current_entry_for_args_dict(
            dict(strategy_name=strategy_name)
        )
        return current_capital_entry

    def update_broker_account_value(
        self,
        new_capital_value: float,
        date: datetime.datetime = arg_not_supplied,
    ):
        ## Update account value but also propogate
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        self.update_capital_value_for_strategy(
            BROKER_ACCOUNT_VALUE, new_capital_value, date=date
        )

    def update_profit_and_loss_account(
        self, new_capital_value: float, date: datetime.datetime = arg_not_supplied
    ):

        self.update_capital_value_for_strategy(
            ACC_PROFIT_VALUES, new_capital_value, date=date
        )

    def update_total_capital(
        self, new_capital_value: float, date: datetime.datetime = arg_not_supplied
    ):
        self.update_capital_value_for_strategy(
            GLOBAL_STRATEGY, new_capital_value, date=date
        )

    def update_maximum_capital(
        self, new_capital_value: float, date: datetime.datetime = arg_not_supplied
    ):
        return self.update_capital_value_for_strategy(
            MAXIMUM_ACCOUNT_VALUE, new_capital_value, date=date
        )

    def update_capital_value_for_strategy(
        self,
        strategy_name: str,
        new_capital_value: float,
        date: datetime.datetime = arg_not_supplied,
    ):
        new_capital_entry = capitalEntry(new_capital_value, date=date)
        try:
            self._update_entry_for_args_dict(
                new_capital_entry, dict(strategy_name=strategy_name)
            )
        except Exception as e:
            self.log.warn(
                "Error %s when updating capital for %s with %s"
                % (str(e), strategy_name, str(new_capital_entry))
            )

    def get_list_of_strategies_with_capital(self) -> list:
        strategy_names = (
            self._get_list_of_strategies_with_capital_including_reserved_names()
        )
        for strat_name in SPECIAL_NAMES:
            try:
                strategy_names.remove(strat_name)
            except IndexError:
                # Don't have to have capital defined
                pass

        return strategy_names

    def _get_list_of_strategies_with_capital_including_reserved_names(self) -> list:
        list_of_args_dict = self._get_list_of_args_dict()
        strategy_names = [d["strategy_name"] for d in list_of_args_dict]
        strategy_names = list(set(strategy_names))

        return strategy_names

    def delete_last_capital_for_strategy(self, strategy_name: str, are_you_sure=False):

        self._delete_last_entry_for_args_dict(
            dict(strategy_name=strategy_name), are_you_sure=are_you_sure
        )

    def delete_all_capital_for_strategy(
        self, strategy_name: str, are_you_really_sure=False
    ):

        self._delete_all_data_for_args_dict(
            dict(strategy_name=strategy_name), are_you_really_sure=are_you_really_sure
        )

    def delete_all_special_capital_entries(self, are_you_really_sure=False):
        for strat_name in SPECIAL_NAMES:
            self.delete_all_capital_for_strategy(
                strat_name, are_you_really_sure=are_you_really_sure
            )

    def delete_recent_capital_for_total_strategy(
        self, start_date: datetime.datetime, are_you_sure=False
    ):
        self.delete_recent_capital_for_strategy(
            GLOBAL_STRATEGY, start_date, are_you_sure=are_you_sure
        )

    def delete_recent_capital_for_maximum(
        self, start_date: datetime.datetime, are_you_sure=False
    ):
        self.delete_recent_capital_for_strategy(
            MAXIMUM_ACCOUNT_VALUE, start_date, are_you_sure=are_you_sure
        )

    def delete_recent_capital_for_broker_value(
        self, start_date: datetime.datetime, are_you_sure=False
    ):
        self.delete_recent_capital_for_strategy(
            BROKER_ACCOUNT_VALUE, start_date, are_you_sure=are_you_sure
        )

    def delete_recent_capital_for_pandl(
        self, start_date: datetime.datetime, are_you_sure=False
    ):
        self.delete_recent_capital_for_strategy(
            ACC_PROFIT_VALUES, start_date, are_you_sure=are_you_sure
        )

    def delete_recent_capital_for_strategy(
        self, strategy_name: str, start_date: datetime.datetime, are_you_sure=False
    ):
        have_capital_to_delete = True
        while have_capital_to_delete:
            try:
                last_date_in_data = self.get_date_of_last_entry_for_strategy(
                    strategy_name
                )
            except missingData:
                ## gone to the start, nothing left
                break
            if last_date_in_data < start_date:
                # before the start date, so don't want to delete
                break
            else:
                self.delete_last_capital_for_strategy(
                    strategy_name, are_you_sure=are_you_sure
                )


from sysdata.mongodb.mongo_timed_storage import mongoListOfEntriesData

CAPITAL_COLLECTION = "capital"


class mongoCapitalData(capitalData, mongoListOfEntriesData):
    """
    Read and write data class to get capital for each strategy


    """

    @property
    def _collection_name(self):
        return CAPITAL_COLLECTION

    @property
    def _data_name(self):
        return "mongoStrategyCapitalData"


class totalCapitalCalculationData(object):
    """
    This object allows us to calculate available total capital from previous capital and profits

    It uses the special strategy names GLOBAL_STRATEGY and BROKER_ACCOUNT_VALUE, MAXIMUM and PROFIT

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
    def capital_data(self):
        return self._capital_data

    @property
    def calc_method(self):
        return self._calc_method

    def __repr__(self):
        return "capitalCalculationData for %s" % self._capital_data

    def get_returns_as_account_curve(self) -> pd.DataFrame:
        raise NotImplementedError()

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

    def get_current_total_capital(self):
        return self.capital_data.get_current_total_capital()

    def get_total_capital(self) -> pd.Series:
        return self.capital_data.get_total_capital_pd_series()

    def get_profit_and_loss_account(self) -> pd.Series():
        return self.capital_data.get_profit_and_loss_account_pd_series()

    def get_broker_account(self) -> pd.Series:
        return self.capital_data.get_broker_account_value_pd_series()

    def get_maximum_account(self) -> pd.Series:
        return self.capital_data.get_maximum_account_value_pd_series()

    def get_all_capital_calcs(self) -> pd.DataFrame:
        total_capital = self.get_total_capital()
        max_capital = self.get_maximum_account()
        acc_pandl = self.get_profit_and_loss_account()
        broker_acc = self.get_broker_account()

        all_capital = pd.concat(
            [total_capital, max_capital, acc_pandl, broker_acc], axis=1
        )
        all_capital.columns = ["Actual", "Max", "Accumulated", "Broker"]

        return all_capital

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
        prev_broker_account_value = (
            self._get_prev_broker_account_value_create_if_no_data(
                new_broker_account_value
            )
        )
        prev_maximum_capital = self.capital_data.get_current_maximum_account_value()
        prev_total_capital = self.capital_data.get_current_total_capital()

        capital_updater = totalCapitalUpdater(
            new_broker_account_value=new_broker_account_value,
            prev_total_capital=prev_total_capital,
            prev_maximum_capital=prev_maximum_capital,
            prev_broker_account_value=prev_broker_account_value,
            calc_method=calc_method,
        )

        return capital_updater

    def _get_prev_broker_account_value_create_if_no_data(
        self, new_broker_account_value: float
    ) -> float:
        try:
            prev_broker_account_value = self.capital_data.get_broker_account_value()
        except missingData:
            # No previous capital, need to set everything up
            self.create_initial_capital(
                new_broker_account_value, are_you_really_sure=True
            )
            prev_broker_account_value = copy(new_broker_account_value)

        return prev_broker_account_value

    def _update_capital_data_after_pandl_event(
        self, capital_updater: totalCapitalUpdater
    ):

        # Update broker account value and add p&l entry with synched dates
        date = datetime.datetime.now()

        new_total_capital = capital_updater.new_total_capital
        new_maximum_capital = capital_updater.new_maximum_capital
        new_broker_account_value = capital_updater.new_broker_account_value
        profit_and_loss = capital_updater.profit_and_loss

        self.capital_data.update_total_capital(new_total_capital, date=date)
        self.capital_data.update_maximum_capital(new_maximum_capital, date=date)
        self.capital_data.update_broker_account_value(
            new_broker_account_value, date=date
        )

        self._update_pandl(profit_and_loss, date=date)

    def _update_pandl(self, profit_and_loss: float, date: datetime.datetime):

        # Add P&L to accumulated p&l
        prev_acc_pandl = self._capital_data.get_current_pandl_account()
        new_acc_pandl = prev_acc_pandl + profit_and_loss
        self._capital_data.update_profit_and_loss_account(new_acc_pandl, date=date)

    def adjust_broker_account_for_delta(self, delta_value: float):
        """
        If you have changed broker account value, for example because of a withdrawal, but don't want this to
        affect capital calculations

        A negative delta_value indicates a withdrawal (capital value falling) and vice versa

        :param value: change in account value to be ignore, a minus figure is a withdrawal, positive is deposit
        :return: None
        """

        try:
            prev_broker_account_value = self.capital_data.get_broker_account_value()
        except missingData:
            self._capital_data.log.warn(
                "Can't apply a delta to broker account value, since no value in data"
            )
            raise

        broker_account_value = prev_broker_account_value + delta_value

        # Update broker account value
        self.modify_account_values(
            broker_account_value=broker_account_value, propagate=True, are_you_sure=True
        )

    def modify_account_values(
        self,
        broker_account_value: float = arg_not_supplied,
        total_capital: float = arg_not_supplied,
        maximum_capital: float = arg_not_supplied,
        acc_pandl: float = arg_not_supplied,
        date: datetime.datetime = arg_not_supplied,
        are_you_sure: bool = False,
        propagate: bool = True,
    ):
        """
        Allow any account valuation to be modified
        Be careful! Only use if you really know what you are doing

        :param value: new_maximum_account_value
        :return: None
        """
        if not are_you_sure:
            self._capital_data.log.warn("You need to be sure to modify capital!")
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        if broker_account_value is not arg_not_supplied:
            self.capital_data.update_broker_account_value(
                broker_account_value, date=date
            )
        elif propagate:
            self.propagate_broker_account(date)

        if total_capital is not arg_not_supplied:
            self.capital_data.update_total_capital(total_capital, date=date)
        elif propagate:
            self.propagate_total_capital(date)

        if maximum_capital is not arg_not_supplied:
            self.capital_data.update_maximum_capital(maximum_capital, date=date)
        elif propagate:
            self.propagate_maximum_account_value(date)

        if acc_pandl is not arg_not_supplied:
            self.capital_data.update_profit_and_loss_account(acc_pandl, date=date)
        elif propagate:
            self.propagate_current_pandl(date)

    def propagate_total_capital(self, date):
        current_total_capital = self.get_current_total_capital()
        self.capital_data.update_total_capital(current_total_capital, date)

    def propagate_maximum_account_value(self, date):
        current_max_capital = self.capital_data.get_current_maximum_account_value()
        self.capital_data.update_maximum_capital(current_max_capital, date)

    def propagate_current_pandl(self, date):
        current_pandl = self.capital_data.get_current_pandl_account()
        self.capital_data.update_profit_and_loss_account(current_pandl, date)

    def propagate_broker_account(self, date):
        broker_account_value = self.capital_data.get_broker_account_value()
        self.capital_data.update_broker_account_value(broker_account_value, date=date)

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
        self.delete_all_capital(are_you_really_sure=are_you_really_sure)

        if total_capital is arg_not_supplied:
            total_capital = broker_account_value

        if maximum_capital is arg_not_supplied:
            maximum_capital = total_capital

        if acc_pandl is arg_not_supplied:
            acc_pandl = 0

        date = datetime.datetime.now()

        self.capital_data.update_total_capital(total_capital, date=date)
        self.capital_data.update_maximum_capital(maximum_capital, date=date)
        self.capital_data.update_broker_account_value(broker_account_value, date=date)
        self.capital_data.update_profit_and_loss_account(acc_pandl, date=date)

    def delete_recent_capital(
        self, start_date: datetime.datetime, are_you_sure: bool = False
    ):
        """
        Delete all capital entries on or after start date

        :param start_date: pd.datetime
        :return:
        """
        if not are_you_sure:
            self._capital_data.log.warn("You have to be sure to delete capital")
            return failure

        self.capital_data.delete_recent_capital_for_total_strategy(
            start_date, are_you_sure=are_you_sure
        )
        self.capital_data.delete_recent_capital_for_maximum(
            start_date, are_you_sure=are_you_sure
        )
        self.capital_data.delete_recent_capital_for_broker_value(
            start_date, are_you_sure=are_you_sure
        )
        self.capital_data.delete_recent_capital_for_pandl(
            start_date, are_you_sure=are_you_sure
        )

    def delete_all_capital(self, are_you_really_sure: bool = False):
        self._capital_data.delete_all_special_capital_entries(
            are_you_really_sure=are_you_really_sure
        )


def get_dict_of_capital_by_strategy():
    data = dataBlob()
    data.add_class_object(mongoCapitalData)
    old_data_capital = data.db_capital
    strategy_list = old_data_capital.get_list_of_strategies_with_capital()
    dict_of_capital = dict(
        [
            (
                strategy_name,
                old_data_capital.get_capital_pd_series_for_strategy(strategy_name),
            )
            for strategy_name in strategy_list
        ]
    )

    return dict_of_capital


def get_old_capital():
    data = dataBlob()
    data.add_class_object(mongoCapitalData)
    old_data_capital = data.db_capital
    cap_calculator = totalCapitalCalculationData(old_data_capital)

    original_capital_pd = cap_calculator.get_all_capital_calcs()

    return original_capital_pd


def delete_old_total_capital():
    data = dataBlob()
    data.add_class_object(mongoCapitalData)
    old_data_capital = data.db_capital
    old_data_capital.delete_all_special_capital_entries(are_you_really_sure=True)


def delete_old_capital_for_strategy(strategy_name):
    data = dataBlob()
    data.add_class_object(mongoCapitalData)
    old_data_capital = data.db_capital
    old_data_capital.delete_all_capital_for_strategy(
        strategy_name, are_you_really_sure=True
    )
