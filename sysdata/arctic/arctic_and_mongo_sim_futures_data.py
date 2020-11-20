"""
Get data from mongo and arctic used for futures trading

"""

from syscore.objects import arg_not_supplied
from sysdata.base_data import simData
from sysdata.futures.futuresDataForSim import (
    futuresAdjustedPriceData,
    futuresConfigDataForSim,
    futuresMultiplePriceData,
)

from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.mongodb.mongo_connection import mongoDb
from sysdata.mongodb.mongo_futures_instruments import mongoFuturesInstrumentData

from syslogdiag.log import logtoscreen as logger

"""
Static variables to store location of data
"""


class dbconnections(simData):
    def __init__(self, mongo_db=arg_not_supplied, log=logger("arcticSimData")):
        """

        Use a different database
        """

        super().__init__(log = log)
        if mongo_db is arg_not_supplied:
            mongo_db = mongoDb()

        self.mongo_db = mongo_db


"""
The next two sub classes are unusual in that they directly access the relevant files rather than going by another data object

  (i) specified as override_data_path on __init__ (via csvPaths init),
  ii) specified in the datapath_dict with the relevant keyname on __init__ (via csvPaths init),
  iii) specified in this file as DEFAULT_SIM_CONFIG_PATH
"""


class mongoFuturesConfigDataForSim(dbconnections, futuresConfigDataForSim):
    def get_all_instrument_data(self):
        """
        Get a data frame of interesting information about instruments, either
        from a file or cached

        :returns: pd.DataFrame

        """

        data_object = self._get_config_data_object()

        all_instr_dataframe = data_object.get_all_instrument_data_as_df()

        return all_instr_dataframe

    def get_instrument_object(self, instrument_code):
        data_object = self._get_config_data_object()
        instr_data = data_object.get_instrument_data(instrument_code)

        return instr_data

    def _get_config_data_object(self):

        data_object = mongoFuturesInstrumentData(self.mongo_db)

        return data_object

    def _get_instrument_object_with_cost_data(self, instrument_code):
        """
        Get a data frame of cost data

        :returns: pd.DataFrame

        """

        mongo_configdata_object = self._get_config_data_object()
        instrument_object = mongo_configdata_object.get_instrument_data(
            instrument_code)

        return instrument_object


class arcticFuturesAdjustedPriceSimData(
        dbconnections, futuresAdjustedPriceData):
    """
    Get futures specific data from arctic database

    """

    def get_backadjusted_futures_price(self, instrument_code):
        """
        Get instrument price backadjusted

        :param instrument_code: instrument to get prices for
        :type instrument_code: str

        :returns: pd.DataFrame

        """

        self.log.msg(
            "Loading arctic data for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        adj_prices_data = self._get_adj_prices_data_object()
        adj_prices = adj_prices_data.get_adjusted_prices(instrument_code)

        return adj_prices

    def get_instrument_list(self):
        adj_prices_data = self._get_adj_prices_data_object()
        instrument_list = adj_prices_data.get_list_of_instruments()

        return instrument_list

    def _get_adj_prices_data_object(self):

        adj_prices_data = arcticFuturesAdjustedPricesData(self.mongo_db, log = self.log)

        return adj_prices_data


class arcticFuturesMultiplePriceSimData(
        dbconnections, futuresMultiplePriceData):
    def _get_all_price_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 6 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD, FORWARD_CONTRACT

        These are specifically needed for futures trading

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        """

        self.log.msg(
            "Loading arctic data for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        multiple_prices_data = self._get_all_prices_data_object()
        instr_all_price_data = multiple_prices_data.get_multiple_prices(
            instrument_code)

        return instr_all_price_data

    def _get_all_prices_data_object(self):

        multiple_prices_data_object = arcticFuturesMultiplePricesData(
            self.mongo_db, log = self.log)

        return multiple_prices_data_object


class arcticFXSimData(dbconnections, simData):
    """
    Get fx data from arctic


    """

    def _get_fx_data(self, currency1, currency2):
        """
        Get fx data

        :param currency1: numerator currency
        :type currency1: str

        :param currency2: denominator currency
        :type currency2: str

        :returns: Tx1 pd.DataFrame, or None if not available

        """

        self.log.msg(
            "Loading arctic fx data", fx="%s%s" %
            (currency1, currency2))

        fx_prices_data_object = self._get_fx_data_object()
        currency_code = currency1 + currency2

        fx_prices = fx_prices_data_object.get_fx_prices(currency_code)

        if fx_prices.empty:
            return None

        return fx_prices

    def _get_fx_data_object(self):

        fx_prices_data_object = arcticFxPricesData(self.mongo_db, log = self.log)

        return fx_prices_data_object


"""
This class ties everything together so we can just create a single object every time we need to access mongo data for sim

"""


class arcticFuturesSimData(
    arcticFXSimData,
    arcticFuturesAdjustedPriceSimData,
    mongoFuturesConfigDataForSim,
    arcticFuturesMultiplePriceSimData,
):
    """
    Get futures specific data from mongo and arctic

    Extends the FuturesData class for a specific data source

    """

    def __repr__(self):
        return "arcticFuturesSimData for %d instruments" % len(
            self.get_instrument_list()
        )


if __name__ == "__main__":
    import doctest

    doctest.testmod()
