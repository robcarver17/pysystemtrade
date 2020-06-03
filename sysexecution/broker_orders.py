
from sysexecution.order_stack import orderStackData
from sysexecution.base_orders import  no_order_id, no_children, no_parent, MODIFICATION_STATUS_NO_MODIFICATION
from sysexecution.contract_orders import contractOrder
from sysexecution.contract_orders import contractTradeableObject
from syscore.genutils import  none_to_object, object_to_none
from syscore.objects import failure, success, arg_not_supplied


class brokerOrder(contractOrder):

    def __init__(self, *args, fill=None,
                 locked=False, order_id=no_order_id,
                 modification_status = MODIFICATION_STATUS_NO_MODIFICATION,
                 modification_quantity = None, parent=no_parent,
                 children=no_children, active=True,
                 algo_used="", order_type = "market", limit_price = None, filled_price = None,
                 submit_datetime=None,
                 fill_datetime = None,
                 side_price = None, mid_price = None,
                 algo_comment = "",
                 broker="", broker_account="", broker_clientid="",
                 commission=0.0,
                 broker_permid="", broker_tempid="",
                 manual_fill = False,
                 calendar_spread_order=None
                 ):
        """

        :param args: Eithier a single argument 'strategy/instrument/contract_id' str, or strategy, instrument, contract_id; followed by trade
        i.e. brokerOrder(strategy, instrument, contractid, trade,  **kwargs) or 'strategy/instrument/contract_id', trade, type, **kwargs)

        Contract_id can eithier be a single str or a list of str for spread orders, all YYYYMM
        If expressed inside a longer string, seperate contract str by '_'

        i.e. brokerOrder('a strategy', 'an instrument', '201003', 6,  **kwargs)
         same as brokerOrder('a strategy/an instrument/201003', 6,  **kwargs)
        brokerOrder('a strategy', 'an instrument', ['201003', '201406'], [6,-6],  **kwargs)
          same as brokerOrder('a strategy/an instrument/201003_201406', [6,-6],  **kwargs)
        :param fill:  fill done so far, list of int
        :param locked: bool, is order locked
        :param order_id: int, my ref number
        :param modification_status: str, is being modified?
        :param modification_quantity: list of int, any modification required
        :param parent: int or not supplied, parent order
        :param children: list of int or not supplied, child order ids (FUNCTIONALITY NOT USED HERE)
        :param active: bool, is order active or has been filled/cancelled
        :param algo_used: Name of the algo I used to generate the order
        :param order_type: market or limit order (other types may be supported in future)
        :param limit_price: if relevant, float
        :param filled_price: float
        :param submit_datetime: datetime
        :param fill_datetime: datetime
        :param side_price: Price on the 'side' we are submitting eg offer if buying, when order submitted
        :param mid_price: Average of bid and offer when we are submitting
        :param algo_comment: Any comment made by the algo, eg 'Aggressive', 'Passive'...
        :param broker: str, name of broker
        :param broker_account: str, brokerage account
        :param broker_clientid: int, client ID used to generate order
        :param commission: float
        :param broker_permid: Brokers permanent ref number
        :param broker_tempid: Brokers temporary ref number
        :param manual_fill: bool, was fill entered manually rather than being picked up from IB

        """

        tradeable_object, trade = super()._resolve_args(args)
        self._tradeable_object = tradeable_object

        if type(trade) is int:
            trade = [trade]

        if len(trade)==1:
            calendar_spread_order = False
        else:
            calendar_spread_order = True

        if fill is None:
            fill = [0]*len(trade)

        self._trade = trade
        self._fill = fill
        self._fill_datetime = fill_datetime
        self._filled_price = filled_price

        self._locked = locked
        self._order_id = order_id
        self._modification_status = modification_status
        self._modification_quantity = modification_quantity
        self._parent = parent
        self._children = children
        self._active = active


        self._order_info = dict(algo_used=algo_used, order_type=order_type, submit_datetime = submit_datetime,
                 limit_price = limit_price,
                             manual_fill = manual_fill,
                                 calendar_spread_order = calendar_spread_order,
                                side_price = side_price, mid_price = mid_price,
                                algo_comment = algo_comment, broker = broker, broker_account = broker_account,
                                broker_permid = broker_permid, broker_tempid = broker_tempid, broker_clientid = broker_clientid,
                                commission=commission)


    @property
    def algo_used(self):
        return self._order_info['algo_used']


    @property
    def order_type(self):
        return self._order_info['order_type']

    @property
    def submit_datetime(self):
        return self._order_info['submit_datetime']



    @property
    def manual_fill(self):
        return self._order_info['manual_fill']

    @property
    def calendar_spread_order(self):
        return self._order_info['calendar_spread_order']

    @property
    def side_price(self):
        return self._order_info['side_price']

    @property
    def mid_price(self):
        return self._order_info['mid_price']

    @property
    def algo_comment(self):
        return self._order_info['algo_comment']

    @algo_comment.setter
    def algo_comment(self, comment):
        self._order_info['algo_comment'] = comment

    @property
    def broker(self):
        return self._order_info['broker']

    @property
    def broker_account(self):
        return self._order_info['broker_account']

    @property
    def broker_permid(self):
        return self._order_info['broker_permid']

    @broker_permid.setter
    def broker_permid(self, permid):
        self._order_info['broker_permid'] = permid

    @property
    def broker_clientid(self):
        return self._order_info['broker_clientid']


    @property
    def broker_tempid(self):
        return self._order_info['broker_tempid']

    @property
    def commission(self):
        return self._order_info['commission']

    @commission.setter
    def commission(self, comm):
        self._order_info['commission'] = comm

    @classmethod
    def from_dict(instrumentOrder, order_as_dict):
        trade = order_as_dict.pop('trade')
        key = order_as_dict.pop('key')
        fill = order_as_dict.pop('fill')
        filled_price = order_as_dict.pop('filled_price')
        fill_datetime = order_as_dict.pop('fill_datetime')

        locked = order_as_dict.pop('locked')
        order_id = none_to_object(order_as_dict.pop('order_id'), no_order_id)
        modification_status = order_as_dict.pop('modification_status')
        modification_quantity = order_as_dict.pop('modification_quantity')
        parent = none_to_object(order_as_dict.pop('parent'), no_parent)
        children = none_to_object(order_as_dict.pop('children'), no_children)
        active = order_as_dict.pop('active')

        order_info = order_as_dict

        order = brokerOrder(key, trade, fill=fill, locked = locked, order_id = order_id,
                      modification_status = modification_status,
                      modification_quantity = modification_quantity,
                      parent = parent, children = children,
                      active = active, filled_price = filled_price, fill_datetime = fill_datetime,
                      **order_info)

        return order



    ## Following methods for compatibility with parent class

    @property
    def roll_order(self):
        return False


    @property
    def inter_spread_order(self):
        return False

    @property
    def reference_price(self):
        return None

    @property
    def algo_to_use(self):
        return self.algo_used()

    @property
    def manual_trade(self):
        return False
