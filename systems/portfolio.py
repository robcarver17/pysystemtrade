import pandas as pd
import numpy as np

from systems.subsystem import SubSystem
from systems.defaults import system_defaults
from syscore.objects import calc_or_cache, ALL_KEYNAME
from syscore.pdutils import multiply_df_single_column, divide_df_single_column, fix_weights_vs_pdm
from syscore.dateutils import ROOT_BDAYS_INYEAR

class PortfoliosFixed(SubSystem):
    """
    Subsystem for portfolios 
    
    Gets the position, accounts for instrument weights and diversification multiplier
    
    This version involves fixed weights and multipliers.
    
    Note: At this stage we're dealing with a notional, fixed, amount of capital.
         We'll need to work out p&l to scale positions properly
    
    KEY INPUT: system.positionSize.get_subsystem_position(instrument_code)
                found in self.get_subsystem_position(instrument_code)
                
    KEY OUTPUT: system.portfolio.get_notional_position(instrument_code) 

    Name: portfolio
    """
    
    def __init__(self, instrument_weights=None, instrument_div_multiplier=None):
        """
        Create a SubSystem for creating portfolios
        
        If parameters are not passed will look in system.config
          
        :param instrument_weights: Instrument weights
        :type instrument_weights:    None       (weights will be inherited from system.config)
                                    dict of floats

        :param instrument_div_multiplier: Multiplier to apply
        :type instrument_div_multiplier: None (i.d.m. will be inherited from system.config)
                                       float 
                
        
                
        """
        delete_on_recalc=["_instrument_weights", "_instrument_div_multiplier", "_raw_instrument_weights", "_notional_position"]

        dont_delete=[]
        
        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_delete)

        setattr(self, "name", "portfolio")

        setattr(self, "_passed_instrument_weights", instrument_weights)
        setattr(self, "_passed_instrument_div_multiplier", instrument_div_multiplier)
        
    def get_subsys_position(self, instrument_code):
        """
        Get the position assuming all capital in one position, from a previous module
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 
        
        KEY INPUT
        
        >>> from systems.provided.example.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> 
        >>> ## from config
        >>> system.portfolio.get_subsys_position("EDOLLAR").tail(2)
                    ss_position
        2015-04-21   798.963739
        2015-04-22   687.522788

        """

        return self.parent.positionSize.get_subsys_position(instrument_code)
    

    def get_raw_instrument_weights(self):
        """
        Get the instrument weights
        
        These are 'raw' because we need to account for potentially missing positions, and weights that don't add up.
        
        From: (a) passed into subsystem when created
              (b) ... if not found then: in system.config.instrument_weights
        
        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions 

        >>> from systems.provided.example.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> 
        >>> ## from config
        >>> system.portfolio.get_instrument_weights().tail(2)
                    EDOLLAR  US10
        2015-04-21      0.5   0.5
        2015-04-22      0.5   0.5
        >>>
        >>> ## pass in to object instead
        >>> ird=dict(EDOLLAR=0.1, US10=0.9)
        >>> system2=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed(instrument_weights=ird)], data, config)
        >>> system2.portfolio.get_instrument_weights().tail(2)
                    EDOLLAR  US10
        2015-04-21      0.1   0.9
        2015-04-22      0.1   0.9

        """                    
        def _get_instrument_weights(system,  an_ignored_variable,  this_subsystem ):

            if this_subsystem._passed_instrument_weights is not None:
                instrument_weights=this_subsystem._passed_instrument_weights
            else:
                try:
                    instrument_weights=system.config.instrument_weights
                except:
                    raise Exception("Instrument weights must be passed to PortfoliosFixed(...) or in system.config")
            
            ## Now we have a dict, fixed_weights.
            ## Need to turn into a timeseries covering the range of forecast dates
            instrument_list=list(instrument_weights.keys())
            instrument_list.sort()
            
            subsys_ts=[
                            this_subsystem.get_subsys_position(instrument_code).index 
                         for instrument_code in instrument_list]
            
            earliest_date=min([min(fts) for fts in subsys_ts])
            latest_date=max([max(fts) for fts in subsys_ts])

            ## this will be daily, but will be resampled later
            weight_ts=pd.date_range(start=earliest_date, end=latest_date)
            
            instrument_weights_weights=dict([
                            (instrument_code, pd.Series([instrument_weights[instrument_code]]*len(weight_ts), index=weight_ts)) 
                         for instrument_code in instrument_list])
            
            instrument_weights_weights=pd.concat(instrument_weights_weights, axis=1)
            instrument_weights_weights.columns=instrument_list

            return instrument_weights_weights
        
        instrument_weights=calc_or_cache(self.parent, "_raw_instrument_weights", ALL_KEYNAME,  _get_instrument_weights, self)
        return instrument_weights



    def get_instrument_weights(self):
        """
        Get the time series of instrument weights, accounting for potentially missing positions, and weights that don't add up.
        
        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions 


        """                    
        def _get_clean_instrument_weights(system,  an_ignored_variable,  this_subsystem ):

            raw_instr_weights=this_subsystem.get_raw_instrument_weights()
            instrument_list=list(raw_instr_weights.columns)
            
            subsys_positions=[this_subsystem.get_subsys_position(instrument_code) 
                         for instrument_code in instrument_list]
            
            subsys_positions=pd.concat(subsys_positions, axis=1).ffill()
            subsys_positions.columns=instrument_list
            
            instrument_weights=fix_weights_vs_pdm(raw_instr_weights, subsys_positions)

            return instrument_weights
        
        instrument_weights=calc_or_cache(self.parent, "_instrument_weights", ALL_KEYNAME,  _get_clean_instrument_weights, self)
        return instrument_weights

    
    def get_instrument_diversification_multiplier(self):
        """
        Get the instrument diversification multiplier
        
        From: (a) passed into subsystem when created
              (b) ... if not found then: in system.config.instrument_weights
        
        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions 

        >>> from systems.provided.example.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> 
        >>> ## from config
        >>> system.portfolio.get_instrument_diversification_multiplier().tail(2)
                    idm
        2015-04-21  1.2
        2015-04-22  1.2
        >>>
        >>> ## pass in to object instead
        >>> idm=2.0
        >>> system2=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed(instrument_div_multiplier=idm)], data, config)
        >>> system2.portfolio.get_instrument_diversification_multiplier().tail(2)
                    idm
        2015-04-21    2
        2015-04-22    2

        """                    
        def _get_instrument_div_multiplier(system,  an_ignored_variable,  this_subsystem ):

            if this_subsystem._passed_instrument_div_multiplier is not None:
                div_mult=this_subsystem._passed_instrument_div_multiplier
            else:
                try:
                    div_mult=system.config.instrument_div_multiplier
                except:
                    raise Exception("Instrument div. multiplier must be passed to PortfoliosFixed(...) or in system.config")
            
            ## Now we have a fixed weight
            ## Need to turn into a timeseries covering the range of forecast dates

            ## this will be daily, but will be resampled later
            weight_ts=this_subsystem.get_instrument_weights().index
            
            ts_idm=pd.Series([div_mult]*len(weight_ts), index=weight_ts).to_frame("idm")

            return ts_idm
        
        instrument_div_multiplier=calc_or_cache(self.parent, "_instrument_div_multiplier", ALL_KEYNAME,  _get_instrument_div_multiplier, self)
        return instrument_div_multiplier



    def get_notional_position(self, instrument_code):
        """
        Gets the position, accounts for instrument weights and diversification multiplier
        
        Note: At this stage we're dealing with a notional, fixed, amount of capital.
             We'll need to work out p&l to scale positions properly
            
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 
        
        KEY OUTPUT
        >>> from systems.provided.example.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> 
        >>> ## from config
        >>> system.portfolio.get_notional_position("EDOLLAR").tail(2)
                           pos
        2015-04-21  479.378243
        2015-04-22  412.513673
        >>>

        """                    
        def _get_notional_position(system,  instrument_code,  this_subsystem ):
            idm=this_subsystem.get_instrument_diversification_multiplier()
            instr_weights=this_subsystem.get_instrument_weights()
            subsys_position=this_subsystem.get_subsys_position(instrument_code)
            
            inst_weight_this_code=instr_weights[instrument_code].to_frame("weight")
            
            inst_weight_this_code=inst_weight_this_code.reindex(subsys_position.index).ffill()
            idm=idm.reindex(subsys_position.index).ffill()
            
            multiplier=multiply_df_single_column(inst_weight_this_code, idm)
            notional_position=multiply_df_single_column(subsys_position, multiplier)
            notional_position.columns=['pos']

            return notional_position
        
        notional_position=calc_or_cache(self.parent, "_notional_position", instrument_code,  _get_notional_position, self)
        return notional_position

        


if __name__ == '__main__':
    import doctest
    doctest.testmod()
