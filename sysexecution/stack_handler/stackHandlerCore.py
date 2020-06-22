"""
Stack handler is a giant object, so we split it up into files/classes

This 'core' is inherited by all the other classes and just initialises, plus does some common functions

"""
from syscore.objects import arg_not_supplied, failure, success, duplicate_order, no_children

from sysproduction.data.orders import dataOrders
from sysproduction.data.get_data import dataBlob
from sysproduction.data.controls import dataTradeLimits

class stackHandlerCore(object):
    def __init__(self, data=arg_not_supplied):
        if data is arg_not_supplied:
            data = dataBlob()

        order_data = dataOrders(data)

        instrument_stack = order_data.instrument_stack()
        contract_stack = order_data.contract_stack()
        broker_stack = order_data.broker_stack()

        self.instrument_stack = instrument_stack
        self.contract_stack = contract_stack
        self.broker_stack = broker_stack

        self.order_data = order_data
        self.data = data
        self.log = data.log

    def add_children_to_stack_and_child_id_to_parent(self, parent_stack, child_stack, parent_order, list_of_child_orders):
        parent_log = parent_order.log_with_attributes(self.log)
        list_of_child_ids = child_stack.put_list_of_orders_on_stack(list_of_child_orders)

        if list_of_child_ids is failure:
            parent_log.msg("Failed to add child orders %s for parent order %s" % (str(list_of_child_orders),
                                                                                          str(parent_order)))
            return failure


        for child_order, child_id in zip(list_of_child_orders, list_of_child_ids):
            child_log = child_order.log_with_attributes(parent_log)
            child_log.msg("Put child order %s on stack with ID %d from parent order %s" % (str(child_order),
                                                                                          child_id,
                                                                                          str(parent_order)))
        result = parent_stack.add_children_to_order(parent_order.order_id, list_of_child_ids)
        if result is not success:
            parent_log.msg("Error %s when adding children to instrument order %s" % (str(result), str(parent_order)))
            return failure

        return success

    def add_parent_and_list_of_child_orders_to_stack(self, parent_stack, child_stack,
                                                               parent_order, list_of_child_orders):

        parent_log = parent_order.log_with_attributes(self.log)
        # Do as a transaction: if everything doesn't go to plan can roll back
        parent_order.lock_order()
        parent_order_id = parent_stack.put_order_on_stack(parent_order, allow_zero_orders=True)

        if type(parent_order_id) is not int:
            if parent_order_id is duplicate_order:
                # Probably already done this
                return success
            else:
                parent_log.msg("Couldn't put roll order %s on instrument order stack error %s" % (str(parent_order),
                                                                                           str(parent_order_id)))
            return failure

        ## Add parent order to children
        for child_order in list_of_child_orders:
            child_order.parent = parent_order_id

        # Do as a transaction: if everything doesn't go to plan can roll back
        # if this try fails we will roll back the instrument commit
        try:

            parent_log.msg("List of roll contract orders spawned %s" % str(list_of_child_orders))
            list_of_child_order_ids = child_stack.put_list_of_orders_on_stack(list_of_child_orders, unlock_when_finished=False)

            if list_of_child_order_ids is failure:
                parent_log.msg("Failed to add roll contract orders to stack %s" % (str(list_of_child_orders)))

                ## We create this empty list so we know there is nothing to roll back
                ## The child stack will have already rolled back any child orders that were put on
                list_of_child_order_ids = []
                raise Exception

            for child_order, order_id in zip(list_of_child_orders, list_of_child_order_ids):
                child_log = child_order.log_with_attributes(parent_log)
                child_log.msg("Put child order %s on stack with ID %d from parent order %s" % (str(child_order),
                                                                                              order_id,
                                                                                              str(parent_order)))

            parent_stack._unlock_order_on_stack(parent_order_id)
            result = parent_stack.add_children_to_order(parent_order_id, list_of_child_order_ids)
            if result is not success:
                parent_log.msg("Error %s when adding children to parent order %s" % (str(result), str(parent_order)))
                raise Exception

            child_stack.unlock_list_of_orders(list_of_child_order_ids)

        except:
            ## Roll back parent order
            ## Might be still locked
            parent_stack._unlock_order_on_stack(parent_order_id)
            parent_stack.deactivate_order(parent_order_id)
            parent_stack.remove_order_with_id_from_stack(parent_order_id)

            # If any children, roll them back also
            if len(list_of_child_order_ids)>0:
                child_stack.rollback_list_of_orders_on_stack(list_of_child_order_ids)

            return failure

    def get_all_children_and_grandchildren_for_instrument_order_id(self, instrument_order_id):

        instrument_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)
        list_of_contract_order_id = instrument_order.children
        if list_of_contract_order_id is no_children:
            list_of_contract_order_id = []

        list_of_broker_order_id = []
        list_of_contract_orders = []

        for contract_order_id in list_of_contract_order_id:
            contract_order = self.contract_stack.get_order_with_id_from_stack(contract_order_id)
            list_of_contract_orders.append(self.contract_stack.get_order_with_id_from_stack(contract_order_id))

            broker_order_children = contract_order.children
            if broker_order_children is not no_children:
                list_of_broker_order_id = list_of_broker_order_id+broker_order_children

        return list_of_broker_order_id, list_of_contract_order_id



    def what_contract_trade_is_possible(self, proposed_order):
        log = proposed_order.log_with_attributes(self.log)
        data_trade_limits = dataTradeLimits(self.data)
        strategy_name = proposed_order.strategy_name
        instrument_code = proposed_order.instrument_code

        possible_trade_size = data_trade_limits.what_trade_is_possible(strategy_name, instrument_code, proposed_order.trade[0])

        revised_order = proposed_order.replace_trade_only_use_for_unsubmitted_trades([possible_trade_size])

        if revised_order.trade[0]!=proposed_order.trade[0]:
            log.msg("%s/%s trade change from %s to %s because of trade limits" \
                         % (strategy_name, instrument_code, str(proposed_order.trade), str(revised_order.trade)))

        return revised_order

    def add_trade_to_trade_limits(self, executed_order, trade_size=arg_not_supplied):
        if trade_size is arg_not_supplied:
            trade_size = executed_order.trade[0]
        data_trade_limits = dataTradeLimits(self.data)
        strategy_name = executed_order.strategy_name
        instrument_code = executed_order.instrument_code

        data_trade_limits.add_trade(strategy_name, instrument_code, trade_size)

    def adjust_trade_limit_counter_for_modified_order(self, modified_order):
        ## Adjust modified quantity for trade counter
        assert len(modified_order.trade) == 1
        assert len(modified_order.modification_quantity) == 1

        change_in_order_size = modified_order.modification_quantity[0] - modified_order.trade[0]
        if change_in_order_size > 0:
            self.add_trade_to_trade_limits(modified_order, change_in_order_size)
        else:
            self.remove_trade_from_trade_limits(modified_order, change_in_order_size)

    def remove_trade_from_trade_limits(self, partially_filled_modified_or_cancelled_order, unfilled_qty =arg_not_supplied):
        if unfilled_qty is arg_not_supplied:
            unfilled_qty = partially_filled_modified_or_cancelled_order.trade[0] - \
                           partially_filled_modified_or_cancelled_order.fill[0]

        data_trade_limits = dataTradeLimits(self.data)
        strategy_name = partially_filled_modified_or_cancelled_order.strategy_name
        instrument_code = partially_filled_modified_or_cancelled_order.instrument_code


        data_trade_limits.remove_trade(strategy_name, instrument_code, unfilled_qty)
