import pandas as pd




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
    
    
    def __init__(self, price_dict=dict()):
        
        """
        Config objects control the behaviour of systems 
        
        :param price_dict: Optionally a dictionary of prices, keyword instrument names 
        :type price_dict: Dict of Tx1 pd.DataFrame (not checked here)
        
        :returns: new Data object
    
        >>> data=Data(dict(a=[]))
        >>> data
        Data object with 1 instruments

        """
        setattr(self, "_pricedict", price_dict)

    def __repr__(self):
        return "Data object with %d instruments" % len(self.get_instrument_list())    


    def get_instrument_price(self, instrument_code):
        """
        Default method to get instrument price
        Will usually be overriden when inherited with specific data source
        
        :param instrument_code: instrument to get prices for 
        :type instrument_code: str
        
        :returns: pd.DataFrame
    
        >>> import pandas as pd
        >>> price=pd.DataFrame(dict(price=[2.0, 2.4, 2.2, 2.7]), pd.date_range(pd.datetime(2015,1,1), periods=4))
        >>> data=Data(dict(a=price))
        >>> data.get_instrument_price("a")
                    price
        2015-01-01    2.0
        2015-01-02    2.4
        2015-01-03    2.2
        2015-01-04    2.7
        
        """
        if instrument_code in self._pricedict:
            return self._pricedict[instrument_code]
        else:
            raise Exception("You have created a Data() object missing key value %s; you might need to use a more specific data object" % instrument_code)

        
    def __getitem__(self, keyname):
        """
         convenience method to get the price, make it look like a dict
        
        :param keyname: instrument to get prices for 
        :type keyname: str
        
        :returns: pd.DataFrame 
    
        >>> import pandas as pd
        >>> price=pd.DataFrame(dict(price=[2.0, 2.4, 2.2, 2.7]), pd.date_range(pd.datetime(2015,1,1), periods=4))
        >>> data=Data(dict(a=price))
        >>> data["a"]
                    price
        2015-01-01    2.0
        2015-01-02    2.4
        2015-01-03    2.2
        2015-01-04    2.7
        """
        price=self.get_instrument_price(keyname)
        
        return price


    def get_instrument_list(self):
        """
        list of instruments in this data set
        
        :returns: list of str
    
        >>> data=Data(dict(a=[]))
        >>> data.get_instrument_list()
        ['a']
        """
        # trivial if a dictionary
        return list(self._pricedict.keys())

    def keys(self):
        """
        list of instruments in this data set
        
        :returns: list of str
    
        >>> data=Data(dict(a=[]))
        >>> data.keys()
        ['a']
        """
        return self.get_instrument_list()
    
    def get_value_of_block_price_move(self, instrument_code):
        """
        How much does a $1 (or whatever) move in the price of an instrument block affect it's value?
        eg 100.0 for 100 shares
        
        :param instrument_code: instrument to value for 
        :type instrument_code: str
        
        :returns: float 
    
        """
        
        return 1.0

    def get_default_currency(self):
        """
        We assume we always have rates for the default currency vs others to use in getting cross rates
        eg if default is USD assume we always know GBPUSD, AUDUSD... 
        
        :returns: str
        
        """
        DEFAULT_CURRENCY="USD"
        
        return DEFAULT_CURRENCY

    def get_default_series(self):
        """
        What we return if currency rates match
        """
        DEFAULT_DATES=pd.date_range(start=pd.datetime(1970,1,1),end=pd.datetime(2050,1,1)) 
        DEFAULT_RATE_SERIES=pd.DataFrame(dict(fx=[1.0]*len(DEFAULT_DATES)), index=DEFAULT_DATES)

        return DEFAULT_RATE_SERIES

    def get_instrument_currency(self, instrument_code):
        """
        Get the currency for a particular instrument

        Since we don't have any actual data unless we overload this object, just return the default

        :param instrument_code: instrument to value for 
        :type instrument_code: str

        :returns: str
        
        """
        return self.get_default_currency()


    def get_fx_data(self, currency1, currency2):
        """
        Get the FX rate currency1/currency2 between two currencies
        Or return None if not available
        
        (Normally we'd over ride this with a specific source)

        :param instrument_code: instrument to value for 
        :type instrument_code: str

        :param base_currency: instrument to value for 
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame, or None if not found
        
        
        """

        if currency1==currency2:
            return self.get_default_series()

        ## no data available
        return None

    def get_fx_cross(self, currency1, currency2):
        """
        Get the FX rate between two currencies, using crosses with DEFAULT_CURRENCY if neccessary

        :param instrument_code: instrument to value for 
        :type instrument_code: str

        :param base_currency: instrument to value for 
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame
        
        
        """
        
        ### try and get from raw data
        fx_rate_series=self.get_fx_data(currency1, currency2)
        
        if fx_rate_series is None:
            ## missing; have to get get cross rates
            default_currency=self.get_default_currency()
            currency1_vs_default=self.get_fx_data(currency1, default_currency).resample("1B", how="last")
            currency2_vs_default=self.get_fx_data(currency2, default_currency).resample("1B", how="last")
            
            together=pd.concat([currency1_vs_default, currency2_vs_default], axis=1, join='inner').ffill()
            
            fx_rate_series=together.iloc[:,0]/together.iloc[:, 1]
            fx_rate_series=fx_rate_series.to_frame("fx")
        
        return fx_rate_series

    def get_fx_for_currency(self, instrument_code, base_currency):
        """
        Get the FX rate between the FX rate for the instrument and the base (account) currency

        :param instrument_code: instrument to value for 
        :type instrument_code: str

        :param base_currency: instrument to value for 
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame
        
        >>> data=Data()
        >>> data.get_fx_for_currency("wibble", "USD").tail(2)
                    fx
        2049-12-31   1
        2050-01-01   1
        """

        instrument_currency=self.get_instrument_currency(instrument_code)
        fx_rate_series=self.get_fx_cross(instrument_currency, base_currency)
        
        return fx_rate_series


if __name__ == '__main__':
    import doctest
    doctest.testmod()