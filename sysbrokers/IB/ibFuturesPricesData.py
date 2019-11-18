import pandas as pd
from sysdata.futures.futures_per_contract_prices import futuresContractPriceData
from syslogdiag.log import logtoscreen
from syscore.fileutils import get_filename_for_package

IB_CCY_CONFIG_FILE = get_filename_for_package("sysbrokers.IB.ibConfigSpotFX.csv")

class ibFuturesContractPriceData(futuresContractPriceData):

    def __init__(self, ibconnection, log=logtoscreen("ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB Futures contracts price data"


    def get_instruments_with_price_data(self):
        """

        :return: list of str
        """
        # get from config file
        raise NotImplementedError("*WRITE SOME CODE*")

    def _get_prices_for_contract_object_no_checking(self, contract_object):
        """
        get some prices

        :param contract_object:  futuresContract
        :return: data
        """
        # issue: these are *historical* prices. Need a method for current price / streaming etc?

        # issues: we need IB contracts
        # issues: we need to translate our instrument into IB and back again
        # issue: we need the precise expiry date
        # issue: these dates need to be retrieved, and then stored somewhere
        # issue: so we need a database of contract/instrument objects
        # issue: all of the above stuff is generic (also use in order management, getting fills)
        # issue: so we need an IB contract object

        raise NotImplementedError("*WRITE SOME CODE*")

    def contracts_with_price_data_for_instrument_code(self, instrument_code):
        """
        Valid contracts

        :param instrument_code: str
        :return: list of contract_date
        """
        # return the contract chain
        raise NotImplementedError("*WRITE CODE*")

    def write_prices_for_contract_object(self, futures_contract_object, futures_price_data):
        raise Exception("IB is read only for prices")

    def _delete_prices_for_contract_object_with_no_checks_be_careful(self, futures_contract_object):
        raise Exception("IB is read only for prices")

    def get_contracts_with_price_data(self):
        """

        :return: list of futuresContact
        """
        raise Exception("You can't get a list of all contracts for all instruments with IB - do it instrument by instrument")

