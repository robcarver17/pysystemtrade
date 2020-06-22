from sysproduction.data.get_data import dataBlob
from syscore.objects import arg_not_supplied

class dataLocks(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("mongoLockData")
        self.data = data

    def is_instrument_locked(self, instrument_code):
        return self.data.db_lock.is_instrument_locked(instrument_code)

    def add_lock_for_instrument(self, instrument_code):
        return self.data.db_lock.add_lock_for_instrument(instrument_code)

    def remove_lock_for_instrument(self, instrument_code):
        return self.data.db_lock.remove_lock_for_instrument(instrument_code)

    def get_list_of_locked_instruments(self):
        return self.data.db_lock.get_list_of_locked_instruments()

    def _get_list_of_trade_limits_for_cursor(self, cursor):


        trade_limits = [(tradeLimit.from_dict(db_dict)) for db_dict in list_of_dicts]

        list_of_trade_limits = listOfTradeLimits(trade_limits)

        return list_of_trade_limits

class dataTradeLimits(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("mongoTradeLimitData")
        self.data = data

    def what_trade_is_possible(self, strategy_name, instrument_code, proposed_trade):
        return self.data.db_trade_limit.what_trade_is_possible(strategy_name, instrument_code, proposed_trade)

    def add_trade(self,  strategy_name, instrument_code, trade):
        return self.data.db_trade_limit.add_trade(strategy_name, instrument_code, trade)

    def remove_trade(self,  strategy_name, instrument_code, trade):
        return self.data.db_trade_limit.remove_trade(strategy_name, instrument_code, trade)

    def get_all_limits(self):
        return self.data.db_trade_limit.get_all_limits()

    def update_instrument_limit_with_new_limit(self, instrument_code, period_days, new_limit):
        self.data.db_trade_limit.update_instrument_limit_with_new_limit(instrument_code, period_days, new_limit)

    def reset_instrument_limit(self, instrument_code, period_days):
        self.data.db_trade_limit.reset_instrument_limit(instrument_code, period_days)

    def update_instrument_strategy_limit_with_new_limit(self, strategy_name, instrument_code, period_days, new_limit):
        self.data.db_trade_limit.update_instrument_strategy_limit_with_new_limit(strategy_name, instrument_code, period_days, new_limit)

    def reset_instrument_strategy_limit(self, strategy_name, instrument_code, period_days):
        self.data.db_trade_limit.reset_instrument_strategy_limit(strategy_name, instrument_code, period_days)

class diagOverrides(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("mongoOverrideData")
        self.data = data

    def get_dict_of_all_overrides(self):
        return self.data.db_override.get_dict_of_all_overrides()

    def get_cumulative_override_for_strategy_and_instrument(self, strategy_name, instrument_code):
        return self.data.db_override.get_cumulative_override_for_strategy_and_instrument( strategy_name, instrument_code)

class updateOverrides(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("mongoOverrideData")
        self.data = data

    def update_override_for_strategy(self, strategy_name, new_override):
        self.data.db_override.update_override_for_strategy(strategy_name, new_override)

    def update_override_for_strategy_instrument(self, strategy_name, instrument_code,  new_override):
        self.data.db_override.\
            update_override_for_strategy_instrument( strategy_name, instrument_code, new_override)

    def update_override_for_instrument(self, instrument_code, new_override):
        self.data.db_override. \
            update_override_for_instrument( instrument_code, new_override)

    def update_override_for_instrument_and_contractid(self, instrument_code, contract_id, new_override):

        self.data.\
            db_override.update_override_for_instrument_and_contractid(instrument_code, contract_id, new_override)
