from sysdata.data import Data


class FuturesData(Data):
    """
        Get futures specific data
        
        Extends the Data class to add additional features for asset specific 
        
        Will normally be overriden by a method for a specific data source
        See legacy.py
    
    """
    def __init__(self, price_dict=dict(), carry_data_dict=dict()):
        """
        Create a Data object specifically for futures data
        inherits from Data

        As with pricedata in Data, we can optionally pass in carrydata dict directly (as well as the price_dict)
        
        :param price_dict: Optionally a dictionary of prices, keyword instrument names 
        :type price_dict: Dict of Tx1 pd.DataFrame (not checked here)

        :param carry_data_dict: Optionally a dictionary of futures carry data, keyword instrument names 
        :type carry_data_dict: Dict of Tx1 pd.DataFrame (not checked here)
        
        :returns: new FuturesData object
    
        >>> data=FuturesData(dict(a=[]), dict(a=[]))
        >>> data
        FuturesData object with 1 instruments
        
        """
        ## inherit from Data, which needs price_dict
        super(FuturesData, self).__init__(price_dict)

        """
        All data objects have hidden dicts where they store their data
        """
        setattr(self, "_carrydatadict", carry_data_dict)

    def __repr__(self):
        return "FuturesData object with %d instruments" % len(self.get_instrument_list())    


    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT
        
        These are specifically needed for futures trading
        
        For other asset classes we'd probably pop in eg equities fundamental data, FX interest rates...
        
        Normally we'd inherit from this method for a specific data source
        
        :param instrument_code: instrument to get carry data for 
        :type instrument_code: str
        
        :returns: pd.DataFrame
    
        >>> import pandas as pd
        >>> carry_data=pd.DataFrame(dict(PRICE=[2.0, 2.4, 2.2, 2.7], \
                                        CARRY=[2.2, 2.5, 2.3, 2.9],\
                                        PRICE_CONTRACT=['201503', '201503','201503','201503'],  \
                                        CARRY_CONTRACT=['201506', '201506','201506','201506']),  \
                                       pd.date_range(pd.datetime(2015,1,1), periods=4))
        >>> data=FuturesData(carry_data_dict=dict(a=carry_data))
        >>> data.get_instrument_raw_carry_data("a")
                    CARRY CARRY_CONTRACT  PRICE PRICE_CONTRACT
        2015-01-01    2.2         201506    2.0         201503
        2015-01-02    2.5         201506    2.4         201503
        2015-01-03    2.3         201506    2.2         201503
        2015-01-04    2.9         201506    2.7         201503        

        """
        ### Default method to get instrument price
        ### Will usually be overriden when inherited with specific data source
        if instrument_code in self._carrydatadict:
            return self._carrydatadict[instrument_code]
        else:
            raise Exception("You have created a FuturesData() object without a carrydatadict, or missing key value %s; you probably need to replace this method to do anything useful" % instrument_code)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
