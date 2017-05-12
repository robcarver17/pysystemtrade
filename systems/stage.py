from syscore.objects import get_methods
from syslogdiag.log import logtoscreen


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
        setattr(self, "name", self._name())
        setattr(self, "description", self._description())

        # this will normally be overriden by the base system when we call _system_init
        setattr(self, "log", logtoscreen(stage="config"))

    def _name(self):
        ## normally overriden
        return "unnamed"

    def _description(self):
        ## normally overriden
        return ""

    def __repr__(self):
        return "SystemStage '%s' %s Try %s.methods()" % (self.name,
                                                         self.description,
                                                         self.name)

    def methods(self):
        return get_methods(self)

    def _system_init(self, system):
        # method called once we have a system
        setattr(self, "parent", system)

        # and a log
        log = system.log.setup(stage=self.name)
        setattr(self, "log", log)
