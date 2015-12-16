import pandas as pd

from syscore.accounting import accountCurve, pandl
from systems.stage import SystemStage
from systems.basesystem import ALL_KEYNAME
from syscore.pdutils import multiply_df_single_column,  fix_weights_vs_pdm

class Account(SystemStage):
    """
    SystemStage for accounting
    
    KEY INPUT: 
                found in self.get_forecast(instrument_code, rule_variation)

                found in self.get_forecast_weights_and_fdm(instrument_code)

                system.positionSize.get_subsystem_position(instrument_code)
                found in self.get_subsystem_position(instrument_code)
                
                found in self.get_portfolio_position()
                
                found in self.get_instrument_weights_and_idm(instrument_code)

                found in self.get_capital()

                
    KEY OUTPUT: self.forecasts()
                (will be used to optimise forecast weights in future version)
                
                self.instruments()
                (will be used to optimise instrument weights in future version)
                

    Name: accounts
    """
    
    def __init__(self):
        """
        Create a SystemStage for accounting
        
        
                
        """
        delete_on_recalc=[]

        dont_delete=[]
        
        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_delete)

        setattr(self, "name", "accounts")

        
    def get_subsystem_position(self, instrument_code):
        """
        Get the position assuming all capital in one instruments, from a previous module
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 
        
        KEY INPUT
        
        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> 
        >>> ## from config
        >>> system.portfolio.get_subsystem_position("EDOLLAR").tail(2)
                    ss_position
        2015-04-21   798.963739
        2015-04-22   687.522788

        """

        return self.parent.positionSize.get_subsystem_position(instrument_code)
    
        def portfolio(self):
            pass
        
        def instrument(self, subset=None, percentage=True, isolated=False, sumup=False):
            pass
        
        def rules(self, subset=None, percentage=True, isolated=False, sumup=False):
            pass

        def rulegroup(self, subset=None, percentage=True, isolated=False, sumup=False):
            pass
        
        def rulestyle(self, subset=None, percentage=True, isolated=False, sumup=False):
            pass

        ## these should be in a futures accounting object...
        def assetclass(self, subset=None, percentage=True, isolated=False, sumup=False):
            pass
        
        def country(self, subset=None, percentage=True, isolated=False, sumup=False):
            pass
        
        

if __name__ == '__main__':
    import doctest
    doctest.testmod()
