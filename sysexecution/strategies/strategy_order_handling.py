"""
Called from sysproduction code in a while loop, each time it runs loops over strategies
For each strategy gets the required trades per instrument
It then passes these to the 'virtual' order queue
So called because it deals with instrument level trades, not contract implementation
"""

from syscore.objects import missing_order,  success, failure, locked_order, duplicate_order, zero_order

from syscore.genutils import timerClass
from syscore.objects import resolve_function, not_updated, success, failure

from sysdata.private_config import get_private_then_default_key_value

from sysproduction.data.positions import diagPositions
from sysproduction.data.orders import dataOrders
from sysproduction.data.controls import diagOverrides, dataLocks

class orderHandlerAcrossStrategies(object):
    def __init__(self, data):
        data_orders = dataOrders(data)

        self.data = data
        self.data_orders = data_orders
        self.log = data.log

        self._create_strategy_generators()

    @property
    def order_stack(self):
        return self.data_orders.instrument_stack()

    def _create_strategy_generators(self):
        strategy_dict = get_private_then_default_key_value('strategy_list')
        generator_dict = {}
        for strategy_name, strategy_config in strategy_dict.items():
            self.log.label(strategy_name = strategy_name)
            config_dict = get_private_then_default_key_value('strategy_list')
            try:
                config_for_strategy = config_dict[strategy_name]
                order_config = config_for_strategy['order_handling']
                strategy_handler_class_name = order_config['function']
                strategy_handler_class = resolve_function(strategy_handler_class_name)

            except:
                self.log.critical("No handler found for strategy %s, won't do order handling" % strategy_name)
                strategy_handler_class = orderGeneratorForStrategy

            strategy_handler = strategy_handler_class(self.data, strategy_name)
            generator_dict[strategy_name] = strategy_handler

        self._generator_dict = generator_dict

        return success

    def check_for_orders_across_strategies(self):
        """
        This function is called every time we want to see if any of our strategies have an order
        If new orders are generated, it will handle them

        :return: succcess
        """
        generator_dict = self._generator_dict
        for strategy_name, order_generator in generator_dict.items():
            order_list = order_generator.required_orders_if_updated()
            if order_list is not_updated:
                # next strategy
                continue
            else:
                ## Handle the orders
                pass
                order_list_with_overrides = self.apply_overrides(order_list)
                result = self.submit_order_list(order_list_with_overrides)
                if result is success:
                    generator_dict[strategy_name].set_last_run()

        return success


    def apply_overrides(self, order_list):
        new_order_list = [self.apply_overrides_for_instrument_and_strategy(proposed_order) for
                          proposed_order in order_list]

        return new_order_list

    def submit_order_list(self, order_list):
        data_lock = dataLocks(self.data)
        for order in order_list:
            #try:
                # we allow existing orders to be modified
                log = order.log_with_attributes(self.log)
                log.msg("Required order %s" % str(order))

                instrument_locked = data_lock.is_instrument_locked(order.instrument_code)
                if instrument_locked:
                    log.msg("Instrument locked, not submitting")
                    continue

                order_id = self.order_stack.put_order_on_stack(order)
                if type(order_id) is int:
                    log.msg("Added order %s to instrument order stack with order id %d" % (str(order), order_id),
                            instrument_order_id = order_id)
                else:
                    order_error_object = order_id
                    if order_error_object is zero_order:
                        # To be expected unless modifying an existing order
                        log.msg(
                            "Ignoring zero order %s" % str(
                                order))

                    else:
                        log.warn("Could not put order %s on instrument order stack, error: %s" %
                                      (str(order), str(order_error_object)))

            #except Exception as e:
            #    # serious error, abandon everything
            #    log.critical("Error %s putting %s on instrument order stack" % (str(e), str(order)))
            #    return failure

        return success

    def apply_overrides_for_instrument_and_strategy(self,  proposed_order):
        """
        Apply an override to a trade

        :param strategy_name: str
        :param instrument_code: str
        :return: int, updated position
        """

        diag_overrides = diagOverrides(self.data)
        diag_positions = diagPositions(self.data)

        strategy_name = proposed_order.strategy_name
        instrument_code = proposed_order.instrument_code

        original_position = diag_positions.get_position_for_strategy_and_instrument(strategy_name,
                                                                                    instrument_code)

        override = diag_overrides.get_cumulative_override_for_strategy_and_instrument(strategy_name, instrument_code)
        revised_order = override.apply_override(original_position, proposed_order)

        if revised_order.trade!=proposed_order.trade:
            self.log.msg("%s/%s trade change from %d to %d because of override %s"
                         % (strategy_name, instrument_code, revised_order.trade, proposed_order.trade,
                            str(override)),
                                     strategy_name = strategy_name,
                                     instrument_code = instrument_code)

        return revised_order


class orderGeneratorForStrategy(timerClass):
    """

    Order generators are strategy specific but have common methods used by the order handler

    """

    def __init__(self, data, strategy_name):
        self.data = data
        self.strategy_name = strategy_name
        self.log = data.log

    @property
    def strategy_config(self):
        config = getattr(self, "_strategy_config", None)
        if config is None:
            try:
                config_dict = get_private_then_default_key_value('strategy_list')
                config_for_strategy = config_dict[self.strategy_name]
                config = config_for_strategy['order_handling']
            except Exception as e:
                self.log.critical("Can't find order_handling configuration for strategy in .strategy_list config element error %s" % e)
                return {}

            self._strategy_config = config

        return config

    @property
    def frequency_minutes(self):
        # used by timer code
        # defaults to every hour unless otherwise
        return self.strategy_config.get('frequency_minutes', 60)

    def get_actual_positions_for_strategy(self):
        """
        Actual positions held by a strategy

        :return: dict, keys are instrument codes, values are positions
        """
        data = self.data
        strategy_name = self.strategy_name

        diag_positions = diagPositions(data)
        list_of_instruments = diag_positions.get_list_of_instruments_for_strategy_with_position(strategy_name)
        actual_positions = dict([(instrument_code,
                                  diag_positions.get_position_for_strategy_and_instrument(strategy_name,
                                                                                          instrument_code))
                                 for instrument_code in list_of_instruments])
        return actual_positions

    def required_orders_if_updated(self):
        """
        Called by handler for all strategies

        :return: dict, keys are instrument codes, values are trades OR not_updated
        """

        requires_update = self.check_if_ready_for_another_run()
        if not requires_update:
            return not_updated

        ## needs updating
        orders = self._required_orders_no_checking()

        self.set_last_run()

        return orders

    def _required_orders_no_checking(self):
        ## Would normally be overriden, we only use this class if no class is found in config
        return not_updated

