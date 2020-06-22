
from syscore.objects import missing_order, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, missing_contract, missing_data, rolling_cant_trade, ROLL_PSEUDO_STRATEGY, missing_order, order_is_in_status_reject_modification, order_is_in_status_finished, locked_order, order_is_in_status_modified, resolve_function

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysproduction.data.positions import diagPositions
from sysproduction.data.controls import dataLocks
from sysproduction.data.broker import dataBroker

class stackHandlerChecks(stackHandlerCore):
    ## Do various checks
    ## If bad things happen we warn the user, and for some things do not allow any more trading to take place
    ##   until fixed.
    ## We do these regularly, but also at the end of the day (daily reporting)

    def check_internal_position_break(self):

        diag_positions = diagPositions(self.data)
        breaks = diag_positions.get_list_of_breaks_between_contract_and_strategy_positions()
        for tradeable_object in breaks:
            self.log_and_lock_position_break(tradeable_object, "Internal")


    def check_external_position_break(self):
        data_broker = dataBroker(self.data)
        breaks = data_broker.get_list_of_breaks_between_broker_and_db_contract_positions()
        for tradeable_object in breaks:
            self.log_and_lock_position_break(tradeable_object, "External")

    def log_and_lock_position_break(self, tradeable_object, type_of_break):
        instrument_code = tradeable_object.instrument_code
        data_locks = dataLocks(self.data)
        if data_locks.is_instrument_locked(instrument_code):
            return None
        self.log.critical("%s Break for %s: locking" % (type_of_break, str(tradeable_object)))
        data_locks.add_lock_for_instrument(instrument_code)

    def check_any_missing_broker_order(self):
        list_of_broker_orderids = self.broker_stack.get_list_of_order_ids()
        for broker_order_id in list_of_broker_orderids:
            self.check_if_broker_order_is_missing(broker_order_id)

    def check_if_broker_order_is_missing(self, broker_order_id):
        broker_order = self.broker_stack.get_order_with_id_from_stack(broker_order_id)
        data_broker = dataBroker(self.data)
        matching_order = data_broker.match_db_broker_order_to_order_from_brokers(broker_order)
        if matching_order is missing_order:
            log = broker_order.log_with_attributes(self.log)
            log.warn("Order %s is not with brokers" % str(broker_order))
        return None

    def check_any_orphan_broker_order(self):
        data_broker = dataBroker(self.data)
        list_of_broker_orders_to_match = data_broker.get_list_of_orders_for_matching()
        for broker_order in list_of_broker_orders_to_match:
            self.check_if_orphan_broker_order(broker_order)

    def check_if_orphan_broker_order(self, broker_order):
        broker_tempid = broker_order.broker_tempid
        matched_order = self.broker_stack.find_order_with_broker_tempid(broker_tempid)
        if matched_order is missing_order:
            log = broker_order.log_with_attributes(self.log)
            log.warn("Order %s is with brokers but not in database" % str(broker_order))
        return None

