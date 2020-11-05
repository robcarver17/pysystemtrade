"""
Get data from .csv files used for futures trading

"""

import os

import pandas as pd

from sysdata.data import simData
from sysdata.futures.futuresDataForSim import (
    futuresAdjustedPriceData,
    futuresConfigDataForSim,
    futuresMultiplePriceData,
)
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData
from sysdata.csv.csv_spot_fx import csvFxPricesData
from sysdata.csv.csv_instrument_config import csvFuturesInstrumentData

"""
Static variables to store location of data
"""


class csvPaths(simData):
    def __init__(self, override_datapath=None, datapath_dict={}):
        """

        We look for data in .csv files


        :param override_datapath: relative path to find .csv files. If missing
        :type override_datapath: None or str

        :param mixed_prices_datapath:

        :returns: new csvPaths object

        """

        super().__init__()

        setattr(self, "_override_datapath", override_datapath)
        setattr(self, "_datapath_dict", datapath_dict)

    def _resolve_path(self, path_attr_name, fallback_path=None):

        # a global 'datapath' overrides everything
        if self._override_datapath is not None:
            return self._override_datapath

        # if a specific path is provided use that
        if path_attr_name in self._datapath_dict.keys():
            return self._datapath_dict[path_attr_name]

        return fallback_path


"""
The rest of these sub classes all follow the pattern of accessing a data object specific to the type of data being read
The directory they look in will be either be
  (i) specified as override_data_path on __init__ (via csvPaths init),
  ii) specified in the datapath_dict with the relevant keyname on __init__ (via csvPaths init),
  iii) default specified in the file of the specific data object

"""


class csvFuturesConfigDataForSim(csvPaths, futuresConfigDataForSim):
    """
    Get futures specific data from legacy csv files

    """

    def get_all_instrument_data(self):
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

        data_object = self._get_config_data_object()

        all_instr_dataframe = data_object.get_all_instrument_data_as_df()

        return all_instr_dataframe

    def get_instrument_object(self, instrument_code):
        data_object = self._get_config_data_object()
        instr_data = data_object.get_instrument_data(instrument_code)

        return instr_data

    def _get_config_data_object(self):

        pathname = self._resolve_path("config_data")
        data_object = csvFuturesInstrumentData(datapath=pathname)

        return data_object

    def _get_instrument_object_with_cost_data(self, instrument_code):
        """
        Get a data frame of cost data

        :returns: pd.DataFrame

        >>> data=csvFuturesConfigDataForSim(datapath_dict=dict(config_data = "sysdata.tests.configtestdata"))
        >>> data.get_raw_cost_data("EDOLLAR").meta_data.price_slippage
        0.0025000000000000001
        """

        csv_data_object = self._get_config_data_object()
        instrument_object = csv_data_object.get_instrument_data(
            instrument_code)

        return instrument_object


class csvFuturesAdjustedPriceData(csvPaths, futuresAdjustedPriceData):
    """
    Get futures specific data from legacy csv files

    """

    def get_backadjusted_futures_price(self, instrument_code):
        """
        Get instrument price backadjusted

        :param instrument_code: instrument to get prices for
        :type instrument_code: str

        :returns: pd.DataFrame

        >>> data=csvFuturesAdjustedPriceData(datapath_dict=dict(config_data = "sysdata.tests.configtestdata", adjusted_prices = "sysdata.tests.adjtestdata"))
        >>> data.get_raw_price("EDOLLAR").tail(2)
        2018-01-12 15:33:47    97.4275
        2018-01-12 19:08:00    97.4425
        Name: price, dtype: float64
        >>> data["US10"].tail(2)
        2018-01-12 14:06:00    122.710938
        2018-01-12 15:06:40    122.820312
        Name: price, dtype: float64
        """

        # Read from .csv
        self.log.msg(
            "Loading csv data for %s" %
            instrument_code,
            instrument_code=instrument_code)

        adj_prices_data = self._get_adj_prices_data_object()
        adj_prices = adj_prices_data.get_adjusted_prices(instrument_code)

        return adj_prices

    def get_instrument_list(self):
        adj_prices_data = self._get_adj_prices_data_object()
        instrument_list = adj_prices_data.get_list_of_instruments()

        return instrument_list

    def _get_adj_prices_data_object(self):
        pathname = self._resolve_path("adjusted_prices")

        adj_prices_data = csvFuturesAdjustedPricesData(pathname)
        adj_prices_data.log = self.log

        return adj_prices_data


class csvFuturesMultiplePriceData(csvPaths, futuresMultiplePriceData):
    def _get_all_price_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 6 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD, FORWARD_CONTRACT

        These are specifically needed for futures trading

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        >>> data=csvMultiplePriceData(datapath_dict=dict(config_data = "sysdata.tests.configtestdata", multiple_price_data = "sysdata.tests.multiplepricestestdata"))
        >>> data.get_current_and_forward_price_data("US10").tail(4)
                                  PRICE    FORWARD PRICE_CONTRACT FORWARD_CONTRACT
        2018-01-11 18:57:32  123.070312        NaN         201803           201806
        2018-01-11 23:00:00  123.031250  122.65625         201803           201806
        2018-01-12 14:06:00  122.710938        NaN         201803           201806
        2018-01-12 15:06:40  122.820312        NaN         201803           201806
        >>> data.get_instrument_raw_carry_data("US10").tail(4)
                                  PRICE      CARRY PRICE_CONTRACT CARRY_CONTRACT
        2018-01-11 18:57:32  123.070312        NaN         201803         201806
        2018-01-11 23:00:00  123.031250  122.65625         201803         201806
        2018-01-12 14:06:00  122.710938        NaN         201803         201806
        2018-01-12 15:06:40  122.820312        NaN         201803         201806
        """

        self.log.msg(
            "Loading csv data for %s" %
            instrument_code,
            instrument_code=instrument_code)

        csv_multiple_prices_data = self._get_all_prices_data_object()
        instr_all_price_data = csv_multiple_prices_data.get_multiple_prices(
            instrument_code
        )

        return instr_all_price_data

    def _get_all_prices_data_object(self):

        pathname = self._resolve_path("multiple_price_data")

        csv_multiple_prices_data = csvFuturesMultiplePricesData(
            datapath=pathname)
        csv_multiple_prices_data.log = self.log

        return csv_multiple_prices_data


class csvFXData(csvPaths, simData):
    """
    Get fx data from legacy csv files


    """

    def _get_fx_data(self, currency1, currency2):
        """
        Get fx data

        :param currency1: numerator currency
        :type currency1: str

        :param currency2: denominator currency
        :type currency2: str

        :returns: Tx1 pd.DataFrame, or None if not available

        >>> data=csvFXData(datapath_dict=dict(spot_fx_data = "sysdata.tests.fxtestdata"))
        >>> data._get_fx_data("EUR", "USD").tail(2)
        2018-01-09    1.197046
        2018-01-10    1.192933
        Name: FX, dtype: float64
        """

        self.log.msg("Loading csv fx data", fx="%s%s" % (currency1, currency2))

        csv_fx_prices_data = self._get_fx_data_object()
        code = currency1 + currency2

        fx_prices = csv_fx_prices_data.get_fx_prices(code)

        if fx_prices.empty:
            raise Exception("No FX data for %s" % code)

        return fx_prices

    def _get_fx_data_object(self):
        pathname = self._resolve_path("spot_fx_data")
        csv_fx_prices_data = csvFxPricesData(pathname)
        csv_fx_prices_data.log = self.log

        return csv_fx_prices_data


"""
This class ties everything together so we can just create a single object every time we need to access csv data for sim

You could modify this to mix and match csv and non csv data

But you might need a custom __init__
"""


class csvFuturesSimData(
    csvFXData,
    csvFuturesAdjustedPriceData,
    csvFuturesConfigDataForSim,
    csvFuturesMultiplePriceData,
):
    """
    Get futures specific data from legacy csv files

    Extends the FuturesData class for a specific data source

    You can make this more interesting by replacing each of the objects above

    >>> data=csvFuturesSimData(datapath_dict=dict(config_data = "sysdata.tests.configtestdata", adjusted_prices = "sysdata.tests.adjtestdata", spot_fx_data = "sysdata.tests.fxtestdata", multiple_price_data = "sysdata.tests.multiplepricestestdata"))
    >>> data
    csvFuturesSimData for 6 instruments
    """

    def __repr__(self):
        return "csvFuturesSimData for %d instruments" % len(
            self.get_instrument_list())


if __name__ == "__main__":
    import doctest

    doctest.testmod()
