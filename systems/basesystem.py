from sysdata.configdata import Config

class System(object):
    '''
    system objects are used for signal processing in a 'tree' like framework
    
    This is the base class which all systems inherit
    
    Systems are:
    
        made up of stages
    
       take a data and a config object
       
          
    '''


    def __init__(self,  sub_system_list, data, config=None):
        """
        Create a system object for doing simulations or live trading

        :param data: data for doing simulations 
        :type data: sysdata.data.Data (or anything that inherits from that)
        
        :param config: Optional configuration 
        :type config: sysdata.configdata.Config 

        :param sub_system_list: A list of sub-subsystems 
        :type sub_system_list: list of systems.subsystem.SubSystem (or anything that inherits from it)
        
        :returns: new system object
    
        >>> from subsystem import SubSystem
        >>> subsystem=SubSystem()
        >>> from sysdata.csvdata import csvFuturesData
        >>> data=csvFuturesData()
        >>> System([subsystem], data)
        System with subsystems: default
        
        """
        
        if config is None:
            ## Default - for very dull systems this is sufficient
            config=Config()
            
        setattr(self, "data", data)
        setattr(self, "config", config)

        """
        
        """
        delete_on_recalc=[]
        dont_recalc=[]
        subsystem_names=[]
        
        assert type(sub_system_list) is list
        
        for subsystem in sub_system_list:
            
            """
            This is where we put the methods to store various stages of the process
            
            """

            ## Each subsystem has a link back to the parent system
            setattr(subsystem, "parent", self)
            
            ## Subsystems have names, which are also how we find them in the system attributes
            sub_name=subsystem.name
            
            if sub_name in subsystem_names:
                raise Exception("You have duplicate subsystems with the name %s. Remove one of them, or change a name." % sub_name) 

            setattr(self, sub_name, subsystem)

            subsystem_names.append(sub_name)
            
            subsystem_delete_on_recalc=getattr(subsystem, "_delete_on_recalc",[])
            subsystem_dont_recalc=getattr(subsystem, "_dont_recalc",[])
            
            delete_on_recalc=delete_on_recalc+subsystem_delete_on_recalc
            dont_recalc=dont_recalc+subsystem_dont_recalc
            
        setattr(self, "_subsystem_names", subsystem_names)
        
        """
        These are the places where we hide all intermediate results
        
        We call optimal_positions and then that propogates back finding all the data we need
        
        The results are then cached in the object. Should we call delete_instrument_data (in base class system) then 
            everything related to a particular instrument is removed from these 'nodes'
        This is very useful in live trading when we don't want to update eg cross sectional data every
            sample
        """


        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_recalc)
        
        allitems=delete_on_recalc+dont_recalc
        
        ## Set up the empty dictionaries for storage
        for dictname in allitems:
            empty_dict=dict()
            setattr(self, dictname, empty_dict)
        
    def __repr__(self):
        sslist=", ".join(self._subsystem_names)
        return "System with subsystems: "+sslist
        
    def delete_instrument_data_from_cache(self, instrument_code, delete_all=False):
        """
        Delete everything in the system relating to an instrument_code

        :param instrument_code: Instrument to delete 
        :type instrument_code: str

        :param delete_all: Delete everything, even stuff in self.dont_recalc?  
        :type delete_all: bool

        
        [When working with a live system we listen to a message bus
        
        if a new price is received then we delete the prices in the 'data' object, and reload
        We do a similar thing in the system object; deleting anything in self._delete_on_recalc
        
        This means when we ask for self.optimal_positions(instrument_code) it has to recalc all
          intermediate steps as the cached 

        However we ignore anything in self._dont_recalc
        This is normally cross sectional data which we only want to calculate periodically
        
        if recalc_all is True then we delete that stuff as well
        because this is normally cross sectional data 
        
        (this is roughly equivalent to creating the systems object from scratch)
        
        >>> from systems.provided.example.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()

        >>> system=System([rawdata], data)
        >>> 
        >>> # get some price data
        >>> system.rawdata.get_instrument_price("EDOLLAR").tail(2)
                      price
        2015-04-21  97.9050
        2015-04-22  97.8325
        >>>
        >>> # this is stored in _price_dict 
        >>>
        >>> system._price_dict["EDOLLAR"].tail(2)
                      price
        2015-04-21  97.9050
        2015-04-22  97.8325
        >>>
        >>> # until we delete it
        >>>
        >>> system.delete_instrument_data_from_cache("EDOLLAR")
        >>>
        >>> # it's gone from the cache
        >>>
        >>> system._price_dict.get("EDOLLAR", "no key")
        'no key'
        >>>
        >>> # if we ask for it again, it will be there
        >>>
        >>> system.rawdata.get_instrument_price("EDOLLAR").tail(2)
                      price
        2015-04-21  97.9050
        2015-04-22  97.8325

        """
        
        
        if delete_all:
            nodes_to_delete=getattr(self,"_delete_on_recalc",[])+getattr(self,"_dont_recalc", [])
        else:
            nodes_to_delete=getattr(self, "_delete_on_recalc", [])

        
        for attr_to_delete in nodes_to_delete:
            dicttoclean=getattr(self, attr_to_delete, dict())
            if instrument_code in dicttoclean:
                ## remove data for this instrument
                throwaway=dicttoclean.pop(instrument_code)
                
        
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()
