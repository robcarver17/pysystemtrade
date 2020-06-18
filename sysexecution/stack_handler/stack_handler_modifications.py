from syscore.objects import  success, failure, no_children, no_parent,  missing_order, order_is_in_status_modified


from sysexecution.contract_orders import log_attributes_from_contract_order
from sysexecution.instrument_orders import log_attributes_from_instrument_order
from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore

class stackHandlerForModifications(stackHandlerCore):

    def process_modification_stack(self):
        """
        Run a regular sweep across the stack
        Doing various things

        :return: success
        """

        self.pass_on_modification_from_instrument_to_contract_orders()
        self.pass_on_modification_complete_from_contract_to_instrument_orders()
        self.pass_on_rejections_from_contract_to_instrument_orders()
        self.clear_completed_modifications_from_instrument_and_contract_stacks()
        self.clear_rejected_modifications_from_instrument_and_contract_stacks()

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

