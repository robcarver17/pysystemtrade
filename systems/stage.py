from syscore.objects import get_methods
from syslogdiag.log import logger
from systems.basesystem import System

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

    @property
    def name(self):
        return self._name()

    def _name(self) -> str:
        # normally overriden
        # REPLACE WITH name property in inherited methods
        return "unnamed"

    @property
    def description(self) -> str:
        return self._description()

    def _description(self) -> str:
        # normally overriden
        ## REPLACE WITH PROPERTY
        return ""

    def __repr__(self):
        return "SystemStage '%s' %s Try %s.methods()" % (
            self.name,
            self.description,
            self.name,
        )

    def methods(self):
        return get_methods(self)

    def _system_init(self, system: System):
        # method called once we have a system
        self._parent = system

        # and a log
        log = system.log.setup(stage=self.name)
        self._log = log

    @property
    def log(self) -> logger:
        log = getattr(self, "_log", None)
        return log

    @property
    def parent(self) -> System:
        parent  = getattr(self, "_parent", None)
        return parent