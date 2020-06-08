"""
This piece of code processes the interface between the instrument order stack and the contract order stack

Tasks it needs to accomplish:

- netting of parent orders FIX ME FUTURE
- when a new order is added to the instrument stack with no child orders, create child orders in contract order stack
- when roll status is 'force', and no parent orders, generate an 'orphan roll order (spread or outright)
- when a roll order is happening, need to lock instrument and related instruments
- when a parent order is moved to modification status, change child orders to modification status
- when all child orders are in modification complete status, change parent order to modification complete
- when a parent order and child orders are all in modification complete status, clear modification from parents and children
- when a child order has an updated fill, give the parent order a fill
  - if multiple child orders, give the parent order the fill min(child order fills)


"""

from syscore.objects import missing_order, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, missing_contract, missing_data, rolling_cant_trade, ROLL_PSEUDO_STRATEGY, missing_order, order_is_in_status_reject_modification, order_is_in_status_finished, locked_order, order_is_in_status_modified


from sysexecution.spawn_children_from_instrument_orders import spawn_children_from_instrument_order
from sysexecution.roll_orders import  create_force_roll_orders
from sysexecution.contract_orders import log_attributes_from_contract_order
from sysexecution.instrument_orders import log_attributes_from_instrument_order

from sysproduction.data.positions import diagPositions, updatePositions
from sysproduction.data.orders import dataOrders

class instrument_to_contract_stack_handler(object):
    def __init__(self, data):
        order_data = dataOrders(data)
        instrument_stack = order_data.instrument_stack()
        contract_stack = order_data.contract_stack()

        self.instrument_stack = instrument_stack
        self.contract_stack = contract_stack

        self.order_data = order_data
        self.data = data
        self.log = data.log

    def process_stack(self):
        """
        Run a regular sweep across the stack
        Doing various things

        :return: success
        """

        self.spawn_children_from_new_instrument_orders()
        self.generate_force_roll_orders()
        self.pass_on_modification_from_instrument_to_contract_orders()
        self.pass_on_modification_complete_from_contract_to_instrument_orders()
        self.pass_on_rejections_from_contract_to_instrument_orders()
        self.clear_completed_modifications_from_instrument_and_contract_stacks()
        self.clear_rejected_modifications_from_instrument_and_contract_stacks()
        self.pass_fills_from_children_up_to_parents()
        self.handle_completed_orders()


    def spawn_children_from_new_instrument_orders(self):
        new_order_ids = self.instrument_stack.list_of_new_orders()
        for instrument_order_id in new_order_ids:
            self.spawn_children_from_instrument_order_id(instrument_order_id)

    def spawn_children_from_instrument_order_id(self, instrument_order_id):
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)
        if instrument_order is missing_order:
            return failure

        log = log_attributes_from_instrument_order(self.log, instrument_order)

        list_of_contract_orders = spawn_children_from_instrument_order(self.data, instrument_order)

        log.msg("List of contract orders spawned %s" % str(list_of_contract_orders))

        list_of_child_ids = self.contract_stack.put_list_of_orders_on_stack(list_of_contract_orders)

        if list_of_child_ids is failure:
            log.msg("Failed to create child orders %s from parent order %s" % (str(list_of_contract_orders),
                                                                                          str(instrument_order)))
            return failure


        for contract_order, child_id in zip(list_of_contract_orders, list_of_child_ids):
            child_log = log_attributes_from_contract_order(log, contract_order)
            child_log.msg("Put child order %s on contract_stack with ID %d from parent order %s" % (str(contract_order),
                                                                                          child_id,
                                                                                          str(instrument_order)))
        result = self.instrument_stack.add_children_to_order(instrument_order.order_id, list_of_child_ids)
        if result is not success:
            log.msg("Error %s when adding children to instrument order %s" % (str(result), str(instrument_order)))
            return failure

        return success

    def generate_force_roll_orders(self):
        diag_positions = diagPositions(self.data)
        list_of_instruments = diag_positions.get_list_of_instruments_with_any_position()
        for instrument_code in list_of_instruments:
            self.generate_force_roll_orders_for_instrument(instrument_code)

    def generate_force_roll_orders_for_instrument(self, instrument_code):
        log = self.data.log.setup(instrument_code = instrument_code, strategy_name = ROLL_PSEUDO_STRATEGY)

        instrument_order, contract_orders = create_force_roll_orders(self.data, instrument_code)
        # Create a pseudo instrument order and a set of contract orders
        # This will also prevent trying to generate more than one set of roll orders

        if len(contract_orders)==0 or instrument_order is missing_order:
            # No orders
            return None

        # Do as a transaction: if everything doesn't go to plan can roll back
        instrument_order.lock_order()
        instrument_order_id = self.instrument_stack.put_order_on_stack(instrument_order, allow_zero_orders=True)

        if type(instrument_order_id) is not int:
            if instrument_order_id is duplicate_order:
                # Probably already done this
                return success
            else:
                log.msg("Couldn't put roll order %s on instrument order stack error %s" % (str(instrument_order),
                                                                                           str(instrument_order_id)))
            return failure

        for child_order in contract_orders:
            child_order.parent = instrument_order_id

        # Do as a transaction: if everything doesn't go to plan can roll back
        # if this try fails we will roll back the instrument commit
        try:
            log = log.setup(instrument_order_id= instrument_order_id)

            log.msg("List of roll contract orders spawned %s" % str(contract_orders))
            list_of_child_order_ids = self.contract_stack.put_list_of_orders_on_stack(contract_orders, unlock_when_finished=False)

            if list_of_child_order_ids is failure:
                log.msg("Failed to add roll contract orders to stack %s" % (str(contract_orders)))
                list_of_child_order_ids = []
                raise Exception

            for roll_order, order_id in zip(contract_orders, list_of_child_order_ids):
                child_log = log_attributes_from_contract_order(log, roll_order)
                child_log.msg("Put roll order %s on contract_stack with ID %d from parent order %s" % (str(roll_order),
                                                                                              order_id,
                                                                                              str(instrument_order)))

            self.instrument_stack._unlock_order_on_stack(instrument_order_id)
            result = self.instrument_stack.add_children_to_order(instrument_order_id, list_of_child_order_ids)
            if result is not success:
                log.msg("Error %s when adding children to instrument roll order %s" % (str(result), str(instrument_order)))
                raise Exception

        except:
            ## Roll back instrument order
            self.instrument_stack._unlock_order_on_stack(instrument_order_id)
            self.instrument_stack.deactivate_order(instrument_order_id)
            self.instrument_stack.remove_order_with_id_from_stack(instrument_order_id)

            # If any children, roll them back also
            if len(list_of_child_order_ids)>0:
                self.contract_stack.rollback_list_of_orders_on_stack(list_of_child_order_ids)

            return failure

        return success

    def pass_on_modification_from_instrument_to_contract_orders(self):
        # get list of orders in instrument stack where status is modified
        # for each order, pass on modification to children

        instrument_orders_being_modified = self.instrument_stack.list_of_being_modified_orders()
        for instrument_order_id in instrument_orders_being_modified:
            self.pass_modification_from_parent_to_children(instrument_order_id)

        # We now wait for the children to set their modification as complete

    def pass_modification_from_parent_to_children(self, instrument_order_id):
        """
        Modifications will depend on the parent/child relationship:

        :param instrument_order_id:
        :return:
        """
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)
        child_order_ids = instrument_order.children
        log = log_attributes_from_instrument_order(self.log, instrument_order)

        if child_order_ids is no_children:
            # No children
            result = self._modify_childless_instrument_order(instrument_order_id)
            return result

        elif len(child_order_ids)==1:
            # Dead simple: one child
            child_id = child_order_ids[0]
            result = self._modify_single_child_order(child_id, instrument_order)
            return result
        else:
            # multiple children
            result = self._modify_multiple_child_orders(instrument_order)
            return result


    def _modify_childless_instrument_order(self, instrument_order_id):
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)
        log = log_attributes_from_instrument_order(self.log, instrument_order)
        # We can mark the parent order as completed modifying and clear the modification
        log.msg("Instrument order %s has no children so modification can take place" % str(instrument_order))
        result = self.instrument_stack.completed_modifying_order_on_stack(instrument_order_id)
        if result is failure:
            return failure
        result = self.instrument_stack.clear_modification_of_order_on_stack(instrument_order_id)

        return result

    def _modify_single_child_order(self, child_id, instrument_order):
        child_order = self.contract_stack.get_order_with_id_from_stack(child_id)
        if len(child_order.trade) ==1:
            self._modify_single_child_order_where_child_is_single_contract(child_id, instrument_order)
        else:
            raise Exception("I don't know how to deal with modifying a multiple length child order yet!")

    def _modify_single_child_order_where_child_is_single_contract(self, child_id, instrument_order):
        child_order = self.contract_stack.get_order_with_id_from_stack(child_id)
        child_log = log_attributes_from_contract_order(self.log, child_order)
        modification_quantity = instrument_order.modification_quantity

        result = self.contract_stack.modify_order_on_stack(child_id, [modification_quantity])

        if result is success:
            # fine
            return success
        elif result is order_is_in_status_modified:
            # Modification is already happening, probably from a previous run of this code
            return success
        else:
            child_log.warn("Couldn't pass modification from parent instrument order %s to child %s error %s" %
                           (str(instrument_order), str(child_order), str(result)))
            return failure


    def _modify_multiple_child_orders(self, instrument_order):
        """
        OK, it's got multiple child orders. This is more complicated...

        We now have a series of possibilites:
        - equal and opposite positions in each (eg roll order on outright legs, spread instrument)
        - opposite but not equal positions in each (spread instrument)
        - same sign positions in each (passive roll order)

        It's far too complicated to try and deal with all these cases. So instead we allow a cancellation
         order to go ahead (where there is zero unfilled quantity left), but all other types of modifications
         are rejected
        """

        log = log_attributes_from_instrument_order(self.log, instrument_order)
        parent_order_can_be_cancelled = instrument_order.fill_equals_modification_quantity()
        if not parent_order_can_be_cancelled:
            log.warn("Instrument order %s has multiple children and isn't a full cancellation: can't be modified" % str(
                instrument_order))
            return failure

        child_order_ids = instrument_order.children

        for child_id in child_order_ids:
            child_order = self.contract_stack.get_order_with_id_from_stack(child_id)
            if child_order is missing_order:
                log.warn("Child order orderid % is missing for instrument order %s, can't pass on modification" % (child_id, str(instrument_order)))
                return failure
            child_log = log_attributes_from_contract_order(self.log, child_order)
            result = self.contract_stack.cancel_order(child_id)
            if type(result) is int:
                # successful cancellation modification
                continue
            elif result is order_is_in_status_modified:
                # Modification is already happening, probably from a previous run of this code
                continue
            else:
                child_log.warn("Couldn't pass modification from parent instrument order %s to child %s error %s" %
                         (str(instrument_order), str(child_order), str(result)))
                continue

        return success



    def pass_on_modification_complete_from_contract_to_instrument_orders(self):
        # get list of orders in contract stack where status is modified and complete
        # this will be handled by the contract stack manager
        # for each order, pass on modification to parent
        # ... if and only if *all* children are in modification complete state
        contract_orders_finished_being_modified = self.contract_stack.list_of_finished_modifiying_orders()
        for contract_order_id in contract_orders_finished_being_modified:
            self.pass_modification_complete_from_child_to_parent_orders(contract_order_id)

        # We can now clear modifications

    def pass_modification_complete_from_child_to_parent_orders(self, contract_order_id):
        # ... if and only if *all* children are in modification complete state

        child_order = self.contract_stack.get_order_with_id_from_stack(contract_order_id)
        log = log_attributes_from_contract_order(self.log, child_order)
        parent_order_id = child_order.parent
        if parent_order_id is no_parent:
            log.warn("No parent order for child order %s when trying to mark modification as complete" %
                          (str(child_order)))

            return failure

        instrument_order = self.instrument_stack.get_order_with_id_from_stack(parent_order_id)
        # Check that all children have completed modifying
        child_id_list = instrument_order.children
        if child_id_list is no_children:
            log.warn("Reckless parenting! Instrument order %s has no children but child order %s thinks it is the parent when trying to mark modification as complete" %
                     (str(instrument_order), str(child_order)))

            return failure

        flag_completed = [self.contract_stack.is_finished_modified(other_child_order_id) for
                          other_child_order_id in child_id_list]
        if not all(flag_completed):
            # Can't mark parent order as complete until all children are complete
            return failure

        result = self.instrument_stack.completed_modifying_order_on_stack(parent_order_id)
        if result is failure:
            log.warn("Couldn't pass modification from child order %s up to parent order %d" %
                          (str(child_order), parent_order_id))

            return failure

        return success

    def pass_on_rejections_from_contract_to_instrument_orders(self):
        # get list of orders in contract stack where status is modification rejected
        # this will be handled by the contract stack manager
        # for each order, pass on modification to parent
        # if any child order is rejected, then we also reject the parent and all other child orders
        contract_orders_modification_rejected = self.contract_stack.list_of_rejected_modifying_orders()
        for contract_order_id in contract_orders_modification_rejected:
            self.pass_modification_rejection_from_child_to_parent_order(contract_order_id)

        # We can now clear modifications

    def pass_modification_rejection_from_child_to_parent_order(self, contract_order_id):
        # if any child order is rejected, then we also reject the parent and all other child orders
        child_order = self.contract_stack.get_order_with_id_from_stack(contract_order_id)
        log = log_attributes_from_contract_order(self.log, child_order)
        parent_order_id = child_order.parent
        if parent_order_id is no_parent:
            log.warn("No parent order for child order %s when trying to mark modification as rejected" %
                          (str(child_order)))

            return failure

        instrument_order = self.instrument_stack.get_order_with_id_from_stack(parent_order_id)

        # All children should also be rejected
        child_id_list = instrument_order.children
        if child_id_list is no_children:
            log.warn("Reckless parenting! Instrument order %s has no children but child order %s thinks it is the parent when trying to mark modification as complete" %
                     (str(instrument_order), str(child_order)))

            return failure

        for other_child_id in child_id_list:
            result = self.contract_stack.reject_order_on_stack(other_child_id)
            if result is not success:
                log.warn("Couldn't mark child order %d as rejected when another child %s was rejected" % (other_child_id, str(child_order)))
                return failure

        result = self.instrument_stack.reject_order_on_stack(parent_order_id)
        if result is not success:
            log.warn("Couldn't pass reject modification from child order %s up to parent order %d" %
                          (str(child_order), parent_order_id))

            return failure

        return success


    def clear_completed_modifications_from_instrument_and_contract_stacks(self):
        # get list of orders in contract stack where status is modified and complete
        # if parent is also complete, clear modifications from parent and child

        instrument_orders_finished_being_modified = self.instrument_stack.list_of_finished_modifiying_orders()
        for instrument_order_id in instrument_orders_finished_being_modified:
            self.clear_parents_and_children_if_all_modification_complete(instrument_order_id)

    def clear_parents_and_children_if_all_modification_complete(self, instrument_order_id):
        parent_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)
        log = log_attributes_from_instrument_order(self.log, parent_order)
        list_of_child_order_ids = parent_order.children

        list_of_child_orders = [self.contract_stack.get_order_with_id_from_stack(child_order_id) \
            for child_order_id in list_of_child_order_ids]

        # Check all child orders are in 'completed modifying' state
        # if any are not, we can't do this
        # (this shouldn't happen, since we only set parent order to completed modifying when all children are set)
        for child_order in list_of_child_orders:
            child_log = log_attributes_from_contract_order(self.log, child_order)
            if not child_order.is_order_finished_modifying():
                child_log.warn("Instrument order %s has finished modifying but child contract order %s has not! Can't clear modifications" % \
                         (str(parent_order), str(child_order)))
                return failure

        # clear the modifications for the children
        for child_order_id in list_of_child_order_ids:
            result = self.contract_stack.clear_modification_of_order_on_stack(child_order_id)
            if result is failure:

                log.warn("Can't clear modifications for contract order %d, child of parent %s" %
                         (child_order_id, str(parent_order)))

                return failure

        # Children are completed, we can do parent
        result = self.instrument_stack.clear_modification_of_order_on_stack(instrument_order_id)
        if result is failure:
            instrument_log = log_attributes_from_instrument_order(self.log, parent_order)
            instrument_log.warn("Cleared modifications for contract order children, but can't clear parent instrument order %s!" % parent_order)
            return failure

        return success


    def clear_rejected_modifications_from_instrument_and_contract_stacks(self):
        # get list of orders in contract stack where status is rejected
        # if parent and all child orders are rejected, then clear the modification

        instrument_orders_finished_being_modified = self.instrument_stack.list_of_rejected_modifying_orders()
        for instrument_order_id in instrument_orders_finished_being_modified:
            self.clear_parents_and_children_if_all_modification_rejected(instrument_order_id)

    def clear_parents_and_children_if_all_modification_rejected(self, instrument_order_id):
        parent_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)
        log = log_attributes_from_instrument_order(self.log, parent_order)
        list_of_child_order_ids = parent_order.children

        list_of_child_orders = [self.contract_stack.get_order_with_id_from_stack(child_order_id) \
            for child_order_id in list_of_child_order_ids]

        # Check all child orders are in 'rejected' state
        # If any aren't we can't do this
        # This shouldn't happen since we only mark parent orders as rejected once all the kids are
        for child_order in list_of_child_orders:
            if not child_order.is_order_modification_rejected():
                child_log = log_attributes_from_contract_order(self.log, child_order)
                child_log.warn("Instrument order %s has rejected modifying but child contract order %s has not! Can't clear modifications" % \
                         (str(parent_order), str(child_order)))
                return failure

        for child_order_id in list_of_child_order_ids:
            result = self.contract_stack.clear_modification_of_order_on_stack(child_order_id)
            if result is failure:
                log.warn("Can't clear modifications for contract order %d child of %s" %
                         (child_order_id, str(parent_order)))

                return failure

        # Children are completed, we can do parent
        result = self.instrument_stack.clear_modification_of_order_on_stack(instrument_order_id)
        if result is failure:
            log = log_attributes_from_instrument_order(self.log, parent_order)
            log.warn("Cleared modifications for contract order children, but can't clear parent instrument order %s!" % parent_order)
            return failure

        return success


    def pass_fills_from_children_up_to_parents(self):
        list_of_child_order_ids = self.contract_stack.get_list_of_order_ids()
        for contract_order_id in list_of_child_order_ids:
            self.apply_contract_fill_to_parent_order(contract_order_id)

    def apply_contract_fill_to_parent_order(self, contract_order_id):
        contract_order = self.contract_stack.get_order_with_id_from_stack(contract_order_id)

        if contract_order.fill_equals_zero():
            # Nothing to do here
            return success

        contract_parent_id = contract_order.parent
        if contract_parent_id is no_parent:
            self.log.warn("No parent for contract order %s %d" % (str(contract_order), contract_order_id))
            return failure

        instrument_order = self.instrument_stack.get_order_with_id_from_stack(contract_parent_id)
        list_of_contract_order_ids = instrument_order.children

        # This will be a list...

        if len(list_of_contract_order_ids)==1:
            ## easy, only one child
            result = self.apply_contract_fill_to_parent_order_single_child(contract_order, instrument_order)
        else:
            result = self.apply_contract_fill_to_parent_order_multiple_children(list_of_contract_order_ids, instrument_order)

        return result

    def apply_contract_fill_to_parent_order_single_child(self, contract_order, instrument_order):
        fill_for_contract = contract_order.fill
        filled_price = contract_order.filled_price
        fill_datetime = contract_order.fill_datetime
        if len(fill_for_contract)==1:
            ## Not a spread order, trivial
            result = self.instrument_stack.\
                change_fill_quantity_for_order(instrument_order.order_id, fill_for_contract[0], filled_price=filled_price,
                                               fill_datetime=fill_datetime)
        else:
            ## Spread order
            ## Instrument order quantity is eithier zero (for a roll) or non zero (for a spread)
            if instrument_order.is_zero_trade():
                ## A roll; meaningless to do this
                result = success
            else:
                ## A proper spread order
                self.log.critical("Can't handle spread orders yet! Instrument order %s %s"
                                  % (str(instrument_order), str(instrument_order.order_id)))
                result = failure

        return result

    def apply_contract_fill_to_parent_order_multiple_children(self, list_of_contract_order_ids, instrument_order):
        if instrument_order.is_zero_trade():
            ## A roll trade
            ## Meaningless to do this
            return success
        else:
            ## A proper spread trade
            self.log.critical("Can't handle spread orders yet! Instrument order %s %s"
                              % (str(instrument_order), str(instrument_order.order_id)))
            return failure

    def handle_completed_orders(self):
        list_of_completed_instrument_orders = self.instrument_stack.list_of_completed_orders()
        for instrument_order_id in list_of_completed_instrument_orders:
            self.handle_completed_instrument_order(instrument_order_id)

    def handle_completed_instrument_order(self, instrument_order_id):
        ## Check children all done
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)
        list_of_contract_order_id = instrument_order.children
        if list_of_contract_order_id is no_children:
            list_of_contract_order_id = []

        for contract_order_id in list_of_contract_order_id:
            completely_filled = self.contract_stack.is_completed(contract_order_id)
            if not completely_filled:
                ## OK We can't do this unless all our children are filled
                return success

        # If we have got this far then all our children are filled, and the parent is filled

        list_of_contract_orders = []
        for contract_order_id in list_of_contract_order_id:
            list_of_contract_orders.append(self.contract_stack.get_order_with_id_from_stack(contract_order_id))

        position_updater = updatePositions(self.data)
        # Update strategy position table
        position_updater.update_strategy_position_table_with_instrument_order(instrument_order)

        # Update contract position table
        for contract_order in list_of_contract_orders:
            position_updater.update_contract_position_table_with_contract_order(contract_order)

        order_data = dataOrders(self.data)
        # Update historic order database
        order_data.add_historic_instrument_order_to_data(instrument_order)
        for contract_order in list_of_contract_orders:
            order_data.add_historic_contract_order_to_data(contract_order)

        # Make orders inactive
        # A subsequent process will delete them
        self.instrument_stack.deactivate_order(instrument_order_id)
        for contract_order_id in list_of_contract_order_id:
            self.contract_stack.deactivate_order(contract_order_id)

        return success
