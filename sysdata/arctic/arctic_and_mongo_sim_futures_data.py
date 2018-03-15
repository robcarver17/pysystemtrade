"""
Get data from mongo and arctic used for futures trading

"""

import os

import pandas as pd

from syscore.fileutils import get_pathname_for_package

from sysdata.data import simData
from sysdata.futures.futuresDataForSim import futuresAdjustedPriceData, futuresConfigDataForSim, futuresMultiplePriceData

from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData

"""
Static variables to store location of data
"""


class dbconnections(simData):
    def __init__(self, database_name):
        """

        Use a different database
        """

        super().__init__()

        setattr(self, "_database_name", database_name)


"""
The next two sub classes are unusual in that they directly access the relevant files rather than going by another data object

  (i) specified as override_data_path on __init__ (via csvPaths init),
  ii) specified in the datapath_dict with the relevant keyname on __init__ (via csvPaths init),
  iii) specified in this file as DEFAULT_SIM_CONFIG_PATH
"""

class mongoFuturesConfigDataForSim():
    pass

class csvFuturesConfigDataForSim(csvPaths, futuresConfigDataForSim):
    """
    Get futures specific data from legacy csv files

    """


    def _get_instrument_data(self):
        """
        Get a data frame of interesting information about instruments, either
        from a file or cached

        :returns: pd.DataFrame

        >>> data=csvFuturesConfigDataForSim(datapath_dict=dict(config_data = "sysdata.tests.configtestdata"))
        >>> data._get_instrument_data()
                   Instrument  Pointsize AssetClass Currency  Shortonly
        Instrument
        EDOLLAR       EDOLLAR       2500       STIR      USD      False
        US10             US10       1000       Bond      USD      False
        BUND             BUND       1000       Bond      EUR      False
        >>> data.get_instrument_asset_classes()
        Instrument
        EDOLLAR    STIR
        US10       Bond
        BUND       Bond
        Name: AssetClass, dtype: object
        >>> data.get_value_of_block_price_move("EDOLLAR")
        2500
        >>> data.get_instrument_currency("US10")
        'USD'
        """

        self.log.msg("Loading csv instrument config")

        pathname = get_pathname_for_package(self._resolve_path("config_data", DEFAULT_SIM_CONFIG_PATH))

        filename = os.path.join(pathname, "instrumentconfig.csv")
        instr_data = pd.read_csv(filename)
        instr_data.index = instr_data.Instrument

        return instr_data


    def _get_all_cost_data(self):
        """
        Get a data frame of cost data

        :returns: pd.DataFrame

        >>> data=csvFuturesConfigDataForSim(datapath_dict=dict(config_data = "sysdata.tests.configtestdata"))
        >>> data._get_all_cost_data()
                   Instrument  Slippage  PerBlock  Percentage  PerTrade
        Instrument
        BUND             BUND    0.0050      2.00           0         0
        US10             US10    0.0080      1.51           0         0
        EDOLLAR       EDOLLAR    0.0025      2.11           0         0
        >>> data.get_raw_cost_data("EDOLLAR")['price_slippage']
        0.0025000000000000001
        """

        self.log.msg("Loading csv cost file")

        pathname = get_pathname_for_package(self._resolve_path("config_data", DEFAULT_SIM_CONFIG_PATH))
        filename = os.path.join(pathname, "costs_analysis.csv")
        try:
            instr_data = pd.read_csv(filename)
            instr_data.index = instr_data.Instrument

            return instr_data
        except OSError:
            self.log.warn("Cost file not found %s" % filename)
            return None

"""
The rest of these sub classes all follow the pattern of accessing a data object specific to the type of data being read
The directory they look in will be eithier be
  (i) specified as override_data_path on __init__ (via csvPaths init),
  ii) specified in the datapath_dict with the relevant keyname on __init__ (via csvPaths init),
  iii) default specified in the file of the specific data object

"""


class arcticFuturesAdjustedPriceSimData(dbconnections, futuresAdjustedPriceData):
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
            instrument_code=instrument_code)

        adj_prices_data = self._get_adj_prices_data_object()
        adj_prices = adj_prices_data.get_adjusted_prices(instrument_code)

        return adj_prices

    def get_instrument_list(self):
        adj_prices_data = self._get_adj_prices_data_object()
        instrument_list = adj_prices_data.get_list_of_instruments()

        return instrument_list

    def _get_adj_prices_data_object(self):
        adj_prices_data = arcticFuturesAdjustedPricesData(self._database_name)
        adj_prices_data.log = self.log

        return adj_prices_data

class arcticFuturesMultiplePriceSimData(dbconnections, futuresMultiplePriceData):

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
            instrument_code=instrument_code)

        multiple_prices_data = self._get_all_prices_data_object()
        instr_all_price_data = multiple_prices_data.get_multiple_prices(instrument_code)

        return instr_all_price_data

    def _get_all_prices_data_object(self):

        multiple_prices_data_object = arcticFuturesMultiplePriceSimData(self._database_name)
        multiple_prices_data_object.log = self.log

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

        self.log.msg("Loading arctic fx data", fx="%s%s" % (currency1, currency2))

        if currency1 == currency2:
            return self._get_default_series()

        fx_prices_data_object = self._get_fx_data_object()
        currency_code = currency1+currency2

        fx_prices = fx_prices_data_object.get_fx_prices(currency_code)

        if fx_prices.empty:
            return None

        return fx_prices

    def _get_fx_data_object(self):

        fx_prices_data_object = arcticFXSimData(self._database_name)
        fx_prices_data_object.log = self.log

        return fx_prices_data_object
"""
This class ties everything together so we can just create a single object every time we need to access mongo data for sim

"""

class arcticFuturesSimData(arcticFXSimData, arcticFuturesAdjustedPriceSimData,
                           mongoFuturesConfigDataForSim, arcticFuturesMultiplePriceSimData):
    """
        Get futures specific data from mongo and arctic

        Extends the FuturesData class for a specific data source

    """

    def __repr__(self):
        return "arcticFuturesSimData for %d instruments" % len(self.get_instrument_list())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
