from sysbrokers.baseServer import brokerServer
from ibapi import wrapper
import queue
from sysbrokers.baseServer import FINISHED
from syslogdiag.log import logtoscreen

class ibServer(wrapper.EWrapper, brokerServer):
    """
    Server specific to interactive brokers

    Overrides the methods in the base class specifically for IB

    """

    def __init__(self, log=logtoscreen("IBserver")):
        self._my_contract_details = {}
        self._my_historic_data_dict = {}

        self.log = log


    def error(self, id, errorCode, errorString):
        ## Overriden method
        ## Uses method in brokerServer to actually handle the error
        ## WHITELIST?

        errormsg = "IB error id %d errorcode %d string %s" % (id, errorCode, errorString)
        self.broker_error(errormsg)

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

    ## Historic data code
    def init_historicprices(self, tickerid):
        historic_data_queue = self._my_historic_data_dict[tickerid] = queue.Queue()

        return historic_data_queue


    def historicalData(self, tickerid , bar):

        ## Overriden method
        ## Note I'm choosing to ignore barCount, WAP and hasGaps but you could use them if you like
        bardata=(bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume)

        historic_data_dict=self._my_historic_data_dict

        ## Add on to the current data
        if tickerid not in historic_data_dict.keys():
            self.init_historicprices(tickerid)

        historic_data_dict[tickerid].put(bardata)

    def historicalDataEnd(self, tickerid, start:str, end:str):
        ## overriden method

        if tickerid not in self._my_historic_data_dict.keys():
            self.init_historicprices(tickerid)

        self._my_historic_data_dict[tickerid].put(FINISHED)
