

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
    

if __name__ == '__main__':
    import doctest
    doctest.testmod()