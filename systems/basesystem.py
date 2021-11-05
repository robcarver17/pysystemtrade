from syscore.objects import arg_not_supplied, missing_data
from sysdata.config.configdata import Config
from sysdata.config.instruments import get_duplicate_list_of_instruments_to_remove_from_config, get_list_of_bad_instruments_in_config, get_list_of_ignored_instruments_in_config, get_list_of_untradeable_instruments_in_config
from sysdata.sim.sim_data import simData
from syslogdiag.log_to_screen import logtoscreen, logger
from systems.system_cache import systemCache, base_system_cache

"""
This is used for items which affect an entire system, not just one instrument
"""
ALL_KEYNAME = "all"


class System(object):
    """
    system objects are used for signal processing in a 'tree' like framework


    This is the base class which all systems inherit

    Systems are:

        made up of stages

       take a data, and optionally a config object

    The system only has one method 'of its own' which is get_instrument_list

    """

    def __init__(
            self,
            stage_list: list,
            data: simData,
            config: Config=arg_not_supplied,
            log: logger=logtoscreen("base_system")):
        """
        Create a system object for doing simulations or live trading

        :param stage_list: A list of stages
        :type stage_list: list of systems.stage.SystemStage (or anything that inherits from it)

        :param data: data for doing simulations
        :type data: sysdata.data.simData (or anything that inherits from that)

        :param config: Optional configuration
        :type config: sysdata.configdata.Config

        :returns: new system object

        >>> from systems.stage import SystemStage
        >>> stage=SystemStage()
        >>> from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
        >>> data=csvFuturesSimData()
        >>> System([stage], data)
        System base_system with .config, .data, and .stages: Need to replace method when inheriting

        """

        if config is arg_not_supplied:
            # Default - for very dull systems this is sufficient
            config = Config()

        self._data = data
        self._config = config
        self._log = log

        self.config.system_init(self)
        self.data.system_init(self)
        self._setup_stages(stage_list)
        self._cache = systemCache(self)


    def _setup_stages(self, stage_list: list):
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
            current_stage_name = stage.name

            # Each stage has a link back to the parent system
            # This init sets this, and also passes the system logging object
            stage.system_init(self)

            if current_stage_name in stage_names:
                raise Exception(
                    "You have duplicate subsystems with the name %s. Remove "
                    "one of them, or change a name." % current_stage_name
                )

            setattr(self, current_stage_name, stage)
            stage_names.append(current_stage_name)

        self._stage_names = stage_names


    def __repr__(self):
        sslist = ", ".join(self.stage_names)
        description = "System %s with .config, .data, and .stages: " % self.name

        return description + sslist


    @property
    def log(self):
        return self._log

    @property
    def data(self):
        return self._data

    @property
    def config(self):
        return self._config

    @property
    def name(self):
        return "base_system"

    @property
    def cache(self):
        return self._cache

    @property
    def stage_names(self):
        return self._stage_names

    def set_logging_level(self, new_log_level: str):
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

        self.data.log.set_logging_level(new_log_level)

    # note we have to use this special cache here, or we get recursion problems
    @base_system_cache()
    def get_instrument_list(self) -> list:
        """
        Get the instrument list

        :returns: list of instrument_code str
        """
        instrument_list = self._get_raw_instrument_list_from_config()
        instrument_list = self._remove_instruments_from_instrument_list(
                                                                   instrument_list)

        instrument_list = sorted(set(list(instrument_list)))

        return instrument_list

    def _get_raw_instrument_list_from_config(self) -> list:
        config = self.config
        try:
            # if instrument weights specified in config ...
            instrument_list = config.instrument_weights.keys()
        except:
            try:
                # alternative place if no instrument weights
                instrument_list = config.instruments
            except:
                try:
                    # okay maybe not, must be in data
                    instrument_list = self.data.get_instrument_list()
                except:
                    raise Exception("Can't find instrument_list anywhere!")

        return instrument_list

    def _remove_instruments_from_instrument_list(self, instrument_list):
        list_of_instruments_to_remove = self.get_list_of_instruments_to_remove()

        instrument_list = [instrument for instrument in instrument_list
                           if instrument not in list_of_instruments_to_remove]

        return instrument_list

    @base_system_cache()
    def get_list_of_instruments_to_remove(self) -> list:
        list_of_duplicates = self.get_list_of_duplicate_instruments_to_remove()
        list_of_ignored = self.get_list_of_ignored_instruments_to_remove()

        joint_list = list(set(list_of_ignored+list_of_duplicates))

        return joint_list

    def get_list_of_duplicate_instruments_to_remove(self):
        duplicate_list = get_duplicate_list_of_instruments_to_remove_from_config(self.config)
        if len(duplicate_list)>0:
            self.log.msg("Following instruments are 'duplicate_markets' and will be excluded from sim %s " % str(
                duplicate_list))

        return duplicate_list

    @base_system_cache()
    def get_list_of_ignored_instruments_to_remove(self) -> list:
        ignore_instruments = get_list_of_ignored_instruments_in_config(self.config)
        if len(ignore_instruments)>0:
            self.log.msg("Following instruments are marked as 'ignore_instruments': not included: %s" % str(ignore_instruments))

        return ignore_instruments

    @base_system_cache()
    def get_list_of_markets_not_trading_but_with_data(self) -> list:
        trading_restrictions = self.get_list_of_markets_with_trading_restrictions()
        bad_markets = self.get_list_of_bad_markets()

        not_trading = trading_restrictions + bad_markets
        not_trading_unique = list(set(not_trading))

        return not_trading_unique

    @base_system_cache()
    def get_list_of_markets_with_trading_restrictions(self) -> list:
        trading_restrictions = get_list_of_untradeable_instruments_in_config(self.config)
        if len(trading_restrictions)>0:
            ## will only log once as cached
            self.log.msg("Following instruments have restricted trading: optimisation will not trade them %s " % str(
                trading_restrictions))
        return trading_restrictions

    @base_system_cache()
    def get_list_of_bad_markets(self) -> list:
        bad_markets = get_list_of_bad_instruments_in_config(self.config)
        if len(bad_markets)>0:
            ## will only log once as cached
            self.log.msg("Following instruments are marked as 'bad_markets': optimisation will not trade them %s" % str(bad_markets))

        return bad_markets


if __name__ == "__main__":
    import doctest

    doctest.testmod()
