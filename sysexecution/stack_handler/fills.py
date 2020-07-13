from syscore.objects import fill_exceeds_trade, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, missing_contract, missing_data, rolling_cant_trade, ROLL_PSEUDO_STRATEGY, missing_order, order_is_in_status_reject_modification, order_is_in_status_finished, locked_order, order_is_in_status_modified, resolve_function


from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysproduction.data.broker import dataBroker

class stackHandlerForFills(stackHandlerCore):

    def process_fills_stack(self):
        """
        Run a regular sweep across the stack
        Doing various things

        :return: success
        """

        self.pass_fills_from_broker_to_broker_stack()
        self.pass_fills_from_broker_up_to_contract()
        self.pass_fills_from_contract_up_to_instrument()

    def pass_fills_from_broker_to_broker_stack(self):
        list_of_broker_order_ids = self.broker_stack.get_list_of_order_ids()
        for broker_order_id in list_of_broker_order_ids:
            self.apply_broker_fill_to_broker_stack(broker_order_id)

    def apply_broker_fill_to_broker_stack(self, broker_order_id):

        db_broker_order = self.broker_stack.get_order_with_id_from_stack(broker_order_id)
        if db_broker_order is missing_order:
            return failure

        log = db_broker_order.log_with_attributes(self.log)

        if db_broker_order.fill_equals_desired_trade():
            ## No point
            ## We don't log or we'd be spamming like crazy
            return success

        data_broker = dataBroker(self.data)
        matched_broker_order = data_broker.match_db_broker_order_to_order_from_brokers(db_broker_order)

        if matched_broker_order is missing_order:
            log.warn("Order %s does not match any broker orders" % db_broker_order)
            return failure

        result = self.broker_stack.\
            add_execution_details_from_matched_broker_order(broker_order_id, matched_broker_order)

        if result is fill_exceeds_trade:
            self.log.warn("Fill for %s exceeds trade for %s, ignoring... (hopefully will go away)" % (
                db_broker_order, matched_broker_order
            ))

        return result


    def pass_fills_from_broker_up_to_contract(self):
        list_of_child_order_ids = self.broker_stack.get_list_of_order_ids()
        for broker_order_id in list_of_child_order_ids:
            self.apply_broker_fill_to_contract_order(broker_order_id)

    def apply_broker_fill_to_contract_order(self, broker_order_id):
        broker_order = self.broker_stack.get_order_with_id_from_stack(broker_order_id)
        log = broker_order.log_with_attributes(self.log)
        if broker_order.fill_equals_zero():
            # Nothing to do here
            return success

        parent_id = broker_order.parent
        if parent_id is no_parent:
            log.error("No contract order parent for broker order %s %d" % (str(broker_order), broker_order_id))
            return failure

        contract_order = self.contract_stack.get_order_with_id_from_stack(parent_id)
        result = self.apply_broker_fill_to_known_contract_order(broker_order, contract_order)

        return result

    def apply_broker_fill_to_known_contract_order(self, broker_order, contract_order):
        log = broker_order.log_with_attributes(self.log)
        filled_qty = broker_order.fill ## will be a list
        filled_price = broker_order.filled_price
        fill_datetime = broker_order.fill_datetime
        result = self.contract_stack.\
            change_fill_quantity_for_order(contract_order.order_id, filled_qty, filled_price=filled_price,
                                           fill_datetime=fill_datetime)

        return result

    def pass_fills_from_contract_up_to_instrument(self):
        list_of_child_order_ids = self.contract_stack.get_list_of_order_ids()
        for contract_order_id in list_of_child_order_ids:
            self.apply_contract_fill_to_instrument_order(contract_order_id)

    def apply_contract_fill_to_instrument_order(self, contract_order_id):
        contract_order = self.contract_stack.get_order_with_id_from_stack(contract_order_id)
        log = contract_order.log_with_attributes(self.log)

        if contract_order.fill_equals_zero():
            # Nothing to do here
            return success

        contract_parent_id = contract_order.parent
        if contract_parent_id is no_parent:
            log.error("No parent for contract order %s %d" % (str(contract_order), contract_order_id))
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
        log = contract_order.log_with_attributes(self.log)

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
            ## Instrument order quantity is either zero (for a roll) or non zero (for a spread)
            if instrument_order.is_zero_trade():
                ## A roll; meaningless to do this
                result = success
            else:
                ## A proper spread order with non zero legs
                log.critical("Can't handle non-flat spread orders yet! Instrument order %s %s"
                                  % (str(instrument_order), str(instrument_order.order_id)))
                result = failure

        return result

    def apply_contract_fill_to_parent_order_multiple_children(self, list_of_contract_order_ids, instrument_order):
        log = instrument_order.log_with_attributes(self.log)
        if instrument_order.is_zero_trade():
            ## An inter-market flat spread
            ## Meaningless to do this
            return success
        else:
            ## A proper spread trade with non zero legs
            log.critical("Can't handle inter-market spread orders yet! Instrument order %s %s"
                              % (str(instrument_order), str(instrument_order.order_id)))
            return failure
