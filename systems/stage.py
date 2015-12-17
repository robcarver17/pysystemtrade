

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

        # We set these to empty lists but in the inherited object they'll be
        # overriden
        setattr(self, "_protected", [])
        setattr(self, "name", "unnamed")

    def __repr__(self):
        return "SystemStage '%s'" % self.name
