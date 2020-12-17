from syscore.objects import arg_not_supplied
from syscore.genutils import sign

from sysobjects.production.position_limits import positionLimitAndPosition
from sysdata.mongodb.mongo_lock_data import mongoLockData
from sysdata.mongodb.mongo_position_limits import mongoPositionLimitData
from sysdata.mongodb.mongo_trade_limits import mongoTradeLimitData
from sysdata.mongodb.mongo_override import mongoOverrideData
from sysdata.mongodb.mongo_IB_client_id import mongoIbBrokerClientIdData

from sysdata.data_blob import dataBlob
from sysproduction.data.positions import diagPositions
from sysobjects.production.strategy import instrumentStrategy, listOfInstrumentStrategies

class dataBrokerClientIDs(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoIbBrokerClientIdData)
        self.data = data

    def clear_all_clientids(self):
        self.data.db_ib_broker_client_id.clear_all_clientids()


class dataLocks(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoLockData)
        self.data = data

    def is_instrument_locked(self, instrument_code):
        return self.data.db_lock.is_instrument_locked(instrument_code)

    def add_lock_for_instrument(self, instrument_code):
        return self.data.db_lock.add_lock_for_instrument(instrument_code)

    def remove_lock_for_instrument(self, instrument_code):
        return self.data.db_lock.remove_lock_for_instrument(instrument_code)

    def get_list_of_locked_instruments(self):
        return self.data.db_lock.get_list_of_locked_instruments()


class dataTradeLimits(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoTradeLimitData)
        self.data = data

    def what_trade_is_possible(
            self,
            strategy_name,
            instrument_code,
            proposed_trade):
        return self.data.db_trade_limit.what_trade_is_possible(
            strategy_name, instrument_code, proposed_trade
        )

    def add_trade(self, strategy_name, instrument_code, trade):
        return self.data.db_trade_limit.add_trade(
            strategy_name, instrument_code, trade)

    def remove_trade(self, strategy_name, instrument_code, trade):
        return self.data.db_trade_limit.remove_trade(
            strategy_name, instrument_code, trade
        )

    def get_all_limits(self):
        return self.data.db_trade_limit.get_all_limits()

    def update_instrument_limit_with_new_limit(
        self, instrument_code, period_days, new_limit
    ):
        self.data.db_trade_limit.update_instrument_limit_with_new_limit(
            instrument_code, period_days, new_limit
        )

    def reset_instrument_limit(self, instrument_code, period_days):
        self.data.db_trade_limit.reset_instrument_limit(
            instrument_code, period_days)

    def update_instrument_strategy_limit_with_new_limit(
        self, strategy_name, instrument_code, period_days, new_limit
    ):
        self.data.db_trade_limit.update_instrument_strategy_limit_with_new_limit(
            strategy_name, instrument_code, period_days, new_limit)

    def reset_instrument_strategy_limit(
        self, strategy_name, instrument_code, period_days
    ):
        self.data.db_trade_limit.reset_instrument_strategy_limit(
            strategy_name, instrument_code, period_days
        )


class diagOverrides(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoOverrideData)
        self.data = data

    def get_dict_of_all_overrides(self):
        return self.data.db_override.get_dict_of_all_overrides()

    def get_cumulative_override_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        # FIXME REMOVE
        instrument_strategy = instrumentStrategy(strategy_name  =strategy_name,
            instrument_code=instrument_code)
        return \
            self.get_cumulative_override_for_instrument_strategy(instrument_strategy)

    def get_cumulative_override_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ):
        return \
            self.data.db_override.get_cumulative_override_for_instrument_strategy(
                instrument_strategy)


class updateOverrides(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoOverrideData)
        self.data = data

    def update_override_for_strategy(self, strategy_name, new_override):
        self.data.db_override.update_override_for_strategy(
            strategy_name, new_override)

    def update_override_for_strategy_instrument(
        self, strategy_name, instrument_code, new_override
    ):
        # FIXME REMOVE
        instrument_strategy = instrumentStrategy(strategy_name  =strategy_name,
            instrument_code=instrument_code)

        self.update_override_for_instrument_strategy(instrument_strategy, new_override)

    def update_override_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy, new_override
    ):
        self.data.db_override.update_override_for_instrument_strategy(
            instrument_strategy, new_override
        )

    def update_override_for_instrument(self, instrument_code, new_override):
        self.data.db_override.update_override_for_instrument(
            instrument_code, new_override
        )

    def update_override_for_instrument_and_contractid(
        self, instrument_code, contract_id, new_override
    ):

        self.data.db_override.update_override_for_instrument_and_contractid(
            instrument_code, contract_id, new_override
        )


class dataPositionLimits:
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        data.add_class_object(mongoPositionLimitData)
        self.data = data

    def cut_down_proposed_instrument_trade_okay(
            self,
            instrument_trade):

            strategy_name = instrument_trade.strategy_name
            instrument_code = instrument_trade.instrument_code
            proposed_trade = instrument_trade.trade.as_int()

            ## want to CUT DOWN rather than bool possible trades
            ## FIXME:
            ## underneath should be using tradeQuantity and position objects
            ## these will handle abs cases plus legs if required in future
            # :FIXME
            instrument_strategy = instrumentStrategy(strategy_name=strategy_name,
                                                     instrument_code=instrument_code)

            max_trade_ok_against_instrument_strategy = \
                self.check_if_proposed_trade_okay_against_instrument_strategy_constraint(instrument_strategy,
                                                                                        proposed_trade)
            max_trade_ok_against_instrument = \
                self.check_if_proposed_trade_okay_against_instrument_constraint(instrument_code,
                                                                                proposed_trade)

            ## FIXME THIS IS UGLY WOULD BE BETTER IF DONE INSIDE TRADE SIZE OBJECT
            mini_max_trade = sign(proposed_trade) * \
                             min([abs(max_trade_ok_against_instrument),
                            abs(max_trade_ok_against_instrument_strategy)])

            instrument_trade = instrument_trade.replace_trade_only_use_for_unsubmitted_trades(mini_max_trade)

            return instrument_trade

    def check_if_proposed_trade_okay_against_instrument_strategy_constraint(
            self,
            instrument_strategy: instrumentStrategy,
            proposed_trade: int) -> int:

            position_and_limit = self.get_limit_and_position_for_instrument_strategy(instrument_strategy)
            max_trade_ok_against_instrument_strategy =  position_and_limit.what_trade_is_possible(proposed_trade)

            return max_trade_ok_against_instrument_strategy

    def check_if_proposed_trade_okay_against_instrument_constraint(
            self,
            instrument_code: str,
            proposed_trade: int) -> int:

            position_and_limit = self.get_limit_and_position_for_instrument(instrument_code)
            max_trade_ok_against_instrument = position_and_limit.what_trade_is_possible(proposed_trade)

            return max_trade_ok_against_instrument

    def get_all_instrument_limits_and_positions(self) -> list:
        instrument_list = self.get_all_relevant_instruments()
        list_of_limit_and_position = [self.get_limit_and_position_for_instrument(instrument_code)
                                      for instrument_code in instrument_list]

        return list_of_limit_and_position

    def get_all_relevant_instruments(self):
        ## want limits both for the union of instruments where we have positions & limits are set
        instrument_list_held = self.get_instruments_with_current_positions()
        instrument_list_limits = self.get_instruments_with_position_limits()

        instrument_list = list(set(instrument_list_held+instrument_list_limits))

        return instrument_list

    def get_instruments_with_current_positions(self) -> list:
        diag_positions = diagPositions(self.data)
        instrument_list = diag_positions.get_list_of_instruments_with_current_positions()

        return instrument_list

    def get_instruments_with_position_limits(self) -> list:
        instrument_list = self.data.db_position_limit.get_all_instruments_with_limits()

        return instrument_list

    def get_all_strategy_instrument_limits_and_positions(self) -> list:
        instrument_strategy_list = self.get_all_relevant_strategy_instruments()
        list_of_limit_and_position = [self.get_limit_and_position_for_instrument_strategy(instrument_strategy)
                            for instrument_strategy in instrument_strategy_list]

        return list_of_limit_and_position

    def get_all_relevant_strategy_instruments(self)-> listOfInstrumentStrategies:
        ## want limits both for the union of strategy/instruments where we have positions & limits are set
        # return list of tuple strategy_name, instrument_code
        strategy_instrument_list_held = self.get_instrument_strategies_with_current_positions()
        strategy_instrument_list_limits = self.get_strategy_instruments_with_position_limits()

        strategy_instrument_list = strategy_instrument_list_held.unique_join_with_other_list(strategy_instrument_list_limits)

        return strategy_instrument_list

    def get_instrument_strategies_with_current_positions(self) -> listOfInstrumentStrategies:
        diag_positions = diagPositions(self.data)
        strategy_instrument_list_held = diag_positions.get_list_of_strategies_and_instruments_with_positions()

        return strategy_instrument_list_held

    def get_strategy_instruments_with_position_limits(self) -> listOfInstrumentStrategies:
        # return list of tuple strategy_name, instrument_code
        strategy_instrument_list_limits = self.data.db_position_limit.get_all_instrument_strategies_with_limits()

        return strategy_instrument_list_limits

    def get_limit_and_position_for_instrument_strategy(self, instrument_strategy: instrumentStrategy):
        limit_object = self.get_position_limit_object_for_instrument_strategy(instrument_strategy)
        position = self.get_current_position_for_instrument_strategy(instrument_strategy)

        position_and_limit = positionLimitAndPosition(limit_object, position)

        return position_and_limit

    def get_limit_and_position_for_instrument(self, instrument_code):
        limit_object = self.get_position_limit_object_for_instrument(instrument_code)
        position = self.get_current_position_for_instrument(instrument_code)

        position_and_limit = positionLimitAndPosition(limit_object, position)

        return position_and_limit

    def get_position_limit_object_for_instrument_strategy(self, instrument_strategy: instrumentStrategy):
        limit_object = self.data.db_position_limit.get_position_limit_object_for_instrument_strategy(instrument_strategy)
        return limit_object

    def get_position_limit_object_for_instrument(self, instrument_code):
        limit_object = self.data.db_position_limit.get_position_limit_object_for_instrument(instrument_code)

        return limit_object

    def get_current_position_for_instrument(self, instrument_code):
        diag_positions = diagPositions(self.data)
        position = diag_positions.get_current_instrument_position_across_strategies(instrument_code)

        return position

    def get_current_position_for_instrument_strategy(self, instrument_strategy: instrumentStrategy):
        diag_positions = diagPositions(self.data)
        position = diag_positions.get_current_position_for_instrument_strategy(instrument_strategy)

        return position

    def set_abs_position_limit_for_strategy_instrument(self, strategy_name, instrument_code, new_position_limit):

        #FIXME DELETE
        instrument_strategy = instrumentStrategy(strategy_name=strategy_name, instrument_code=instrument_code)
        self.set_position_limit_for_instrument_strategy(instrument_strategy, new_position_limit)

    def set_position_limit_for_instrument_strategy(self, instrument_strategy: instrumentStrategy,
                                                   new_position_limit: int):

        self.data.db_position_limit.set_position_limit_for_instrument_strategy(instrument_strategy,
                                                                               new_position_limit)


    def set_abs_position_limit_for_instrument(self, instrument_code, new_position_limit):

        self.data.db_position_limit.set_position_limit_for_instrument(instrument_code, new_position_limit)

    def delete_position_limit_for_strategy_instrument(self, strategy_name:str,
                                                      instrument_code: str):
        ## FIXME DELETE
        instrument_strategy = instrumentStrategy(strategy_name=strategy_name, instrument_code=instrument_code)
        self.delete_position_limit_for_instrument_strategy(instrument_strategy)

    def delete_position_limit_for_instrument_strategy(self, instrument_strategy: instrumentStrategy):

        self.data.db_position_limit.delete_position_limit_for_instrument_strategy(instrument_strategy)


    def delete_position_limit_for_instrument(self, instrument_code: str):

        self.data.db_position_limit.delete_position_limit_for_instrument(instrument_code)
