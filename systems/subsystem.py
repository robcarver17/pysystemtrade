 

class SubSystem(object):
    """
    Default subsystem:  we inherit from this, rather than use 'in the raw'
    
    Here is the standard header to use for subsystems:
    
    Create a SubSystem for doing something
    
    
    KEY INPUT: system.....method(args)
                found in self.method(args) 
                
    KEY OUTPUT: system.subsystem_name.method(args)

    Name: subsystem_name
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
        return "SubSystem '%s' containing %s" % (self.name, attributes)
    
    