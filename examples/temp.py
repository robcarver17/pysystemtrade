# Gist example of IB wrapper ...
#
# Download API from http://interactivebrokers.github.io/#
#
# Install python API code /IBJts/source/pythonclient $ python3 setup.py install
#
# Note: The test cases, and the documentation refer to a python package called IBApi,
#    but the actual package is called ibapi. Go figure.
#
# Get the latest version of the gateway:
# https://www.interactivebrokers.com/en/?f=%2Fen%2Fcontrol%2Fsystemstandalone-ibGateway.php%3Fos%3Dunix
#    (for unix: windows and mac users please find your own version)
#
# Run the gateway
#
# user: edemo
# pwd: demo123
#
# Now I'll try and replicate the historical data example

from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract as IBcontract
from ibapi.order import Order
from ibapi.execution import ExecutionFilter

import time
from threading import Thread
import queue
import datetime
from copy import deepcopy

## these are just arbitrary numbers in leiu of a policy on this sort of thing
DEFAULT_MARKET_DATA_ID=50
DEFAULT_GET_CONTRACT_ID=43
DEFAULT_EXEC_TICKER=78

## marker for when queue is finished
FINISHED = object()
STARTED = object()
TIME_OUT = object()

## This is the reqId IB API sends when a fill is received
FILL_CODE=-1

"""
Next section is 'scaffolding'
"""

class finishableQueue(object):
    """
    Creates a queue which will finish at some point
    """

    def __init__(self, queue_to_finish):

        self._queue = queue_to_finish
        self.status = STARTED

    def get(self, timeout):
        """
        Returns a list of queue elements once timeout is finished, or a FINISHED flag is received in the queue
        :param timeout: how long to wait before giving up
        :return: list of queue elements
        """
        contents_of_queue=[]
        finished=False

        while not finished:
            try:
                current_element = self._queue.get(timeout=timeout)
                if current_element is FINISHED:
                    finished = True
                    self.status = FINISHED
                else:
                    contents_of_queue.append(current_element)
                    ## keep going and try and get more data

            except queue.Empty:
                ## If we hit a time out it's most probable we're not getting a finished element any time soon
                ## give up and return what we have
                finished = True
                self.status = TIME_OUT


        return contents_of_queue

    def timed_out(self):
        return self.status is TIME_OUT

"""
Mergable objects are used to capture order and execution information which comes from different sources and needs
  glueing together
"""

## marker to show a mergable object hasn't got any attributes
NO_ATTRIBUTES_SET=object()

class mergableObject(object):
    """
    Generic object to make it easier to munge together incomplete information about orders and executions
    """

    def __init__(self, id, **kwargs):
        """
        :param id: master reference, has to be an immutable type
        :param kwargs: other attributes which will appear in list returned by attributes() method
        """

        self.id=id
        attr_to_use=self.attributes()

        for argname in kwargs:
            if argname in attr_to_use:
                setattr(self, argname, kwargs[argname])
            else:
                print("Ignoring argument passed %s: is this the right kind of object? If so, add to .attributes() method" % argname)

    def attributes(self):
        ## should return a list of str here
        ## eg return ["thingone", "thingtwo"]
        return NO_ATTRIBUTES_SET

    def _name(self):
        return "Generic Mergable object - "

    def __repr__(self):

        attr_list = self.attributes()
        if attr_list is NO_ATTRIBUTES_SET:
            return self._name()

        return self._name()+" ".join([ "%s: %s" % (attrname, str(getattr(self, attrname))) for attrname in attr_list
                                                  if getattr(self, attrname, None) is not None])

    def merge(self, details_to_merge, overwrite=True):
        """
        Merge two things
        self.id must match
        :param details_to_merge: thing to merge into current one
        :param overwrite: if True then overwrite current values, otherwise keep current values
        :return: merged thing
        """

        if self.id!=details_to_merge.id:
            raise Exception("Can't merge details with different IDS %d and %d!" % (self.id, details_to_merge.id))

        arg_list = self.attributes()
        if arg_list is NO_ATTRIBUTES_SET:
            ## self is a generic, empty, object.
            ## I can just replace it wholesale with the new object

            new_object = details_to_merge

            return new_object

        new_object = deepcopy(self)

        for argname in arg_list:
            my_arg_value = getattr(self, argname, None)
            new_arg_value = getattr(details_to_merge, argname, None)

            if new_arg_value is not None:
                ## have something to merge
                if my_arg_value is not None and not overwrite:
                    ## conflict with current value, don't want to overwrite, skip
                    pass
                else:
                    setattr(new_object, argname, new_arg_value)

        return new_object


class orderInformation(mergableObject):
    """
    Collect information about orders
    master ID will be the orderID
    eg you'd do order_details = orderInformation(orderID, contract=....)
    """

    def _name(self):
        return "Order - "

    def attributes(self):
        return ['contract','order','orderstate','status',
                 'filled', 'remaining', 'avgFillPrice', 'permid',
                 'parentId', 'lastFillPrice', 'clientId', 'whyHeld',
                'mktCapPrice']


class execInformation(mergableObject):
    """
    Collect information about executions
    master ID will be the execid
    eg you'd do exec_info = execInformation(execid, contract= ... )
    """

    def _name(self):
        return "Execution - "

    def attributes(self):
        return ['contract','ClientId','OrderId','time','AvgPrice','Price','AcctNumber',
                'Shares','Commission', 'commission_currency', 'realisedpnl']


class list_of_mergables(list):
    """
    A list of mergable objects, like execution details or order information
    """


    def merged_dict(self):
        """
        Merge and remove duplicates of a stack of mergable objects with unique ID
        Essentially creates the union of the objects in the stack
        :return: dict of mergableObjects, keynames .id
        """

        ## We create a new stack of order details which will contain merged order or execution details
        new_stack_dict = {}

        for stack_member in self:
            id = stack_member.id

            if id not in new_stack_dict.keys():
                ## not in new stack yet, create a 'blank' object
                ## Note this will have no attributes, so will be replaced when merged with a proper object
                new_stack_dict[id] = mergableObject(id)

            existing_stack_member = new_stack_dict[id]

            ## add on the new information by merging
            ## if this was an empty 'blank' object it will just be replaced with stack_member
            new_stack_dict[id] = existing_stack_member.merge(stack_member)

        return new_stack_dict


    def blended_dict(self, stack_to_merge):
        """
        Merges any objects in new_stack with the same ID as those in the original_stack
        :param self: list of mergableObject or inheritors thereof
        :param stack_to_merge: list of mergableObject or inheritors thereof
        :return: dict of mergableObjects, keynames .id
        """

        ## We create a new dict stack of order details which will contain merged details

        new_stack = {}

        ## convert the thing we're merging into a dictionary
        stack_to_merge_dict = stack_to_merge.merged_dict()

        for stack_member in self:
            id = stack_member.id
            new_stack[id] = deepcopy(stack_member)

            if id in stack_to_merge_dict.keys():
                ## add on the new information by merging without overwriting
                new_stack[id] = stack_member.merge(stack_to_merge_dict[id], overwrite=False)

        return new_stack


## Just to make the code more readable

class list_of_execInformation(list_of_mergables):
    pass

class list_of_orderInformation(list_of_mergables):
    pass

"""
Now into the main bit of the code; Wrapper and Client objects
"""

class TestWrapper(EWrapper):
    """
    The wrapper deals with the action coming back from the IB gateway or TWS instance
    We override methods in EWrapper that will get called when this action happens, like currentTime
    Extra methods are added as we need to store the results in this object
    """

    def __init__(self):
        self._my_contract_details = {}
        self._my_requested_execution = {}

        ## We set these up as we could get things coming along before we run an init
        self._my_executions_stream = queue.Queue()
        self._my_commission_stream = queue.Queue()
        self._my_open_orders = queue.Queue()

    ## error handling code
    def init_error(self):
        error_queue=queue.Queue()
        self._my_errors = error_queue

    def get_error(self, timeout=5):
        if self.is_error():
            try:
                return self._my_errors.get(timeout=timeout)
            except queue.Empty:
                return None

        return None

    def is_error(self):
        an_error_if=not self._my_errors.empty()
        return an_error_if

    def error(self, id, errorCode, errorString):
        ## Overriden method
        errormsg = "IB error id %d errorcode %d string %s" % (id, errorCode, errorString)
        self._my_errors.put(errormsg)


    ## get contract details code
    def init_contractdetails(self, reqId):
        contract_details_queue = self._my_contract_details[reqId] = queue.Queue()

        return contract_details_queue

    def contractDetails(self, reqId, contractDetails):
        ## overridden method

        if reqId not in self._my_contract_details.keys():
            self.init_contractdetails(reqId)

        self._my_contract_details[reqId].put(contractDetails)

    def contractDetailsEnd(self, reqId):
        ## overriden method
        if reqId not in self._my_contract_details.keys():
            self.init_contractdetails(reqId)

        self._my_contract_details[reqId].put(FINISHED)

    # orders
    def init_open_orders(self):
        open_orders_queue = self._my_open_orders = queue.Queue()

        return open_orders_queue


    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permid,
                    parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):

        order_details = orderInformation(orderId, status=status, filled=filled,
                 avgFillPrice=avgFillPrice, permid=permid,
                 parentId=parentId, lastFillPrice=lastFillPrice, clientId=clientId,
                                         whyHeld=whyHeld, mktCapPrice=mktCapPrice)

        self._my_open_orders.put(order_details)


    def openOrder(self, orderId, contract, order, orderstate):
        """
        Tells us about any orders we are working now
        overriden method
        """

        order_details = orderInformation(orderId, contract=contract, order=order, orderstate = orderstate)
        self._my_open_orders.put(order_details)


    def openOrderEnd(self):
        """
        Finished getting open orders
        Overriden method
        """

        self._my_open_orders.put(FINISHED)


    """ Executions and commissions
    requested executions get dropped into single queue: self._my_requested_execution[reqId]
    Those that arrive as orders are completed without a relevant reqId go into self._my_executions_stream
    All commissions go into self._my_commission_stream (could be requested or not)
    The *_stream queues are permanent, and init when the TestWrapper instance is created
    """


    def init_requested_execution_data(self, reqId):
        execution_queue = self._my_requested_execution[reqId] = queue.Queue()

        return execution_queue

    def access_commission_stream(self):
        ## Access to the 'permanent' queue for commissions

        return self._my_commission_stream

    def access_executions_stream(self):
        ## Access to the 'permanent' queue for executions

        return self._my_executions_stream


    def commissionReport(self, commreport):
        """
        This is called if
        a) we have submitted an order and a fill has come back
        b) We have asked for recent fills to be given to us
        However no reqid is ever passed
        overriden method
        :param commreport:
        :return:
        """

        commdata = execInformation(commreport.execId, Commission=commreport.commission,
                        commission_currency = commreport.currency,
                        realisedpnl = commreport.realizedPNL)


        ## there are some other things in commreport you could add
        ## make sure you add them to the .attributes() field of the execInformation class

        ## These always go into the 'stream' as could be from a request, or a fill thats just happened
        self._my_commission_stream.put(commdata)


    def execDetails(self, reqId, contract, execution):
        """
        This is called if
        a) we have submitted an order and a fill has come back (in which case reqId will be FILL_CODE)
        b) We have asked for recent fills to be given to us (reqId will be
        See API docs for more details
        """
        ## overriden method

        execdata = execInformation(execution.execId, contract=contract,
                                   ClientId=execution.clientId, OrderId=execution.orderId,
                                   time=execution.time, AvgPrice=execution.avgPrice,
                                   AcctNumber=execution.acctNumber, Shares=execution.shares,
                                   Price = execution.price)

        ## there are some other things in execution you could add
        ## make sure you add them to the .attributes() field of the execInformation class

        reqId = int(reqId)

        ## We eithier put this into a stream if its just happened, or store it for a specific request
        if reqId==FILL_CODE:
            self._my_executions_stream.put(execdata)
        else:
            self._my_requested_execution[reqId].put(execdata)



    def execDetailsEnd(self, reqId):
        """
        No more orders to look at if execution details requested
        """
        self._my_requested_execution[reqId].put(FINISHED)


    ## order ids
    def init_nextvalidid(self):

        orderid_queue = self._my_orderid_data = queue.Queue()

        return orderid_queue

    def nextValidId(self, orderId):
        """
        Give the next valid order id
        Note this doesn't 'burn' the ID; if you call again without executing the next ID will be the same
        If you're executing through multiple clients you are probably better off having an explicit counter
        """
        if getattr(self, '_my_orderid_data', None) is None:
            ## getting an ID which we haven't asked for
            ## this happens, IB server just sends this along occassionally
            self.init_nextvalidid()

        self._my_orderid_data.put(orderId)


class TestClient(EClient):
    """
    The client method
    We don't override native methods, but instead call them from our own wrappers
    """
    def __init__(self, wrapper):
        ## Set up with a wrapper inside
        EClient.__init__(self, wrapper)

        self._market_data_q_dict = {}
        self._commissions=list_of_execInformation()

    def resolve_ib_contract(self, ibcontract, reqId=DEFAULT_GET_CONTRACT_ID):

        """
        From a partially formed contract, returns a fully fledged version
        :returns fully resolved IB contract
        """

        ## Make a place to store the data we're going to return
        contract_details_queue = finishableQueue(self.init_contractdetails(reqId))

        print("Getting full contract details from the server... ")

        self.reqContractDetails(reqId, ibcontract)

        ## Run until we get a valid contract(s) or get bored waiting
        MAX_WAIT_SECONDS = 10
        new_contract_details = contract_details_queue.get(timeout = MAX_WAIT_SECONDS)

        while self.wrapper.is_error():
            print(self.get_error())

        if contract_details_queue.timed_out():
            print("Exceeded maximum wait for wrapper to confirm finished - seems to be normal behaviour")

        if len(new_contract_details)==0:
            print("Failed to get additional contract details: returning unresolved contract")
            return ibcontract

        if len(new_contract_details)>1:
            print("got multiple contracts using first one")

        new_contract_details=new_contract_details[0]

        resolved_ibcontract=new_contract_details.summary

        return resolved_ibcontract


    def get_next_brokerorderid(self):
        """
        Get next broker order id
        :return: broker order id, int; or TIME_OUT if unavailable
        """

        ## Make a place to store the data we're going to return
        orderid_q = self.init_nextvalidid()

        self.reqIds(-1) # -1 is irrelevant apparently (see IB API docs)

        ## Run until we get a valid contract(s) or get bored waiting
        MAX_WAIT_SECONDS = 10
        try:
            brokerorderid = orderid_q.get(timeout=MAX_WAIT_SECONDS)
        except queue.Empty:
            print("Wrapper timeout waiting for broker orderid")
            brokerorderid = TIME_OUT

        while self.wrapper.is_error():
            print(self.get_error(timeout=MAX_WAIT_SECONDS))

        return brokerorderid


    def place_new_IB_order(self, ibcontract, order, orderid=None):
        """
        Places an order
        Returns brokerorderid
        """

        ## We can eithier supply our own ID or ask IB to give us the next valid one
        if orderid is None:
            print("Getting orderid from IB")
            orderid = self.get_next_brokerorderid()

            if orderid is TIME_OUT:
                raise Exception("I couldn't get an orderid from IB, and you didn't provide an orderid")

        print("Using order id of %d" % orderid)

        ## Note: It's possible if you have multiple traidng instances for orderids to be submitted out of sequence
        ##   in which case IB will break

        # Place the order
        self.placeOrder(
            orderid,  # orderId,
            ibcontract,  # contract,
            order  # order
        )

        return orderid


    def any_open_orders(self):
        """
        Simple wrapper to tell us if we have any open orders
        """

        return len(self.get_open_orders()) > 0


    def get_open_orders(self):
        """
        Returns a list of any open orders
        """

        ## store the orders somewhere
        open_orders_queue = finishableQueue(self.init_open_orders())

        ## You may prefer to use reqOpenOrders() which only retrieves orders for this client
        self.reqAllOpenOrders()

        ## Run until we get a terimination or get bored waiting
        MAX_WAIT_SECONDS = 5
        open_orders_list = list_of_orderInformation(open_orders_queue.get(timeout = MAX_WAIT_SECONDS))

        while self.wrapper.is_error():
            print(self.get_error())

        if open_orders_queue.timed_out():
            print("Exceeded maximum wait for wrapper to confirm finished whilst getting orders")

        ## open orders queue will be a jumble of order details, turn into a tidy dict with no duplicates
        open_orders_dict = open_orders_list.merged_dict()

        return open_orders_dict


    def get_executions_and_commissions(self, reqId=DEFAULT_EXEC_TICKER, execution_filter = ExecutionFilter()):
        """
        Returns a list of all executions done today with commission data
        """

        ## store somewhere
        execution_queue = finishableQueue(self.init_requested_execution_data(reqId))

        ## We can change ExecutionFilter to subset different orders
        ## note this will also pull in commissions but we would use get_executions_with_commissions
        self.reqExecutions(reqId, execution_filter)

        ## Run until we get a terimination or get bored waiting
        MAX_WAIT_SECONDS = 10
        exec_list = list_of_execInformation(execution_queue.get(timeout = MAX_WAIT_SECONDS))

        while self.wrapper.is_error():
            print(self.get_error())

        if execution_queue.timed_out():
            print("Exceeded maximum wait for wrapper to confirm finished whilst getting exec / commissions")

        ## Commissions will arrive seperately. We get all of them, but will only use those relevant for us
        commissions = self._all_commissions()

        ## glue them together, create a dict, remove duplicates
        all_data = exec_list.blended_dict(commissions)

        return all_data


    def _recent_fills(self):
        """
        Returns any fills since we last called recent_fills
        :return: list of executions as execInformation objects
        """

        ## we don't set up a queue but access the permanent one
        fill_queue = self.access_executions_stream()

        list_of_fills=list_of_execInformation()

        while not fill_queue.empty():
            MAX_WAIT_SECONDS = 5
            try:
                next_fill = fill_queue.get(timeout=MAX_WAIT_SECONDS)
                list_of_fills.append(next_fill)
            except queue.Empty:
                ## corner case where Q emptied since we last checked if empty at top of while loop
                pass

        ## note this could include duplicates and is a list
        return list_of_fills


    def recent_fills_and_commissions(self):
        """
        Return recent fills, with commissions added in
        :return: dict of execInformation objects, keys are execids
        """

        recent_fills = self._recent_fills()
        commissions = self._all_commissions() ## we want all commissions

        ## glue them together, create a dict, remove duplicates
        all_data = recent_fills.blended_dict(commissions)

        return all_data


    def _recent_commissions(self):
        """
        Returns any commissions that are in the queue since we last checked
        :return: list of commissions as execInformation objects
        """

        ## we don't set up a queue, as there is a permanent one
        comm_queue = self.access_commission_stream()

        list_of_comm=list_of_execInformation()

        while not comm_queue.empty():
            MAX_WAIT_SECONDS = 5
            try:
                next_comm = comm_queue.get(timeout=MAX_WAIT_SECONDS)
                list_of_comm.append(next_comm)
            except queue.Empty:
                ## corner case where Q emptied since we last checked if empty at top of while loop
                pass

        ## note this could include duplicates and is a list
        return list_of_comm


    def _all_commissions(self):
        """
        Returns all commissions since we created this instance
        :return: list of commissions as execInformation objects
        """

        original_commissions = self._commissions
        latest_commissions = self._recent_commissions()

        all_commissions = list_of_execInformation(original_commissions + latest_commissions)

        self._commissions = all_commissions

        # note this could include duplicates and is a list
        return all_commissions


    def cancel_order(self, orderid):

        ## Has to be an order placed by this client. I don't check this here -
        ## If you have multiple IDs then you you need to check this yourself.

        self.cancelOrder(orderid)

        ## Wait until order is cancelled
        start_time=datetime.datetime.now()
        MAX_WAIT_TIME_SECONDS = 10

        finished = False

        while not finished:
            if orderid not in self.get_open_orders():
                ## finally cancelled
                finished = True

            if (datetime.datetime.now() - start_time).seconds > MAX_WAIT_TIME_SECONDS:
                print("Wrapper didn't come back with confirmation that order was cancelled!")
                finished = True

        ## return nothing

    def cancel_all_orders(self):

        ## Cancels all orders, from all client ids.
        ## if you don't want to do this, then instead run .cancel_order over named IDs
        app.reqGlobalCancel()

        start_time=datetime.datetime.now()
        MAX_WAIT_TIME_SECONDS = 10

        finished = False

        while not finished:
            if not self.any_open_orders():
                ## all orders finally cancelled
                finished = True
            if (datetime.datetime.now() - start_time).seconds > MAX_WAIT_TIME_SECONDS:
                print("Wrapper didn't come back with confirmation that all orders were cancelled!")
                finished = True

        ## return nothing

class TestApp(TestWrapper, TestClient):
    def __init__(self, ipaddress, portid, clientid):
        TestWrapper.__init__(self)
        TestClient.__init__(self, wrapper=self)

        self.connect(ipaddress, portid, clientid)

        thread = Thread(target = self.run)
        thread.start()

        setattr(self, "_thread", thread)

        self.init_error()


if __name__ == '__main__':

    app = TestApp("127.0.0.1", 4001, 1)

    ## lets get prices for this
    ibcontract = IBcontract()
    ibcontract.secType = "FUT"
    ibcontract.lastTradeDateOrContractMonth="201812"
    ibcontract.symbol="GE"
    ibcontract.exchange="GLOBEX"

    ## resolve the contract
    resolved_ibcontract = app.resolve_ib_contract(ibcontract)

    order1=Order()
    order1.action="BUY"
    order1.orderType="MKT"
    order1.totalQuantity=10
    order1.transmit = True

    orderid1 = app.place_new_IB_order(ibcontract, order1, orderid=None)

    print("Placed market order, orderid is %d" % orderid1)

    while app.any_open_orders():
        ## Warning this will pause forever if fill doesn't come back
        time.sleep(1)

    ## Have a look at the fill
    print("Recent fills")
    filldetails = app.recent_fills_and_commissions()
    print(filldetails)

    ## when I call again should be empty as we've cleared the memory of recent fills
    print("Recent fills (should be blank)")
    morefilldetails = app.recent_fills_and_commissions()
    print(morefilldetails)

    ## but this won't be
    print("Executions today")
    execdetails = app.get_executions_and_commissions()
    print(execdetails)

    ## And here is a limit order, unlikely ever to be filled
    ## Note limit price of 100

    order2=Order()
    order2.action="SELL"
    order2.orderType="LMT"
    order2.totalQuantity=12
    order2.lmtPrice = 100.0
    order2.tif = 'DAY'
    order2.transmit = True


    orderid2 = app.place_new_IB_order(ibcontract, order2, orderid=None)
    print("Placed limit order, orderid is %d" % orderid2)

    ## Short wait ...
    time.sleep(5)

    print("Open orders (should be one)")
    open_orders = app.get_open_orders()
    print(open_orders)

    ## put in another limit order
    order3=Order()
    order3.action="BUY"
    order3.orderType="LMT"
    order3.totalQuantity=5
    order3.lmtPrice = 10.0
    order3.tif = 'DAY'
    order3.transmit = True


    orderid3 = app.place_new_IB_order(ibcontract, order3, orderid=None)
    print("Placed limit order, orderid is %d" % orderid2)

    print("Open orders (should be two)")
    open_orders = app.get_open_orders()
    print(open_orders.keys())

    time.sleep(5)

    ## modify the order

    print("Modifying order %d" % orderid3)

    order3.lmtPrice = 15.0

    print("Limit price was %f will become %f" % (open_orders[orderid3].order.lmtPrice, order3.lmtPrice ))

    app.place_new_IB_order(ibcontract, order3, orderid=orderid3)
    time.sleep(5)
    open_orders = app.get_open_orders()
    print("New limit price %f " % open_orders[orderid3].order.lmtPrice)

    ## Cancel a single limit order, leaving one active limit order (order3)
    print("Cancel order %d " % orderid2)
    app.cancel_order(orderid2)
    open_orders = app.get_open_orders()

    print("Open orders (should just be %d)" % orderid2)
    print(open_orders.keys())

    print("Cancelling all orders")
    app.cancel_all_orders()

    print("Any open orders? - should be False")
    print(app.any_open_orders())

    app.disconnect()