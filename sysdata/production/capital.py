import datetime
import pandas as pd
from syscore.objects import arg_not_supplied, failure, success, missing_data
from sysdata.production.generic_timed_storage import (
    timedEntry,
    listOfEntries,
    listOfEntriesData,
)


class capitalEntry(timedEntry):
    def _setup_args_data(self):
        self._star_args = ["capital_value"]  # compulsory args

    def _name_(self):
        return "Capital"

    def _containing_data_class_name(self):
        return "sysdata.production.capital.capitalForStrategy"


class capitalForStrategy(listOfEntries):
    """
    A list of capitalEntry
    """

    def _entry_class(self):
        return capitalEntry


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

    def _name(self):
        return "capitalData"

    def _data_class_name(self):
        return "sysdata.production.capital.capitalForStrategy"

    def get_total_capital_pd_series(self):
        return self.get_capital_pd_series_for_strategy(GLOBAL_STRATEGY)

    def get_broker_account_value_pd_series(self):
        return self.get_capital_pd_series_for_strategy(BROKER_ACCOUNT_VALUE)

    def get_maximum_account_value_pd_series(self):
        return self.get_capital_pd_series_for_strategy(MAXIMUM_ACCOUNT_VALUE)

    def get_profit_and_loss_account_pd_series(self):
        return self.get_capital_pd_series_for_strategy(ACC_PROFIT_VALUES)

    def get_capital_pd_series_for_strategy(self, strategy_name):
        capital_series = self._get_series_for_args_dict(
            dict(strategy_name=strategy_name)
        )
        pd_series = capital_series.as_pd_df()
        return pd_series

    def get_current_total_capital(self):
        return self.get_current_capital_for_strategy(GLOBAL_STRATEGY)

    def get_broker_account_value(self):
        return self.get_current_capital_for_strategy(BROKER_ACCOUNT_VALUE)

    def get_current_maximum_account_value(self):
        return self.get_current_capital_for_strategy(MAXIMUM_ACCOUNT_VALUE)

    def get_current_pandl_account(self):
        return self.get_current_capital_for_strategy(ACC_PROFIT_VALUES)

    def get_current_capital_for_strategy(self, strategy_name):
        current_capital_entry = self.get_last_entry_for_strategy(strategy_name)
        if current_capital_entry is missing_data:
            return missing_data

        capital_value = current_capital_entry.capital_value

        return capital_value

    def get_date_of_last_entry_for_strategy(self, strategy_name):
        current_capital_entry = self.get_last_entry_for_strategy(strategy_name)
        if current_capital_entry is missing_data:
            return missing_data

        entry_date = current_capital_entry.date

        return entry_date

    def get_last_entry_for_strategy(self, strategy_name):
        current_capital_entry = self._get_current_entry_for_args_dict(
            dict(strategy_name=strategy_name)
        )
        return current_capital_entry

    def update_broker_account_value(
            self,
            new_capital_value,
            date=arg_not_supplied):
        return self.update_capital_value_for_strategy(
            BROKER_ACCOUNT_VALUE, new_capital_value, date=date
        )

    def update_profit_and_loss_account(
            self, new_capital_value, date=arg_not_supplied):
        return self.update_capital_value_for_strategy(
            ACC_PROFIT_VALUES, new_capital_value, date=date
        )

    def update_total_capital(self, new_capital_value, date=arg_not_supplied):
        return self.update_capital_value_for_strategy(
            GLOBAL_STRATEGY, new_capital_value, date=date
        )

    def update_maximum_capital(self, new_capital_value, date=arg_not_supplied):
        return self.update_capital_value_for_strategy(
            MAXIMUM_ACCOUNT_VALUE, new_capital_value, date=date
        )

    def update_capital_value_for_strategy(
        self, strategy_name, new_capital_value, date=arg_not_supplied
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
            return failure

    def get_list_of_strategies_with_capital(self):
        list_of_args_dict = self._get_list_of_args_dict()
        strategy_names = [d["strategy_name"] for d in list_of_args_dict]
        strategy_names = list(set(strategy_names))
        for strat_name in SPECIAL_NAMES:
            try:
                strategy_names.remove(strat_name)
            except IndexError:
                # Don't have to have capital defined
                pass

        return strategy_names

    def delete_last_capital_for_strategy(
            self, strategy_name, are_you_sure=False):
        self._delete_last_entry_for_args_dict(
            dict(strategy_name=strategy_name), are_you_sure=are_you_sure
        )

    def delete_all_capital_for_strategy(
            self, strategy_name, are_you_really_sure=False):
        self._delete_all_data_for_args_dict(
            dict(
                strategy_name=strategy_name),
            are_you_really_sure=are_you_really_sure)

    def delete_all_special_capital_entries(self, are_you_really_sure=False):
        if not are_you_really_sure:
            self.log.warn("You have to be really sure to delete all capital")
            return failure
        for strat_name in SPECIAL_NAMES:
            self.delete_all_capital_for_strategy(
                strat_name, are_you_really_sure=are_you_really_sure
            )

    def delete_recent_capital_for_total_strategy(
            self, start_date, are_you_sure=False):
        self.delete_recent_capital_for_strategy(
            GLOBAL_STRATEGY, start_date, are_you_sure=are_you_sure
        )

    def delete_recent_capital_for_maximum(
            self, start_date, are_you_sure=False):
        self.delete_recent_capital_for_strategy(
            MAXIMUM_ACCOUNT_VALUE, start_date, are_you_sure=are_you_sure
        )

    def delete_recent_capital_for_broker_value(
            self, start_date, are_you_sure=False):
        self.delete_recent_capital_for_strategy(
            BROKER_ACCOUNT_VALUE, start_date, are_you_sure=are_you_sure
        )

    def delete_recent_capital_for_pandl(self, start_date, are_you_sure=False):
        self.delete_recent_capital_for_strategy(
            ACC_PROFIT_VALUES, start_date, are_you_sure=are_you_sure
        )

    def delete_recent_capital_for_strategy(
        self, strategy_name, start_date, are_you_sure=False
    ):
        have_capital_to_delete = True
        while have_capital_to_delete:
            last_date = self.get_date_of_last_entry_for_strategy(strategy_name)
            if last_date is missing_data:
                break
            if last_date > start_date:
                self.delete_last_capital_for_strategy(
                    strategy_name, are_you_sure=are_you_sure
                )
            else:
                break
        return success


LIST_OF_COMPOUND_METHODS = ["full", "half", "fixed"]


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

        :param capital_data: capitalData instance or something that inherits from it
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

    def __repr__(self):
        return "capitalCalculationData for %s" % self._capital_data

    def get_all_capital_calcs(self):
        total_capital = self._capital_data.get_total_capital_pd_series()
        max_capital = self._capital_data.get_maximum_account_value_pd_series()
        acc_pandl = self._capital_data.get_profit_and_loss_account_pd_series()
        broker_acc = self._capital_data.get_broker_account_value_pd_series()

        if (
            total_capital is missing_data
            or max_capital is missing_data
            or acc_pandl is missing_data
            or broker_acc is missing_data
        ):
            return missing_data

        all_capital = pd.concat(
            [total_capital, max_capital, acc_pandl, broker_acc], axis=1
        )
        all_capital.columns = ["Actual", "Max", "Accumulated", "Broker"]

        return all_capital

    def get_total_capital_with_new_broker_account_value(
        self, broker_account_value, check_limit=0.1
    ):
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
        prev_broker_account_value = self._capital_data.get_broker_account_value()
        if prev_broker_account_value is missing_data:
            # No previous capital, need to set everything up
            self.create_initial_capital(
                broker_account_value, are_you_really_sure=True)
            prev_broker_account_value = broker_account_value

        profit_and_loss = broker_account_value - prev_broker_account_value

        abs_perc_change = abs(profit_and_loss / prev_broker_account_value)
        if abs_perc_change > check_limit:
            raise Exception(
                "New capital of %.0f is more than %.1f%% away from original of %.0f, limit is %.1f%%" %
                (broker_account_value, abs_perc_change * 100, prev_broker_account_value, check_limit, ))

        # Adjust capital calculations. This will also update capital
        new_total_capital, new_maximum_capital = self._capital_calculations(
            profit_and_loss
        )

        # Update broker account value and add p&l entry with synched dates
        date = datetime.datetime.now()
        self._capital_data.update_total_capital(new_total_capital, date=date)
        self._capital_data.update_maximum_capital(
            new_maximum_capital, date=date)
        self._capital_data.update_broker_account_value(
            broker_account_value, date=date)
        self._add_pandl_entry(profit_and_loss, date=date)

        return new_total_capital

    def _add_pandl_entry(self, profit_and_loss, date=arg_not_supplied):
        # Add P&L to accumulated p&l
        prev_acc_pandl = self._capital_data.get_current_pandl_account()
        new_acc_pandl = prev_acc_pandl + profit_and_loss
        self._capital_data.update_profit_and_loss_account(
            new_acc_pandl, date=date)

        return new_acc_pandl

    def _capital_calculations(self, profit_and_loss):
        """
        Calculate capital depending on method

        :param profit_and_loss: float
        :return: new capital
        """

        if self._calc_method == "full":
            new_total_capital, new_maximum_capital = self._full_capital_calculation(
                profit_and_loss)
        elif self._calc_method == "half":
            new_total_capital, new_maximum_capital = self._half_capital_calculation(
                profit_and_loss)
        elif self._calc_method == "fixed":
            new_total_capital, new_maximum_capital = self._fixed_capital_calculation(
                profit_and_loss)
        else:
            raise Exception(
                "Capital method should be one of full, half or fixed")

        return new_total_capital, new_maximum_capital

    def _full_capital_calculation(self, profit_and_loss):
        """
        Update capital accumallating all p&l

        :param profit_and_loss: float
        :return: new capital
        """

        prev_total_capital = self._capital_data.get_current_total_capital()
        new_total_capital = prev_total_capital + profit_and_loss

        if new_total_capital < 0:
            new_total_capital = 0

        # We don't really use maximum capital but set it to the same as capital
        # for tidieness
        new_maximum_capital = new_total_capital

        return new_total_capital, new_maximum_capital

    def _half_capital_calculation(self, profit_and_loss):
        """
        Update capital accumallating losses, but not profits about HWM (maximum capital)

        :param profit_and_loss: float
        :return: new capital
        """

        prev_total_capital = self._capital_data.get_current_total_capital()
        prev_maximum_capital = self._capital_data.get_current_maximum_account_value()

        new_total_capital = min(
            prev_total_capital + profit_and_loss, prev_maximum_capital
        )
        if new_total_capital < 0:
            new_total_capital = 0

        # Max is unchanged
        new_maximum_capital = prev_maximum_capital

        return new_total_capital, new_maximum_capital

    def _fixed_capital_calculation(self, profit_and_loss):
        """
        'Update' capital but capital is fixed

        :param profit_and_loss: float
        :return: new capital
        """

        prev_total_capital = self._capital_data.get_current_total_capital()
        new_total_capital = prev_total_capital

        # We don't really use maximum capital but set it to the same as capital
        # for tidieness
        new_maximum_capital = new_total_capital

        return new_total_capital, new_maximum_capital

    def adjust_broker_account_for_delta(self, delta_value):
        """
        If you have changed broker account value, for example because of a withdrawal, but don't want this to
        affect capital calculations

        A negative delta_value indicates a withdrawal (capital value falling) and vice versa

        :param value: change in account value to be ignore, a minus figure is a withdrawal, positive is deposit
        :return: None
        """

        prev_broker_account_value = self._capital_data.get_broker_account_value()
        if prev_broker_account_value is missing_data:
            self._capital_data.log.warn(
                "Can't apply a delta to broker account value, since no value in data"
            )

        broker_account_value = prev_broker_account_value + delta_value

        # Update broker account value
        self._capital_data.update_broker_account_value(broker_account_value)

        return success

    def modify_account_values(
        self,
        broker_account_value=arg_not_supplied,
        total_capital=arg_not_supplied,
        maximum_capital=arg_not_supplied,
        acc_pandl=arg_not_supplied,
        date=arg_not_supplied,
        are_you_sure=False,
    ):
        """
        Allow any account valuation to be modified
        Be careful! Only use if you really know what you are doing

        :param value: new_maximum_account_value
        :return: None
        """
        if not are_you_sure:
            self._capital_data.log.warn(
                "You need to be sure to modify capital!")
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        if broker_account_value is not arg_not_supplied:
            self._capital_data.update_broker_account_value(
                broker_account_value, date=date
            )

        if total_capital is not arg_not_supplied:
            self._capital_data.update_total_capital(total_capital, date=date)

        if maximum_capital is not arg_not_supplied:
            self._capital_data.update_maximum_capital(
                maximum_capital, date=date)

        if acc_pandl is not arg_not_supplied:
            self._capital_data.update_profit_and_loss_account(
                acc_pandl, date=date)

        return success

    def create_initial_capital(
        self,
        broker_account_value,
        total_capital=arg_not_supplied,
        maximum_capital=arg_not_supplied,
        acc_pandl=arg_not_supplied,
        are_you_really_sure=False,
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

        self._capital_data.update_total_capital(total_capital, date=date)
        self._capital_data.update_maximum_capital(maximum_capital, date=date)
        self._capital_data.update_broker_account_value(
            broker_account_value, date=date)
        self._capital_data.update_profit_and_loss_account(acc_pandl, date=date)

        return success

    def delete_recent_capital(self, start_date, are_you_sure=False):
        """
        Delete all capital entries on or after start date

        :param start_date: pd.datetime
        :return:
        """
        if not are_you_sure:
            self._capital_data.log.warn(
                "You have to be sure to delete capital")
            return failure

        self._capital_data.delete_recent_capital_for_total_strategy(
            start_date, are_you_sure=are_you_sure
        )
        self._capital_data.delete_recent_capital_for_maximum(
            start_date, are_you_sure=are_you_sure
        )
        self._capital_data.delete_recent_capital_for_broker_value(
            start_date, are_you_sure=are_you_sure
        )
        self._capital_data.delete_recent_capital_for_pandl(
            start_date, are_you_sure=are_you_sure
        )

        return success

    def delete_all_capital(self, are_you_really_sure=False):
        self._capital_data.delete_all_special_capital_entries(
            are_you_really_sure=are_you_really_sure
        )
