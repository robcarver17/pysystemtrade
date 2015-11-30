

class SubSystem(object):
    """
    Default subsystem
    
    Usually we inherit from this, rather than use 'in the raw'
    """
    
    def __init__(self):
        '''
        
        '''
        

        ## We set these to empty lists but in the inherited object they'll be overriden
        setattr(self, "_delete_on_recalc", [])
        setattr(self, "_dont_recalc", [])

        setattr(self, "name", "default")


    