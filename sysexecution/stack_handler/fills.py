from syscore.objects import missing_order, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, missing_contract, missing_data, rolling_cant_trade, ROLL_PSEUDO_STRATEGY, missing_order, order_is_in_status_reject_modification, order_is_in_status_finished, locked_order, order_is_in_status_modified, resolve_function


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
        data_broker = dataBroker(self.data)

        db_broker_order = self.broker_stack.get_order_with_id_from_stack(broker_order_id)

        if db_broker_order.fill_equals_desired_trade():
            ## No point
            return success

        matched_broker_order = data_broker.match_db_broker_order_to_order_from_brokers(db_broker_order)

        if matched_broker_order is missing_order:
            return failure

        result = self.apply_updated_broker_order_info_to_broker_order(broker_order_id, matched_broker_order)

        return result

    def apply_updated_broker_order_info_to_broker_order(self, broker_order_id, matched_broker_order):
        db_broker_order = self.broker_stack.get_order_with_id_from_stack(broker_order_id)
        # fill
        assert len(db_broker_order.fill)==1
        assert len(matched_broker_order.fill)==1

        if matched_broker_order.fill[0]>db_broker_order.fill[0]:
            self.broker_stack.change_fill_quantity_for_order(broker_order_id, matched_broker_order.fill,
                                                             filled_price = matched_broker_order.filled_price,
                                                             fill_datetime=matched_broker_order.fill_datetime)

        ## FIX ME OUGHT TO BE DONE WITHOUT RESORTING TO _CHANGE ORDER
        db_broker_order.fill_order(matched_broker_order.fill,
                                                             filled_price = matched_broker_order.filled_price,
                                                             fill_datetime=matched_broker_order.fill_datetime)
        db_broker_order.commission = matched_broker_order.commission
        db_broker_order.broker_permid = matched_broker_order.broker_permid
        db_broker_order.algo_comment = matched_broker_order.algo_comment

        self.broker_stack._change_order_on_stack(broker_order_id, db_broker_order)

        return success

    def pass_fills_from_broker_up_to_contract(self):
        list_of_child_order_ids = self.broker_stack.get_list_of_order_ids()
        for broker_order_id in list_of_child_order_ids:
            self.apply_broker_fill_to_parent_order(broker_order_id)

    def apply_broker_fill_to_parent_order(self, broker_order_id):
        broker_order = self.broker_stack.get_order_with_id_from_stack(broker_order_id)

        if broker_order.fill_equals_zero():
            # Nothing to do here
            return success

        parent_id = broker_order.parent
        if parent_id is no_parent:
            self.log.warn("No parent for broker order %s %d" % (str(broker_order), broker_order_id))
            return failure

        contract_order = self.contract_stack.get_order_with_id_from_stack(parent_id)
        result = self.apply_broker_fill_to_known_contract_order(broker_order, contract_order)

        return result

    def apply_broker_fill_to_known_contract_order(self, broker_order, contract_order):
        filled_qty = broker_order.fill ## will be a list
        filled_price = broker_order.filled_price
        fill_datetime = broker_order.fill_datetime
        if len(filled_qty)==1:
            ## Not a spread order, trivial
            result = self.contract_stack.\
                change_fill_quantity_for_order(contract_order.order_id, filled_qty, filled_price=filled_price,
                                               fill_datetime=fill_datetime)
        else:
            ## Spread order
            self.log.critical("Can't handle spread orders yet!")

            result = failure

        return result

    def pass_fills_from_contract_up_to_instrument(self):
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
            ## Instrument order quantity is either zero (for a roll) or non zero (for a spread)
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
