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

LEGACY_DATA_MODULE="sysdata"
LEGACY_DATA_DIR="legacytemp"

class csvFuturesData(FuturesData):
    
    def __init__(self, datapath=None, pricedict=dict(), carrydatadict=dict()):

        if datapath is None:            
            datapath=get_pathname_for_package(LEGACY_DATA_MODULE, LEGACY_DATA_DIR)

        super(csvFuturesData, self).__init__(pricedict=pricedict, carrydatadict=carrydatadict)

        setattr(self, "_datapath", datapath)
    
    
    def get_instrument_price(self, instrument_code):
        if instrument_code in self._pricedict.keys():
            return self._pricedict[instrument_code]
        
        filename=os.path.join(self._datapath, instrument_code+"_price.csv")
        instrpricedata=pd_readcsv(filename)
        
        return instrpricedata
    
    def get_instrument_rawcarrydata(self, instrument_code):
        if instrument_code in self._carrydatadict.keys():
            return self._carrydatadict[instrument_code]

        filename=os.path.join(self._datapath, instrument_code+"_carrydata.csv")
        instrcarrydata=pd_readcsv(filename)
        instrcarrydata.columns=["PRICE", "CARRY", "CARRY_CONTRACT", "PRICE_CONTRACT"]

        instrcarrydata.CARRY_CONTRACT=instrcarrydata.CARRY_CONTRACT.apply(str_of_int)
        instrcarrydata.PRICE_CONTRACT=instrcarrydata.PRICE_CONTRACT.apply(str_of_int)
        
        return instrcarrydata

    def get_instrument_list(self):
        config=self.get_instrument_config()
        
        return list(config.Instrument)


    def _get_instrument_config(self):
        
        if not hasattr(self, "_instrconfig"):
            filename=os.path.join(self._datapath, "instrumentconfig.csv")
            instr_list=pd.read_csv(filename)
            setattr(self, "_instrconfig", instr_list)
            
        return self._instrconfig

    def get_instrument_asset_classes(self):
        """
        Returns dataframe with index of instruments, column AssetClass
        """ 
        if not hasattr(self, "_instrassetclasses"):
            config=self.get_instrument_config()
            instr_assets=config.AssetClass
            instr_assets.index=config.Instrument
            setattr(self, "_instrassetclasses", instr_assets)
            
        return self._instrassetclasses
        

        
    