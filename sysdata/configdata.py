"""
Configuration is used to control the behaviour of a system

Config can be passed as a dict, a filename from which a YAML spec is read in and then parsed

There are no set elements for configurations, although typically they will contain:

parameters - a dict of values which override those in system.defaults
trading_rules - a specification of the trading rules for a system

"""
import yaml
from syscore.fileutils import get_filename_for_package


class Config(object):

    def __init__(self, config_object=dict()):
        """
        Config objects control the behaviour of systems

        :param config_object: Eithier:
                        a string (which points to a YAML filename)
                        or a dict (which may nest many things)
                        or a list of strings or dicts (build config from multiple elements, latter elements will overwrite earlier oness)

        :type config_object: str or dict

        :returns: new Config object

        >>> Config(dict(parameters=dict(p1=3, p2=4.6), another_thing=[]))
        Config with elements: another_thing, parameters

        >>> Config("sysdata.tests.exampleconfig.yaml")
        Config with elements: parameters, trading_rules

        >>> Config(["sysdata.tests.exampleconfig.yaml", dict(parameters=dict(p1=3, p2=4.6), another_thing=[])])
        Config with elements: another_thing, parameters, trading_rules

        """

        if isinstance(config_object, list):
            # multiple configs
            for config_item in config_object:
                self._create_config_from_item(config_item)
        else:
            self._create_config_from_item(config_object)

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
            raise Exception(
                "Can only create a config with a nested dict or the string of a 'yamable' filename, or a list comprising these things")

    def _create_config_from_dict(self, config_object):
        """
        Take a dictionary object and turn it into self

        When we've finished self will be an object where the attributes are

        So if config_objec=dict(a=2, b=2)
        Then this object will become self.a=2, self.b=2

        """
        attr_names = list(config_object.keys())
        [setattr(self, keyname, config_object[keyname])
         for keyname in config_object]
        existing_elements = getattr(self, "_elements", [])
        new_elements = list(set(existing_elements + attr_names))

        setattr(self, "_elements", new_elements)

    def __repr__(self):
        element_names = sorted(getattr(self, "_elements", []))
        element_names = ", ".join(element_names)
        return "Config with elements: " + element_names


if __name__ == '__main__':
    import doctest
    doctest.testmod()
