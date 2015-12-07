import numpy as np

from systems.rawdata import RawData
from syscore.objects import update_recalc, calc_or_cache
from syscore.dateutils import expiry_diff
from syscore.pdutils import divide_df_single_column


class FuturesRawData(RawData):
    """
    A SubSystem that does futures specific raw data calculations

    KEY INPUT: system.data.get_instrument_raw_carry_data(instrument_code)    
              found in self.get_instrument_raw_carry_data(self, instrument_code)
    
    KEY OUTPUT: system.rawdata.daily_annualised_roll(instrument_code)

    Name: rawdata
    """


    
    def __init__(self):
        
        """
        Create a futures raw data subsystem
        
        >>> ans=FuturesRawData()
        >>> delkeys=ans._delete_on_recalc
        >>> delkeys.sort()
        >>> delkeys
        ['_annualisedrolldict', '_capped_norm_return_dict', '_daily_denominator_price_dict', '_daily_percentage_volatility', '_daily_prices_dict', '_daily_returns_dict', '_daily_vol_dict', '_dailyannualisedrolldict', '_indexed_dict', '_norm_return_dict', '_price_dict', '_raw_carry_dict', '_rawfuturesrolldict', '_rolldifferentialsdict', '_smoothedrolldict']
        """
        
        super(FuturesRawData, self).__init__()

        """
        if you add another method to this you also need to add its blank dict here
        """
        
        delete_on_recalc=["_dailyannualisedrolldict", "_annualisedrolldict","_rawfuturesrolldict", 
                             "_dailyannualisedrolldict", "_raw_carry_dict", 
                          "_rolldifferentialsdict", "_smoothedrolldict"]
        dont_delete=[]
        update_recalc(self, delete_on_recalc, dont_delete)
        
    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT
        
        :param instrument_code: instrument to get data for
        :type instrument_code: str
        
        :returns: Tx4 pd.DataFrame
       
        KEY INPUT
        
        >>> from systems.provided.example.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (rawdata, data, config)=get_test_object_futures()
        >>> system=System([rawdata], data)
        >>> system.rawdata.get_instrument_raw_carry_data("EDOLLAR").tail(2)
                    PRICE    CARRY CARRY_CONTRACT PRICE_CONTRACT
        2015-04-21  97.83  97.9050         201806         201809
        2015-04-22    NaN  97.8325         201806         201809
        """
        
        def _calc_raw_carry(system, instrument_code):
            instrcarrydata=system.data.get_instrument_raw_carry_data(instrument_code)
            return instrcarrydata

        raw_carry=calc_or_cache(self.parent, "_raw_carry_dict", instrument_code, _calc_raw_carry)
        
        return raw_carry
        

        
    
    def raw_futures_roll(self, instrument_code):
        """
        Returns the raw difference between price and carry

        :param instrument_code: instrument to get data for
        :type instrument_code: str
        
        :returns: Tx4 pd.DataFrame

        >>> from systems.provided.example.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (rawdata, data, config)=get_test_object_futures()
        >>> system=System([rawdata], data)
        >>> system.rawdata.raw_futures_roll("EDOLLAR").tail(2)
                    raw_roll
        2015-04-21    -0.075
        2015-04-22       NaN
        """

        
        def _calc_raw_futures_roll(system, instrument_code, this_subsystem):
                        
            carrydata=this_subsystem.get_instrument_raw_carry_data(instrument_code)
            raw_roll=carrydata.PRICE - carrydata.CARRY
            
            raw_roll[raw_roll==0]=np.nan

            raw_roll=raw_roll.to_frame('raw_roll')
            return raw_roll

        raw_roll=calc_or_cache(self.parent, "_rawfuturesrolldict", instrument_code, _calc_raw_futures_roll, self)
        
        return raw_roll

 
    def roll_differentials(self, instrument_code):
        """
        Work out the annualisation factor 

        :param instrument_code: instrument to get data for
        :type instrument_code: str
        
        :returns: Tx4 pd.DataFrame

        >>> from systems.provided.example.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (rawdata, data, config)=get_test_object_futures()
        >>> system=System([rawdata], data)
        >>> system.rawdata.roll_differentials("EDOLLAR").tail(2)
                    roll_diff
        2015-04-21  -0.251882
        2015-04-22  -0.251882
        """
        def _calc_roll_differentials(system, instrument_code, this_subsystem):
            carrydata=this_subsystem.get_instrument_raw_carry_data(instrument_code)
            roll_diff=carrydata.apply(expiry_diff, 1)

            roll_diff=roll_diff.to_frame('roll_diff')
            
            return roll_diff
    
        roll_diff=calc_or_cache(self.parent, "_rolldifferentialsdict", instrument_code, _calc_roll_differentials, self)
        
        return roll_diff

    
    def annualised_roll(self, instrument_code):
        """
        Work out annualised futures roll
        
        :param instrument_code: instrument to get data for
        :type instrument_code: str
        
        :returns: Tx4 pd.DataFrame

        >>> from systems.provided.example.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (rawdata, data, config)=get_test_object_futures()
        >>> system=System([rawdata], data)
        >>> system.rawdata.annualised_roll("EDOLLAR").tail(2)
                    annualised_roll
        2015-04-21         0.297758
        2015-04-22              NaN

        """
        
        def _calc_annualised_roll(system, instrument_code, this_subsystem):
            rolldiffs=this_subsystem.roll_differentials(instrument_code)
            rawrollvalues=this_subsystem.raw_futures_roll(instrument_code)

            annroll=divide_df_single_column(rawrollvalues, rolldiffs)
            annroll.columns=['annualised_roll']

            return annroll

        annroll=calc_or_cache(self.parent, "_annualisedrolldict", instrument_code, _calc_annualised_roll, self)

        return annroll
    
    
    def daily_annualised_roll(self, instrument_code):
        """
        Resample annualised roll to daily frequency
        
        We don't resample earlier, or we'll get bad data
        
        :param instrument_code: instrument to get data for
        :type instrument_code: str
        
        :returns: Tx4 pd.DataFrame

        KEY OUTPUT
        
        >>> from systems.provided.example.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (rawdata, data, config)=get_test_object_futures()
        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_annualised_roll("EDOLLAR").tail(2)
                    annualised_roll_daily
        2015-04-21               0.297758
        2015-04-22                    NaN
        """
        
        def _calc_daily_ann_roll(system, instrument_code, this_subsystem):
        
            annroll=this_subsystem.annualised_roll(instrument_code)
            annroll=annroll.resample("1B", how="mean")
            annroll.columns=['annualised_roll_daily']
            return annroll
        
        
        ann_daily_roll=calc_or_cache(self.parent, "_dailyannualisedrolldict", instrument_code, _calc_daily_ann_roll, self)
        
        return ann_daily_roll
    
    
    def daily_denominator_price(self, instrument_code):
        """
        Gets daily prices for use with % volatility
        This won't always be the same as the normal 'price'

        :param instrument_code: Instrument to get prices for 
        :type trading_rules: str
        
        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.provided.example.testdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (rawdata, data, config)=get_test_object_futures()
        >>> system=System([rawdata], data)
        >>>
        >>> system.rawdata.daily_denominator_price("EDOLLAR").tail(2)
                    price
        2015-04-21  97.83
        2015-04-22  NaN

        """
        def _daily_denominator_prices(system, instrument_code, this_subsystem):
            prices=this_subsystem.get_instrument_raw_carry_data( instrument_code).PRICE.to_frame()
            daily_prices=prices.resample("1B", how="last")
            daily_prices.columns=['price']
            return daily_prices
        
        daily_dem_prices=calc_or_cache(self.parent, "_daily_denominator_price_dict", instrument_code, _daily_denominator_prices, self)
        
        return daily_dem_prices
        

    

if __name__ == '__main__':
    import doctest
    doctest.testmod()