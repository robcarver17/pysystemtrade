import datetime
import pandas as pd


from ibapi.client import EClient
from ibapi.contract import Contract as IBcontract

from sysbrokers.baseClient import brokerClient
from sysbrokers.baseServer import finishableQueue
from syscore.dateutils import expiry_date
from sysdata.fx.spotfx import fxPrices
from syslogdiag.log import logtoscreen

MAX_WAIT_SECONDS = 10

class ibClient(brokerClient, EClient):
    """
    Client specific to interactive brokers

    Overrides the methods in the base class specifically for IB

    """

    def __init__(self, wrapper, reqIDoffset, log=logtoscreen("ibClient")):
        ## Set up with a wrapper inside
        EClient.__init__(self, wrapper)
        self.ib_init_request_id_factory(reqIDoffset)
        self.log = log


    # Methods in parent class overriden here
    # These methods should abstract the broker completely
    def broker_get_fx_data(self, ccy1, ccy2="USD"):
        """
        Get some spot fx data

        :param ccy1: first currency in pair
        :param ccy2: second currency in pair
        :return: fxPrices object
        """

        specific_log = self.log.setup(fxrate=ccy1+"/"+ccy2)

        ibcontract = self.ib_spotfx_contract(ccy1, ccy2=ccy2, log=specific_log)
        fx_data_raw = self.ib_get_historical_data(ibcontract, durationStr="1 Y", barSizeSetting="1 day",
                                              whatToShow = "MIDPOINT", log=specific_log)
        # Format is (bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume)
        # turn into a pd.Series
        date_index = [expiry_date(fx_row[0]) for fx_row in fx_data_raw]
        closing_prices = [fx_row[4] for fx_row in fx_data_raw]
        fx_data_as_series = pd.Series(closing_prices, index = date_index)

        # turn into a fxPrices
        fx_data = fxPrices(fx_data_as_series)

        return fx_data

    """
    Most things need request IDs
    Let's make sure we don't reuse them accidentally
    """
    def ib_init_request_id_factory(self, reqIDoffset:int):
        #  generate request ids make sure multiple IDs don't conflict
        #  however if we run multiple processes this could happen
        #  hence we add reqIDoffset
        self._reqIDused = []
        self._reqIDoffset = reqIDoffset

    def ib_next_req_id(self):
        current_reqs_used = self._reqIDused
        if len(current_reqs_used)==0:
            next_req_id = self._reqIDoffset+1
        else:
            next_req_id = int(max(current_reqs_used) + 1)

        current_reqs_used.append(next_req_id)
        self._reqIDused = current_reqs_used

        return next_req_id

    def ib_clear_req_id(self, reqId):
        current_reqs_used = self._reqIDused
        try:
            current_reqs_used.remove(reqId)
        except ValueError:
            # not there
            pass

        return reqId

    # Broker specific methods
    # Called by parent class generics

    ## CONTRACTS
    def ib_spotfx_contract(self, ccy1, ccy2="USD", log=None):
        ibcontract = IBcontract()
        ibcontract.symbol = ccy1
        ibcontract.secType = 'CASH'
        ibcontract.exchange = 'IDEALPRO'
        ibcontract.currency = ccy2

        ibcontract = self.ib_resolve_contract(ibcontract, log=log)

        return ibcontract

    def ib_futures_contract(self, futures_contract_object):
        # THIS SORT OF THING, TED...
        # NEED CONFIG INFORMATION, IB SPECIFIC
        #ibcontract = IBcontract()
        #ibcontract.secType = "FUT"

        # NEED TO DEAL WITH VIX - BETTER TO POLL AVAILABLE CONTRACTS
        # THIS WOULD BE SLOW, SO NEED TO HAVE SOME LOGIC FOR WHEN CONTRACT DATE FULLY SPECIFIED ALREADY
        #ibcontract.lastTradeDateOrContractMonth = "201809"
        #ibcontract.symbol = "GE"
        #ibcontract.exchange = "GLOBEX"
        #ibcontract = self.ib_resolve_contract(ibcontract)

        #return ibcontract

        raise NotImplementedError

    def ib_resolve_contract(self, ibcontract, log=None):

        if log is None:
            log=self.log

        reqId = self.ib_next_req_id()
        ## Make a place to store the data we're going to return
        contract_details_queue = finishableQueue(self.init_contractdetails(reqId))

        log.msg("Getting full contract details from the server... ")

        self.reqContractDetails(reqId, ibcontract)

        ## Run until we get a valid contract(s) or get bored waiting

        new_contract_details = contract_details_queue.get(timeout=MAX_WAIT_SECONDS)

        self.ib_clear_req_id(reqId)

        while self.broker_is_error():
            self.log.warn(self.broker_get_error()) ## WHITELIST?

        if contract_details_queue.timed_out():
            self.log.msg("Exceeded maximum wait for wrapper to confirm finished - seems to be normal behaviour")

        if len(new_contract_details) == 0:
            self.log.warn("Failed to get additional contract details: returning unresolved contract")
            return ibcontract

        if len(new_contract_details) > 1:
            self.log.warn("Got multiple contracts using first one")

        new_contract_details = new_contract_details[0]

        resolved_ibcontract = new_contract_details.contract

        return resolved_ibcontract

    ## HISTORICAL DATA
    def ib_get_historical_data(self, ibcontract, durationStr="1 Y", barSizeSetting="1 day",
                               whatToShow = "TRADES", log=None):

        """
        Returns historical prices for a contract, up to today
        ibcontract is a Contract
        :returns list of prices in 4 tuples: Open high low close volume
        """

        if log is None:
            log = self.log

        # PACING VIOLATIONS ARE NOT HANDLED HERE
        # CALLING CODE SHOULD NOT VIOLATE RULE: Making more than 60 requests within any ten minute period.

        tickerid = self.ib_next_req_id()
        ## Make a place to store the data we're going to return
        historic_data_queue = finishableQueue(self.init_historicprices(tickerid))

        # Request some historical data. Native method in EClient
        self.reqHistoricalData(
            tickerid,  # tickerId,
            ibcontract,  # contract,
            datetime.datetime.today().strftime("%Y%m%d %H:%M:%S %Z"),  # endDateTime,
            durationStr,  # durationStr,
            barSizeSetting,  # barSizeSetting,
            whatToShow,  # whatToShow,
            1,  # useRTH,
            1,  # formatDate
            False,  # KeepUpToDate <<==== added for api 9.73.2
            [] ## chartoptions not used
        )

        ## Wait until we get a completed data, an error, or get bored waiting
        log.msg("Getting historical data from the server... could take %d seconds to complete " % MAX_WAIT_SECONDS)

        historic_data = historic_data_queue.get(timeout = MAX_WAIT_SECONDS)

        while self.wrapper.broker_is_error():
            # WHITELIST
            log.warn(self.broker_get_error())

        if historic_data_queue.timed_out():
            log.msg("Exceeded maximum wait for wrapper to confirm finished - seems to be normal behaviour")

        self.cancelHistoricalData(tickerid)
        self.ib_clear_req_id(tickerid)

        return historic_data
