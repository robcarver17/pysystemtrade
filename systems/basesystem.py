'''
system objects are used for signal processing in a 'tree' like framework

This is the base class which all systems inherit

Systems are:

    made up of subsystems

   take a data and a config object
   
   have a delete_key method and optimal_position method by default
   
   have an optimal_positions method (which by default does nothing, but we include here to ensure
      we don't forget to override it in inherited systems)
      
'''
from sysdata.configdata import configData

class system(object):
    '''
    classdocs
    '''


    def __init__(self,  data, config=None, subsystemlist=[]):
        '''
        '''
        
        if config is None:
            ## Default - for very dull systems this is sufficient
            config=configData()
            
        setattr(self, "data", data)
        setattr(self, "config", config)

        delete_on_recalc=[]
        dont_recalc=[]
        subsystem_names=[]
        
        for subsystem in subsystemlist:
            
            """
            This is where we put the methods to store various stages of the process
            
            """

            setattr(subsystem, "parent", self)
            sub_name=subsystem.name
            subsystem_names.append(sub_name)
            delete_on_recalc=delete_on_recalc+subsystem._delete_on_recalc
            dont_recalc=dont_recalc+subsystem._dont_recalc
            setattr(self, sub_name, subsystem)

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
        
        for dictname in allitems:
            empty_dict=dict()
            setattr(self, dictname, empty_dict)
        
    def __repr__(self):
        sslist=", "+self._subsystem_names
        return "System with subsystems: "+sslist
        
    def delete_instrument_data(self, instrument_code, recalc_all=False):
        """
        When working with a live system we listen to a message bus
        
        if a new price is received then we delete the prices in the 'data' object, and reload
        We do a similar thing in the system object; deleting anything in self._delete_on_recalc
        
        This means when we ask for self.optimal_positions(instrument_code) it has to recalc all
          intermediate steps as the cached 

        However we ignore anything in self._dont_recalc
        This is normally cross sectional data which we only want to calculate periodically
        
        if recalc_all is True then we delete that stuff as well
        because this is normally cross sectional data 
        
        (this is roughly equivalent to creating the systems object from scratch)
        
        For cross sectional there will need to be a completeness check to make sure all nodes required
              are included before returning a cached data
        """
        
        nodes_to_delete=self._delete_on_recalc
        
        if recalc_all:
            nodes_to_delete=nodes_to_delete+self._dont_recalc
        
        for attr_to_delete in nodes_to_delete:
            dicttoclean=getattr(self, attr_to_delete)
            if instrument_code in dicttoclean:
                ## remove data for this instrument
                throwaway=dicttoclean.pop(instrument_code)
                
        
    
        