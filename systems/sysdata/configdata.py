"""
Configuration is used to control the behaviour of a system

Config can be passed as a dict, a filename from which a YAML spec is read in and then parsed

There are no set elements for configurations, although typically they will contain:

parameters - a dict of values which override those in system.defaults
trading_rules - a specification of the trading rules for a system

"""
import yaml

class configData(object):
    
    def __init__(self,  config_object=dict()):
        """
        We can create a config_object with eithier a string (which points to a filename) or a nested dict
        """
        if type(config_object) is dict:
            ## its a dict
            self._create_config_from_dict(config_object)
            
        elif type(config_object) is str:
            ## must be a file YAML'able, from which we load the 
            with open(config_object) as file_to_parse:
                dict_to_parse=yaml.load(file_to_parse)
                
            self._create_config_from_dict(dict_to_parse)
                
                
        else:
            raise Exception("Can only create a config with a nested dict or the string of a 'yamable' filename")

    def _create_config_from_dict(self, config_object):
        """
        Take a dictionary object and turn it into self 
        
        When we've finished self will be an object where the attributes are
        
        So if config_objec=dict(a=2, b=2)
        Then this object will become self.a=2, self.b=2
        
        """
        attr_names=config_object.keys()
        [setattr(self, keyname, config_object[keyname]) for keyname in config_object]
        
        setattr(self, "_elements", attr_names)
        
    def __repr__(self):
        element_names=",".join(self._elements)
        return "Config with elements: "+element_names
        
         
