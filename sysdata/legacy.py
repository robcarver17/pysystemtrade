"""
Get legacy data from .csv files

Used for quick examples / 'scaffolding'
"""

import os

import pandas as pd

from syscore.fileutils import get_pathname_for_package
from syscore.pdutils import pd_readcsv
from syscore.genutils import str_of_int

from sysdata.futuresdata import FuturesData

"""
Static variables to store location of data
"""
LEGACY_DATA_MODULE="sysdata"
LEGACY_DATA_DIR="legacycsv"

class csvFuturesData(FuturesData):
    """
        Get futures specific data from legacy csv files
        
        Extends the FuturesData class for a specific data source 
    
    """
    
    def __init__(self, datapath=None, price_dict=dict(), carry_data_dict=dict()):
        """
        Create a FuturesData object for reading .csv files from datapath
        inherits from FuturesData

        We look for data in price_dict and carry_dict; then if not found we read from .csv files
        Once read data is cached in the object

        :param datapath: path to find .csv files (defaults to LEGACY_DATA_MODULE/LEGACY_DATA_DIR 
        :type datapath: None or str
        
        :param price_dict: Optionally a dictionary of prices, keyword instrument names 
        :type price_dict: Dict of Tx1 pd.DataFrame (not checked here)

        :param carry_data_dict: Optionally a dictionary of futures carry data, keyword instrument names 
        :type carry_data_dict: Dict of Tx1 pd.DataFrame (not checked here)
        
        :returns: new csvFuturesData object
    
        >>> data=csvFuturesData()
        >>> data
        FuturesData object with 38 instruments
        
        """

        if datapath is None:            
            datapath=get_pathname_for_package(LEGACY_DATA_MODULE, [LEGACY_DATA_DIR])

        super(csvFuturesData, self).__init__(price_dict=price_dict, carry_data_dict=carry_data_dict)

        """
        Most Data objects that read data from a specific place have a 'source' of some kind
        """
        setattr(self, "_datapath", datapath)
    
    
    def get_instrument_price(self, instrument_code):
        """
        Get instrument price
        If already in object dict, return that, otherwise get from .csv files
        
        :param instrument_code: instrument to get prices for 
        :type instrument_code: str
        
        :returns: pd.DataFrame

        >>> data=csvFuturesData(datapath="tests/")
        >>> data.get_instrument_price("EDOLLAR").tail(2)
                        ADJ
        2015-04-21  97.9050
        2015-04-22  97.8325
        >>> data["US10"].tail(2)
                           ADJ
        2015-04-21  129.390625
        2015-04-22  128.867188        
        """
        
        if instrument_code in self._pricedict.keys():
            return self._pricedict[instrument_code]
        
        ## Read from .csv
        filename=os.path.join(self._datapath, instrument_code+"_price.csv")
        instrpricedata=pd_readcsv(filename)
        
        return instrpricedata
    
    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT
        
        These are specifically needed for futures trading
        
        If not found in 
        
        :param instrument_code: instrument to get carry data for 
        :type instrument_code: str
        
        :returns: pd.DataFrame
    
        >>> data=csvFuturesData(datapath="tests/")
        >>> data.get_instrument_raw_carry_data("EDOLLAR").tail(5)
                     PRICE    CARRY CARRY_CONTRACT PRICE_CONTRACT
        2015-04-16  97.860  97.9350         201806         201809
        2015-04-17  97.865  97.9400         201806         201809
        2015-04-20  97.850  97.9250         201806         201809
        2015-04-21  97.830  97.9050         201806         201809
        2015-04-22     NaN  97.8325         201806         201809
        """
        if instrument_code in self._carrydatadict.keys():
            return self._carrydatadict[instrument_code]

        filename=os.path.join(self._datapath, instrument_code+"_carrydata.csv")
        instrcarrydata=pd_readcsv(filename)
        instrcarrydata.columns=["PRICE", "CARRY", "CARRY_CONTRACT", "PRICE_CONTRACT"]

        instrcarrydata.CARRY_CONTRACT=instrcarrydata.CARRY_CONTRACT.apply(str_of_int)
        instrcarrydata.PRICE_CONTRACT=instrcarrydata.PRICE_CONTRACT.apply(str_of_int)
        
        return instrcarrydata

    def _get_instrument_data(self):
        """
        Get a data frame of interesting information about instruments, eithier from a file or cached
                
        :returns: pd.DataFrame

        >>> data=csvFuturesData(datapath="tests/")
        >>> data._get_instrument_data()
                   Instrument  Pointsize AssetClass
        Instrument                                 
        EDOLLAR       EDOLLAR       2500       STIR
        US10             US10       1000       Bond

        """
        
        if not hasattr(self, "_instr_data"):
            filename=os.path.join(self._datapath, "instrumentconfig.csv")
            instr_data=pd.read_csv(filename)
            instr_data.index=instr_data.Instrument

            setattr(self, "_instr_data", instr_data)

        return self._instr_data

    def get_instrument_list(self):
        """
        list of instruments in this data set
        
        :returns: list of str

        >>> data=csvFuturesData(datapath="tests/")
        >>> data.get_instrument_list()
        ['EDOLLAR', 'US10']
        >>> data.keys()
        ['EDOLLAR', 'US10']
        """

        instr_data=self._get_instrument_data()
        
        return list(instr_data.Instrument)

            

    def get_instrument_asset_classes(self):
        """
        Returns dataframe with index of instruments, column AssetClass

        >>> data=csvFuturesData(datapath="tests/")
        >>> data.get_instrument_asset_classes()
        Instrument
        EDOLLAR    STIR
        US10       Bond
        Name: AssetClass, dtype: object
        """ 
        instr_data=self._get_instrument_data()
        instr_assets=instr_data.AssetClass
            
        return instr_assets
        

        
if __name__ == '__main__':
    import doctest
    doctest.testmod()
