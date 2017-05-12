from sysdata.configdata import Config
from syslogdiag.log import logtoscreen
from systems.system_cache import systemCache, base_system_cache
"""
This is used for items which affect an entire system, not just one instrument
"""
ALL_KEYNAME = "all"


class System(object):
    '''
    system objects are used for signal processing in a 'tree' like framework


    This is the base class which all systems inherit

    Systems are:

        made up of stages

       take a data, and optionally a config object

    The system only has one method 'of its own' which is get_instrument_list

    '''

    def __init__(self,
                 stage_list,
                 data,
                 config=None,
                 log=logtoscreen("base_system")):
        """
        Create a system object for doing simulations or live trading

        :param stage_list: A list of stages
        :type stage_list: list of systems.stage.SystemStage (or anything that inherits from it)

        :param data: data for doing simulations
        :type data: sysdata.data.Data (or anything that inherits from that)

        :param config: Optional configuration
        :type config: sysdata.configdata.Config

        :returns: new system object

        >>> from systems.stage import SystemStage
        >>> stage=SystemStage()
        >>> from sysdata.csvdata import csvFuturesData
        >>> data=csvFuturesData()
        >>> System([stage], data)
        System with stages: unnamed

        """

        if config is None:
            # Default - for very dull systems this is sufficient
            config = Config()

        setattr(self, "data", data)
        setattr(self, "config", config)
        setattr(self, "log", log)

        self.config._system_init(self)
        self.data._system_init(self)

        stage_names = []

        try:
            iter(stage_list)
        except AssertionError:
            raise Exception(
                "You didn't pass a list into this System instance; even just one stage should be System([stage_instance])"
            )

        for stage in stage_list:
            """
            This is where we put the methods to store various stages of the process

            """

            # Stages have names, which are also how we find them in the system
            # attributes
            sub_name = stage.name

            # Each stage has a link back to the parent system
            # This init sets this, and also passes the system logging object
            stage._system_init(self)

            if sub_name in stage_names:
                raise Exception(
                    "You have duplicate subsystems with the name %s. Remove "
                    "one of them, or change a name." % sub_name)

            setattr(self, sub_name, stage)

            stage_names.append(sub_name)

        setattr(self, "_stage_names", stage_names)
        """
        The cache hides all intermediate results

        We call optimal_positions and then that propogates back finding all the
        data we need

        The results are then cached in the object. Should we call
            delete_instrument_data (in base class system) then everything
            related to a particular instrument is removed from these 'nodes'
            except for protected items

        This is very useful in live trading when we don't want to update eg
            cross sectional data every sample
        """

        setattr(self, "cache", systemCache(self))
        self.name = "base_system"  # makes caching work and for general consistency

    def __repr__(self):
        sslist = ", ".join(self._stage_names)
        return "System with .config, .data, and .stages: " + sslist

    def set_logging_level(self, new_log_level):
        """

        Set the log level for the system

        :param new_log_level: one of ["off", "terse", "on"]
        :type new_log_level: str

        :returns: None
        """

        self.log.set_logging_level(new_log_level)
        for stage_name in self._stage_names:
            stage = getattr(self, stage_name)
            stage.log.set_logging_level(new_log_level)

    # note we have to use this special cache here, or we get recursion problems
    @base_system_cache()
    def get_instrument_list(self):
        """
        Get the instrument list

        :returns: list of instrument_code str
        """
        try:
            # if instrument weights specified in config ...
            instrument_list = self.config.instrument_weights.keys()
        except:
            try:
                # alternative place if
                instrument_list = self.config.instruments
            except:
                # okay maybe not, must be in data
                instrument_list = self.data.get_instrument_list()

        instrument_list = sorted(set(list(instrument_list)))
        return instrument_list

    def calc_or_cache_nested(self, *args, **kwargs):
        raise Exception(
            "You are using old style caching: rewrite your functions with decorators @input, @output, @diagnostic"
        )

    def calc_or_cache(self, *args, **kwargs):
        raise Exception(
            "You are using old style caching: rewrite your functions with decorators @input, @output, @diagnostic"
        )


if __name__ == '__main__':
    import doctest
    doctest.testmod()
