"""
Configuration is used to control the behaviour of a system

Config can be passed as a dict, a filename from which a YAML spec is read in
and then parsed

There are no set elements for configurations, although typically they will
contain:

parameters - a dict of values which override those in system.defaults
trading_rules - a specification of the trading rules for a system

"""
from copy import copy

import yaml
from syscore.fileutils import get_filename_for_package
from systems.defaults import get_system_defaults
from syslogdiag.log import logtoscreen
from syscore.objects import get_methods

RESERVED_NAMES = ["log", "_elements"]


class Config(object):
    def __init__(self, config_object=dict()):
        """
        Config objects control the behaviour of systems

        :param config_object: Either:
                        a string (which points to a YAML filename)
                        or a dict (which may nest many things)
                        or a list of strings or dicts (build config from
                        multiple elements, latter elements will overwrite
                        earlier oness)

        :type config_object: str or dict

        :returns: new Config object

        >>> Config(dict(parameters=dict(p1=3, p2=4.6), another_thing=[]))
        Config with elements: another_thing, parameters

        >>> Config("sysdata.tests.exampleconfig.yaml")
        Config with elements: parameters, trading_rules

        >>> Config(["sysdata.tests.exampleconfig.yaml", dict(parameters=dict(p1=3, p2=4.6), another_thing=[])])
        Config with elements: another_thing, parameters, trading_rules

        """
        setattr(self, "_elements", [])  # will be populated later

        # this will normally be overriden by the base system
        setattr(self, "log", logtoscreen(stage="config"))

        if isinstance(config_object, list):
            # multiple configs
            for config_item in config_object:
                self._create_config_from_item(config_item)
        else:
            self._create_config_from_item(config_object)

    def _system_init(self, base_system):
        """
        This is run when added to a base system

        :param base_system
        :return: nothing
        """

        ## inherit the log
        setattr(self, "log", base_system.log.setup(stage="config"))

        ## fill with defaults
        self.fill_with_defaults()

    def _create_config_from_item(self, config_item):
        if isinstance(config_item, dict):
            # its a dict
            self._create_config_from_dict(config_item)

        elif isinstance(config_item, str):
            # must be a file YAML'able, from which we load the
            filename = get_filename_for_package(config_item)
            with open(filename) as file_to_parse:
                dict_to_parse = yaml.load(file_to_parse)

            self._create_config_from_dict(dict_to_parse)

        else:
            error_msg = ("Can only create a config with a nested dict or the "
                         "string of a 'yamable' filename, or a list "
                         "comprising these things")
            self.log.critical(error_msg)

    def _create_config_from_dict(self, config_object):
        """
        Take a dictionary object and turn it into self

        When we've finished self will be an object where the attributes are

        So if config_objec=dict(a=2, b=2)
        Then this object will become self.a=2, self.b=2
        """
        base_config = config_object.get('base_config')
        if base_config is not None:
            self._create_config_from_item(base_config)

        attr_names = list(config_object.keys())
        [
            setattr(self, keyname, config_object[keyname])
            for keyname in config_object
        ]
        existing_elements = getattr(self, "_elements", [])
        new_elements = list(set(existing_elements + attr_names))

        setattr(self, "_elements", new_elements)

    def __delattr__(self, element_name):
        """
        Remove element_name from config

        >>> config=Config(dict(parameters=dict(p1=3, p2=4.6), another_thing=[]))
        >>> del(config.another_thing)
        >>> config
        Config with elements: parameters
        >>>
        """
        # to avoid recursion, we must first avoid recursion
        super().__delattr__(element_name)

        elements = self._elements
        elements.remove(element_name)

    def __setattr__(self, element_name, value):
        """
        Add / replace element_name in config

        >>> config=Config(dict(parameters=dict(p1=3, p2=4.6), another_thing=[]))
        >>> config.another_thing="test"
        >>> config.another_thing
        'test'
        >>> config.yet_another_thing="more testing"
        >>> config
        Config with elements: another_thing, parameters, yet_another_thing
        >>>
        """
        # to avoid recursion, we must first avoid recursion
        super().__setattr__(element_name, value)

        if element_name not in RESERVED_NAMES:
            elements = self._elements
            if element_name not in elements:
                elements.append(element_name)

    def fill_with_defaults(self):
        """
        Fills with defaults
        >>> config=Config(dict(forecast_cap=22.0, forecast_scalar_estimate=dict(backfill=False), forecast_weight_estimate=dict(correlation_estimate=dict(min_periods=40))))
        >>> config
        Config with elements: forecast_cap, forecast_scalar_estimate, forecast_weight_estimate
        >>> config.fill_with_defaults()
        >>> config.forecast_scalar
        1.0
        >>> config.forecast_cap
        22.0
        >>> config.forecast_scalar_estimate['pool_instruments']
        True
        >>> config.forecast_scalar_estimate['backfill']
        False
        >>> config.forecast_weight_estimate['correlation_estimate']['min_periods']
        40
        >>> config.forecast_weight_estimate['correlation_estimate']['ew_lookback']
        500
        """
        self.log.msg("Adding config defaults")

        existing_elements = self._elements
        default_elements = list(get_system_defaults().keys())

        new_elements = list(set(existing_elements + default_elements))
        [
            self.element_fill_with_defaults(element_name)
            for element_name in new_elements
        ]

        setattr(self, "_elements", new_elements)

    def element_fill_with_defaults(self, element_name):
        """
        Fills the config with any defaults for element_name

        If item is a dict, then calls dict_with_defaults

        """

        config_item = getattr(self, element_name, None)
        default_item = get_system_defaults().get(element_name, None)

        if config_item is None:
            if default_item is None:
                error_msg = "Element %s not in defaults or config" % element_name
                self.log.critical(error_msg)

            else:
                config_item = default_item

        if isinstance(config_item, dict):
            if isinstance(default_item, dict):
                config_item = self.dict_with_defaults(element_name)
        else:
            if isinstance(default_item, dict):
                error_msg = "Config item %s is not a dict, but it is in the default!" % element_name
                self.log.critical(error_msg)

        setattr(self, element_name, config_item)

    def dict_with_defaults(self, element_name):
        """
        Returns config.element_name with any keys missing replaced with system defaults

        Only works for configs where the element is a dict
        """
        config_dict = copy(getattr(self, element_name, dict()))

        default_dict = get_system_defaults().get(element_name, dict())
        required = default_dict.keys()

        for dict_key in required:
            # key automatically in default...
            if dict_key not in config_dict:
                config_dict[dict_key] = default_dict[dict_key]

            if isinstance(config_dict[dict_key], dict):
                if isinstance(default_dict[dict_key], dict):
                    config_dict[dict_key] = self.nested_dict_with_defaults(
                        element_name, dict_key)
            else:
                if isinstance(default_dict[dict_key], dict):
                    error_msg = "You've created a config where %s.%s is not a dict, but it is in the default config!" % (
                        element_name, dict_key)
                    self.log.critical(error_msg)

        return config_dict

    def nested_dict_with_defaults(self, element_name, dict_name):
        """
        Returns config.element_name[dict_name] with any keys required replaced
        with system defaults

        Only works for configs where the element is a nested dict
        """
        element_in_config = copy(getattr(self, element_name, dict()))
        nested_config_dict = element_in_config.get(dict_name, dict())

        element_in_default = get_system_defaults().get(element_name, dict())
        nested_default_dict = element_in_default.get(dict_name, dict())

        required = nested_default_dict.keys()

        if len(required) > 0:

            for dict_key in required:
                if dict_key not in nested_config_dict:
                    nested_config_dict[dict_key] = nested_default_dict[
                        dict_key]

        return nested_config_dict

    def __repr__(self):
        element_names = sorted(getattr(self, "_elements", []))
        element_names = ", ".join(element_names)
        return "Config with elements: " + element_names


if __name__ == '__main__':
    import doctest
    doctest.testmod()
