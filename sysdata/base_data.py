import datetime
import pandas as pd
from syslogdiag.log import logtoscreen
from syscore.objects import get_methods


class baseData(object):
    """
    Core data object - Base class

    simData objects are used to get data from a particular source, and give certain information about it

    The baseData class is highly generic

    Normally we'd inherit from this for specific implementations (eg simulation, production for different data types),
      specific asset classes (eg carry data for futures), and then for a
      specific source of data (eg csv files, databases, ...)

    The inheritance is:

    Base generic class: simData
    -> implementation specific eg simData for simulation
    -> asset class specific eg futuresdata.FuturesData
    -> source specific eg legacy.csvFuturesSimData

    """

    def __init__(self, log=logtoscreen("baseData")):
        """
        simData socket base class

        >>> data = baseData()
        >>> data
        simData object
        """

        self._log = log

    def __repr__(self):
        return "simData object"

    @property
    def log(self):
        return self._log


    def __getitem__(self, keyname):
        """
         convenience method to get the price, make it look like a dict

        :param keyname: instrument to get prices for
        :type keyname: str

        :returns: pd.DataFrame
        """

        raise Exception(
            "__getitem__ not defined for baseData class: use a class where it has been overriden"
        )

    def keys(self):
        """
        list of things in this data set (futures contracts, instruments...)

        :returns: list of str

        >>> data=simData()
        >>> data.keys()
        []
        """

        raise Exception(
            "keys() not defined for baseData class: use a class where it has been overriden"
        )


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

    def _system_init(self, base_system):
        """
        This is run when added to a base system

        :param base_system
        :return: nothing
        """

        # inherit the log
        self._log = base_system.log.setup(stage="data")

    def methods(self):
        return get_methods(self)

    def daily_prices(self, instrument_code):
        """
        Gets daily prices

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.Series

        """
        instrprice = self.get_raw_price(instrument_code)
        dailyprice = instrprice.resample("1B").last()

        return dailyprice

    def get_raw_price(self, instrument_code):
        """
        Default method to get instrument price
        Will usually be overriden when inherited with specific data source

        :param instrument_code: instrument to get prices for
        :type instrument_code: str

        :returns: pd.Series

        """
        error_msg = (
            "You have created a simData() object; you might need to use a more specific data object" %
            instrument_code)
        self.log.critical(error_msg)

    def __getitem__(self, keyname):
        """
         convenience method to get the price, make it look like a dict

        :param keyname: instrument to get prices for
        :type keyname: str

        :returns: pd.DataFrame
        """
        price = self.get_raw_price(keyname)

        return price

    def get_instrument_list(self):
        """
        list of instruments in this data set

        :returns: list of str

        """
        return []

    def keys(self):
        """
        list of instruments in this data set

        :returns: list of str

        >>> data=simData()
        >>> data.keys()
        []
        """
        return self.get_instrument_list()

    def get_value_of_block_price_move(self, instrument_code):
        """
        How much does a $1 (or whatever) move in the price of an instrument block affect its value?
        eg 100.0 for 100 shares

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: float

        """

        return 1.0

    def get_raw_cost_data(self, instrument_code):
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

        return dict(
            price_slippage=0.0,
            value_of_block_commission=0.0,
            percentage_cost=0.0,
            value_of_pertrade_commission=0.0,
        )

    def get_instrument_currency(self, instrument_code):
        """
        Get the currency for a particular instrument

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: str

        """
        raise NotImplementedError(
            "Need to inherit from base class for specific data source"
        )

    def _get_fx_data(self, currency1, currency2):
        """
        Get the FX rate currency1/currency2 between two currencies
        Or return None if not available

        (Normally we'd over ride this with a specific source)


        """
        raise NotImplementedError("Need to inherit for a specific data source")

    def get_fx_for_instrument(self, instrument_code, base_currency):
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

    def get_instrument_asset_classes(self):
        """

        :return: A pd.Series, row names are instruments, content is asset class
        """
        error_msg = "You have created a simData() object; you need to use a more specific data object to use .get_instrument_asset_classes"
        self.log.critical(error_msg)

    def all_instruments_in_asset_class(self, asset_class):
        """
        Return all the instruments in a given asset class

        :param asset_class: str
        :return: list of instrument codes
        """
        asset_class_data = self.get_instrument_asset_classes()
        asset_class_instrument_list = list(
            asset_class_data[asset_class_data == asset_class].index
        )

        # Remove anything that's missing
        instrument_list = self.get_instrument_list()
        filtered_asset_class_instrument_list = [
            instrument
            for instrument in asset_class_instrument_list
            if instrument in instrument_list
        ]

        return filtered_asset_class_instrument_list

    def asset_class_for_instrument(self, instrument_code):
        """
        Which asset class is some instrument in?

        :param instrument_code:
        :return: str
        """

        asset_class_data = self.get_instrument_asset_classes()
        asset_class = asset_class_data[instrument_code]

        return asset_class


if __name__ == "__main__":
    import doctest

    doctest.testmod()
