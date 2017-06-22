import pandas as pd
from syslogdiag.log import logtoscreen
from syscore.objects import get_methods

DEFAULT_CURRENCY = "USD"

DEFAULT_DATES = pd.date_range(
    start=pd.datetime(1970, 1, 1), freq="B", end=pd.datetime(2040, 12, 10))
DEFAULT_RATE_SERIES = pd.Series(
    [1.0] * len(DEFAULT_DATES), index=DEFAULT_DATES)


class Data(object):
    """
    Core data object - Base class

    Data objects are used to get data from a particular source, and give certain information about it

    The bare Data class isn't much good and holds only price data

    Normally we'd inherit from this for specific asset classes (eg carry data for futures), and then for a
      specific source of data (eg csv files, databases, ...)

    The inheritance is:

    Base generic class: Data
    -> asset class specific eg futuresdata.FuturesData
    -> source specific eg legacy.csvFuturesData

    """

    def __init__(self):
        """
        Data socket base class
        """
        # this will normally be overriden by the base system
        setattr(self, "log", logtoscreen(stage="data"))

    def __repr__(self):
        return "Data object with %d instruments" % len(
            self.get_instrument_list())

    def _system_init(self, base_system):
        """
        This is run when added to a base system

        :param base_system
        :return: nothing
        """

        ## inherit the log
        setattr(self, "log", base_system.log.setup(stage="data"))

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
        error_msg = "You have created a Data() object; you might need to use a more specific data object" % instrument_code
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

        >>> data=Data()
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
            value_of_pertrade_commission=0.0)

    def _get_default_currency(self):
        """
        We assume we always have rates for the default currency vs others to use in getting cross rates
        eg if default is USD assume we always know GBPUSD, AUDUSD...

        :returns: str


        """

        return DEFAULT_CURRENCY

    def _get_default_series(self):
        """
        What we return if currency rates match

        >>> data=Data()
        >>> data._get_default_series().tail(5)
        Expected:
        2014-12-26   1
        2014-12-29   1
        2014-12-30   1
        2014-12-31   1
        2015-01-01   1
        Freq: B, dtype: float64
        """

        return DEFAULT_RATE_SERIES

    def get_instrument_currency(self, instrument_code):
        """
        Get the currency for a particular instrument

        Since we don't have any actual data unless we overload this object, just return the default

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: str

        """
        return self._get_default_currency()

    def _get_fx_data(self, currency1, currency2):
        """
        Get the FX rate currency1/currency2 between two currencies
        Or return None if not available

        (Normally we'd over ride this with a specific source)

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :param base_currency: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.Series, or None if not found


        """

        if currency1 == currency2:
            return self._get_default_series()

        # no data available
        return None

    def _get_fx_cross(self, currency1, currency2):
        """
        Get the FX rate between two currencies, using crosses with DEFAULT_CURRENCY if neccessary

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :param base_currency: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.Series

        >>> data=Data()
        >>> data._get_fx_cross("USD", "USD").tail(5)
        2014-12-26   1
        2014-12-29   1
        2014-12-30   1
        2014-12-31   1
        2015-01-01   1
        Freq: B, dtype: float64
        """

        # try and get from raw data
        fx_rate_series = self._get_fx_data(currency1, currency2)

        if fx_rate_series is None:
            # missing; have to get get cross rates
            default_currency = self._get_default_currency()
            currency1_vs_default = self._get_fx_data(currency1,
                                                     default_currency)
            currency2_vs_default = self._get_fx_data(currency2,
                                                     default_currency)

            (aligned_c1, aligned_c2) = currency1_vs_default.align(
                currency2_vs_default, join="outer")

            fx_rate_series = aligned_c1.ffill() / aligned_c2.ffill()

        return fx_rate_series

    def get_fx_for_instrument(self, instrument_code, base_currency):
        """
        Get the FX rate between the FX rate for the instrument and the base (account) currency

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :param base_currency: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.Series

        >>> data=Data()
        >>> data.get_fx_for_instrument("wibble", "USD").tail(5)
        2014-12-26    1
        2014-12-29    1
        2014-12-30    1
        2014-12-31    1
        2015-01-01    1
        Freq: B, dtype: float64
        """

        instrument_currency = self.get_instrument_currency(instrument_code)
        fx_rate_series = self._get_fx_cross(instrument_currency, base_currency)

        return fx_rate_series

    def get_instrument_asset_classes(self):
        """

        :return: A pd.Series, row names are instruments, content is asset class
        """
        error_msg = "You have created a Data() object; you need to use a more specific data object to use .get_instrument_asset_classes"
        self.log.critical(error_msg)

    def all_instruments_in_asset_class(self, asset_class):
        """
        Return all the instruments in a given asset class

        :param asset_class: str
        :return: list of instrument codes
        """
        asset_class_data = self.get_instrument_asset_classes()
        instrument_list = list(asset_class_data[asset_class_data==asset_class].index)

        return instrument_list

    def asset_class_for_instrument(self, instrument_code):
        """
        Which asset class is some instrument in?

        :param instrument_code:
        :return: str
        """

        asset_class_data = self.get_instrument_asset_classes()
        asset_class = asset_class_data[instrument_code]

        return asset_class

if __name__ == '__main__':
    import doctest
    doctest.testmod()
