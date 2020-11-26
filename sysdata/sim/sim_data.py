import pandas as pd

from syscore.objects import get_methods
from sysdata.base_data import baseData
from systems.basesystem import System

from sysobjects.spot_fx_prices import fxPrices
from sysobjects.instruments import instrumentCosts



class simData(baseData):
    """
    Core data object - Base class for simulation

    simData objects are used to get a collection of data

    The bare simData class isn't much good and holds only price and fx data

    Normally we'd inherit from this for specific asset classes (eg carry data for futures), and then for a
      specific source of data (eg csv files, databases, ...)

    The inheritance is:

    -> asset class specific eg futuresdata.FuturesData
    -> source specific eg legacy.csvFuturesSimData

    We can plug in different sources if desired

    """

    def __repr__(self):
        return "simData object with %d instruments" % len(
            self.get_instrument_list())

    def __getitem__(self, keyname: str):
        """
         convenience method to get the price, make it look like a dict

        :param keyname: instrument to get prices for
        :type keyname: str

        :returns: pd.DataFrame
        """
        price = self.get_raw_price(keyname)

        return price

    def keys(self) -> list:
        """
        list of instruments in this data set

        :returns: list of str

        >>> data=simData()
        >>> data.keys()
        []
        """
        return self.get_instrument_list()


    def _system_init(self, base_system: System):
        """
        This is run when added to a base system

        :param base_system
        :return: nothing
        """

        # inherit the log
        self._log = base_system.log.setup(stage="data")

    def methods(self) -> list:
        return get_methods(self)

    def daily_prices(self, instrument_code: str) -> pd.Series:
        """
        Gets daily prices

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.Series

        """
        instrprice = self.get_raw_price(instrument_code)
        dailyprice = instrprice.resample("1B").last()

        return dailyprice

    def get_fx_for_instrument(self, instrument_code: str, base_currency: str) -> fxPrices:
        """
        Get the FX rate between the FX rate for the instrument and the base (account) currency

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :param base_currency: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.Series

        >>> data=simData()
        >>> data.get_fx_for_instrument("wibble", "USD").tail(5)
        2040-12-04    1.0
        2040-12-05    1.0
        2040-12-06    1.0
        2040-12-07    1.0
        2040-12-10    1.0
        Freq: B, dtype: float64
        """

        instrument_currency = self.get_instrument_currency(instrument_code)
        fx_rate_series = self._get_fx_data(instrument_currency, base_currency)

        return fx_rate_series


    def get_raw_price(self, instrument_code: str) -> pd.Series:
        """
        Default method to get instrument price
        Will usually be overriden when inherited with specific data source

        :param instrument_code: instrument to get prices for
        :type instrument_code: str

        :returns: pd.Series

        """
        raise NotImplementedError("Need to inherit from simData")


    def get_instrument_list(self) -> list:
        """
        list of instruments in this data set

        :returns: list of str

        """
        raise NotImplementedError("Need to inherit from simData")


    def get_value_of_block_price_move(self, instrument_code: str) -> float:
        """
        How much does a $1 (or whatever) move in the price of an instrument block affect its value?
        eg 100.0 for 100 shares

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: float

        """
        self.log.warn("Using base method of simData, value of block price move may not be accurate")

        return 1.0

    def get_raw_cost_data(self, instrument_code: str) -> instrumentCosts:
        """
        Get cost data

        Execution slippage [half spread] price units
        Commission (local currency) per block
        Commission - percentage of value (0.01 is 1%)
        Commission (local currency) per block

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: dict of floats

        """

        self.log.warn("Using base method of simData, using zero costs")

        return instrumentCosts()

    def get_instrument_currency(self, instrument_code: str)-> str:
        """
        Get the currency for a particular instrument

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: str

        """

        raise NotImplementedError(
            "Need to inherit from base class for specific data source"
        )

    def _get_fx_data(self, currency1: str, currency2: str) -> fxPrices:
        """
        Get the FX rate currency1/currency2 between two currencies
        Or return None if not available

        (Normally we'd over ride this with a specific source)


        """
        raise NotImplementedError("Need to inherit for a specific data source")


