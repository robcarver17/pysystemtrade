from sysexecution.order_stack import Order, tradeableObject, orderStackData

possible_order_types = ['best', 'market', 'limit']

class instrumentTradeableObject(tradeableObject):
    def __init__(self, strategy_name, instrument_code):
        dict_def = dict(strategy_name = strategy_name, instrument_code = instrument_code)
        self._set_definition(dict_def)

    @classmethod
    def from_key(instrumentTradeableObject, key):
        strategy_name, instrument_code = key.split("/")

        return instrumentTradeableObject(strategy_name, instrument_code)

    @property
    def key(self):
        return "/".join([self._definition['strategy_name'],self._definition['instrument_code']])

class instrumentOrder(Order):
    def __init__(self,trade, *args, locked=False, type="best"):
        """
        instrumentOrder(strategy, instrument, trade, type) or 'strategy/instrument', trade, type)
        :param trade: float
        :param args: Eithier 2: strategy, instrument; or 1: instrumentTradeableObject
        :param type: str
        """
        if len(args)==1:
            self._tradeable_object = instrumentTradeableObject.from_key(args[0])
        else:
            strategy=args[0]
            instrument = args[1]
            self._tradeable_object = instrumentTradeableObject(strategy, instrument)

        self.trade = trade
        self._locked = locked
        self.order_info = dict(type=type)

    @property
    def strategy_name(self):
        return self._tradeable_object._definition['strategy_name']

    @property
    def instrument_code(self):
        return self._tradeable_object._definition['instrument_code']

    @classmethod
    def from_dict(instrumentOrder, order_as_dict):
        ## will need modifying in child classes
        trade = order_as_dict.pop('trade')
        instrument_strategy_key = order_as_dict.pop('key')
        locked = order_as_dict.pop('locked')
        order_info = order_as_dict

        order = instrumentOrder( trade, instrument_strategy_key, locked=locked, **order_info)

        return order

    @property
    def type(self):
        return self.order_info['type']

class instrumentOrderStackData(orderStackData):
    def __repr__(self):
        return "Instrument order stack: %s" % str(self._stack)

    def view_order_for_strategy_and_instrument(self, strategy_name, instrument_code):
        tradeable_object = instrumentTradeableObject(strategy_name, instrument_code)
        key = tradeable_object.key

        return self.get_order_with_key_from_stack(key)

