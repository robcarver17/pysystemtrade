"""
Core data object - Base class

Data objects are used to get data from a particular source, and give certain information about it

This bare Data class isn't much good and holds only price data

Normally we'd extend this for specific asset classes (eg carry data for futures), and then for a 
  specific source of data (eg csv files, databases, ...)

The inheritance is:

Base generic class: Data
-> asset class specific eg futuresdata.FuturesData
-> source specific eg legacy.csvFuturesData

"""


class Data(object):
    """
    
    data=Data(dict(a=pd.DataFrame(...), b=pd.DataFrame(...))
    print(data.get_instrument_list())
    print(data.
    
    """
    
    
    
    def __init__(self, pricedict=dict()):
        
        """
        normally we'd override this method
        however by default we can pass in a dictionary of pandas Tx1 data frames containing prices
        """
        setattr(self, "_pricedict", pricedict)

    def __repr__(self):
        return "Data object with %d instruments" % len(self.get_instrument_list())    


    def get_instrument_price(self, instrument_code):
        """
        Default method to get instrument price
        Will usually be overriden when inherited with specific data source
        """
        if instrument_code in self._pricedict:
            return self._pricedict[instrument_code]
        else:
            raise Exception("You have created a Data() object missing key value %s; you might need to use a more specific data object" % instrument_code)


    def get_instrument_list(self):
        """
        list of instruments in this data set
        
        """
        # trivial if a dictionary
        return self._pricedict.keys()
        
    def __getitem__(self, keyname):
        ## convenience method to get the price, make it look like a dict
        return self.get_instrument_price(keyname)

    def keys(self):
        ## again to make it look a bit like a dict
        return self.get_instrument_list()