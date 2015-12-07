 

class SystemStage(object):
    """
    Default stage object:  we inherit from this, rather than use 'in the raw'
    
    Here is the standard header to use for stages:
    
    Create a SystemStage for doing something
    
    
    KEY INPUT: system.....method(args)
                found in self.method(args) 
                
    KEY OUTPUT: system.stage_name.method(args)

    Name: stage_name
    """
    
    def __init__(self):
        '''
        
        '''
        

        ## We set these to empty lists but in the inherited object they'll be overriden
        setattr(self, "_delete_on_recalc", [])
        setattr(self, "_dont_recalc", [])

        setattr(self, "name", "default")


    def __repr__(self):
        attributes=getattr(self, "_delete_on_recalc", [])+getattr(self, "_dont_recalc", [])
        attributes=", ".join(attributes)
        return "SystemStage '%s' containing %s" % (self.name, attributes)
    
    