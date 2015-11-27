import numpy as np

from systems.rawdata import subSystemRawData
from syscore.objects import update_recalc, calc_or_cache
from syscore.dateutils import expiry_diff


class FuturesRawData(subSystemRawData):
    
    def __init__(self):
        """
        A SubSystem that does futures specific raw data calculations
        (although a lot is probably common)
        
        """
        """
        if you add another method to this you also need to add its blank dict here
        """
        
        super(FuturesRawData, self).__init__()

        update_recalc(self, ["_dailyannualisedrolldict", "_annualisedrolldict","_rawfuturesrolldict", 
                             "_dailyannualisedrolldict", "_raw_carry_dict", 
                          "_rolldifferentialsdict", "_smoothedrolldict"], 
                      [])
        
    def get_instrument_raw_carrydata(self, instrument_code):
        """
        Returns the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT
        """
        
        def _calc_raw_carry(system, instrument_code):
            instrcarrydata=system.data.get_instrument_rawcarrydata(instrument_code)
            return instrcarrydata

        return calc_or_cache(self.parent, "_raw_carry_dict", instrument_code, _calc_raw_carry)
        

        
    
    def raw_futures_roll(self, instrument_code):
        """
        Returns the raw difference between price and carry
        """
        
        def _calc_raw_futures_roll(system, instrument_code):
                        
            carrydata=system.rawdata.get_instrument_raw_carrydata(instrument_code)
            raw_roll=carrydata.PRICE - carrydata.CARRY
            raw_roll[raw_roll==0]=np.nan
        
            return raw_roll

        return calc_or_cache(self.parent, "_rawfuturesrolldict", instrument_code, _calc_raw_futures_roll)

 
    def roll_differentials(self, instrument_code):
        """
        Work out the annualisation factor
        """
        def _calc_roll_differentials(system, instrument_code):
            carrydata=system.rawdata.get_instrument_raw_carrydata(instrument_code)
            ans=carrydata.apply(expiry_diff, 1)
            
            return ans
    
        return calc_or_cache(self.parent, "_rolldifferentialsdict", instrument_code, _calc_roll_differentials)


    
    def annualised_roll(self, instrument_code):
        """
        Work out annualised futures roll
        """
        
        def _calc_annualised_roll(system, instrument_code):
            rolldiffs=system.rawdata.roll_differentials(instrument_code)
            rawrollvalues=system.rawdata.raw_futures_roll(instrument_code)
            
            return rawrollvalues/rolldiffs

        return calc_or_cache(self.parent, "_annualisedrolldict", instrument_code, _calc_annualised_roll)

    
    
    def daily_annualised_roll(self, instrument_code):
        """
        Resample annualised roll
        
        We don't resample earlier, or we'll get bad data
        """
        
        def _calc_daily_ann_roll(system, instrument_code):
        
            annroll=system.rawdata.annualised_roll(instrument_code)
            annroll=annroll.resample("1B", how="mean")
            
            return annroll
        
        
        return calc_or_cache(self.parent, "_dailyannualisedrolldict", instrument_code, _calc_daily_ann_roll)

