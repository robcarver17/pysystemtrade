from sysdata.data import Data


class FuturesData(Data):
    """
    Get futures specific data
    
    Will normally be overriden by a method for a specific data source
    See legacy.py
    
    """
    def __init__(self, pricedict=dict(), carrydatadict=dict()):
        """
        inherits from Data

        As with pricedata in Data, we can optionally pass in carrydata dict directly
        
        """
        super(FuturesData, self).__init__(pricedict)

        setattr(self, "_carrydatadict", carrydatadict)

    def __repr__(self):
        return "FuturesData object with %d instruments" % len(self.get_instrument_list())    


    def get_instrument_rawcarrydata(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT
        
        These are specifically needed for futures trading
        
        For other asset classes we'd probably pop in eg equities fundamental data, FX interest rates...
        
        Normally we'd inherit from this method for a specific data source
        """
        ### Default method to get instrument price
        ### Will usually be overriden when inherited with specific data source
        if instrument_code in self._carrydatadict:
            return self._carrydatadict[instrument_code]
        else:
            raise Exception("You have created a FuturesData() object without a carrydatadict, or missing key value %s; you probably need to replace this method to do anything useful" % instrument_code)


