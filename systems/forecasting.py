"""
construct the forecasting subsystem

Ways we can do this:

a) We do this by passing a list of trading rules

forecasting([trading_rule1, trading_rule2, ..])

Note that trading rules can be created using the tradingRule class, or you can just pass in the
  name of a function, or a function. 

We can also use a generate_variations method to create a list of multiple rules


b) or we can create from a system config


.... output from this will be forecast for each instrument, trading rule variation ...

need to have:

trading rules (eithier str pointers, or actual functions)
data arg(s) to be passed to trading rules (as str to use with getattr eg [system].data.getthing[(instrument)]
[default for this will be price only]
trading rules also need to have a 'simple' form, for quick and dirty use
probably nicest to have a wrapper function that wraps simple trading rules; in interactive world you'd pass the config etc into this

other config for trading rules, including forecast scalar [with defaults]

So config dict=(data=dict("","","") or data=(dict( actual data)), other_args=dict(a=1, b=2, ...),
       )

how to pass the system.config into the trading rules... 
... we parse the list of trading rules. if they contain a config dict we use that. otherwise we ... 
       use the relevant part of forecast_config. That allows people to override rules if they feel like it.

Note that system.config.forecast will be used if forecast_config not passed

We don't do scaling and capping here, but in the combined forecast module
(since we might want to estimate scaling factors live)


"""
from copy import copy

from systems.subsystem import SubSystem
from syscore.objects import resolve_function, resolve_data_method, hasallattr

class Rules(SubSystem):
    
    def __init__(self, trading_rules=None):
        """
        The SubSystem for forecasting
        
        This isn't an optional subsystem
        
        We eithier pass a dict or a list of trading rules (functions, strings specifying a function, or objects of class tradingRule)
          ... or we'll get it from the overall system config (trading_rules=None)
          
        """
        delete_on_recalc=["_raw_forecasts"]

        dont_delete=[]
        
        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_delete)

        setattr(self, "name", "forecast")
        setattr(self, "_stored_trading_rules", trading_rules)
        setattr(self, "_have_we_parsed_trading_rules", False)
        
    def trading_rules(self):
        """
        Ensure self.trading_rules is actually a properly specified list of trading rules
        """
        
        current_rules=self._stored_trading_rules
        
        ## we only want to do this once
        if self._have_we_parsed_trading_rules and current_rules is not None:
            return current_rules
        
        if current_rules is None:
            """
            We weren't passed anything in the command lines so need to inherit from the system config
            """
        
            if not hasattr(self, "parent"):
                raise Exception("A Rules subsystem needs to be part of a system to identify trading rules")
            
            ## self.parent.config.tradingrules will already be in dictionary form
            forecasting_config=tupilise_forecast_config(self.parent.config.tradingrules)
            new_rules=process_trading_rule_spec(forecasting_config)
            
        else:

        ### Okay, we've been passed a list manually which we'll use rather than getting it from the system
            new_rules=process_trading_rule_spec(current_rules)
            
        setattr(self, "_list_of_trading_rules", new_rules)
        setattr(self, "_parsed_trading_rules", True)
        return(new_rules)

    def get_raw_forecast(self, instrument_code, tradrule_variation):
        """
        This method- and only this method- is required for other parts of the system to work
        
        Does what it says on the tin - pulls the forecast for the trading rule
        
        This forecast may well need scaling and capping later
        
        FIXME - DIAGS FROM RULE?
        """
        
        trading_rule=self.trading_rules()[tradrule_variation]
        
        result=trading_rule.call(self.parent, instrument_code)
        
        return result



class tradingRule(object):
    """
    Container for trading rules
    
    Can be called manually or will be called when configuring a system
    
    rule: eithier a function, or a string identifying the module and name of function (eg 'systems.mytradingrules.myspecialrule')
    
    Functions must be of the form function(*dataargs, **kwargs), where *dataargs are unnamed data items, and **kwargs are named configuration items
    
                              data, an ordered list of strings identifying data to be used (default, just price)
                             other_args: a dictionary of named arguments to be passed to the trading rule
                             forecast_scalar: a number indicating
                             
    Alternatively if rule is a tuple then it will create 
                                  
    """
    
    def __init__(self, rule, data=list(), other_args=dict()):

        if hasallattr(rule, ["function", "data", "args"]):
            ## looks like it is already a trading rule
            self=rule
            

        elif type(rule) is tuple:
            if len(data)>0 or len(other_args)>0:
                print("WARNING: Creating trade rule with 'rule' tuple argument, ignoring data and/or other args")
            if len(rule)<>3:
                raise Exception("Creating trading rule with a tuple, must be length 3 exactly (function/name, data=[], args=dict())")
                
            self=tradingRule(rule[0], rule[1], rule[2])
        
        else:            
            ## Create from scratch
            
            ## turn string into function if required
            rule_function=resolve_function(rule)
            
            setattr(self, "function", rule_function)
            setattr(self, "data", data)
            setattr(self, "args", other_args)
        

    
    def call(self, system, instrument_code):
        """
        Actually call a trading rule
        
        To do this we need some data from the system
        """
        
        assert type(self.data) is list
        
        if len(self.data)==0:
            ## if no data provided defaults to using price
            datalist=["data.get_instrument_price"]
        else:
            datalist=self.data
            
        data_methods=[resolve_data_method(system, data_string) for data_string in datalist]
        data=[datamethod(instrument_code) for datamethod in data_methods]
        
        other_args=self.args
        
        """ FIXME: in a system rules need to return a tuple (result, diags) for diag to persist
        
        """
        
        return self.function(*data, **other_args)
        
    


def process_trading_rule_spec(trading_rules):
    """
    Returns a named dictionary of trading rule variations, with type tradingRule

        data types handled:  
           dict - parse each element of the dict and use the names
           list - parse each element of the list and give them arbitrary names
           anything else is assumed to be something we can pass to tradingRule (string, function, tuple, or tradingRule object)
            
    """
    
    if type(trading_rules) is dict:
        ## Note the system config will always come in as a dict
        ans=[(keyname, process_trading_rule_spec(trading_rules[keyname])) for keyname in trading_rules]
        return ans
    
    if type(trading_rules) is list:
        ## Give some arbitrary name
        ans=dict([("rule%d" % ruleid, process_trading_rule_spec(rule)) for (ruleid, rule) in enumerate(trading_rules)])
    
    ## Must be an individual rule (string, function or tuple)
    rule=trading_rules
    return tradingRule(rule)


def create_univariations(baseRule, list_of_args, argname, **kwargs):
    """
    Returns a dict of trading rule variations, varying only one named parameter
    
    eg create_variations(breakout, [4,10, 100, ], argname="window_size")
    """
    list_of_args_dict=[]
    for arg_value in list_of_args:
        thisdict=dict()
        thisdict[argname]=arg_value
        list_of_args_dict.append(thisdict)

    ans=create_variations(baseRule, list_of_args_dict, argname, **kwargs)
    
    return ans

def create_variations(baseRule, list_of_args_dict, key_argname=None, basename="rule",  nameformat="%s_%s"):
    """
    Returns a dict of trading rule variations 
    
    eg create_variations(ewmacrule, [dict(fast=2, slow=8), dict(fast=4, ...) ], argname="fast", basename="ewmac")
    
    """
    
    if key_argname is None:
         
        if all([len(args_dict)==1 for args_dict in list_of_args_dict]):
            ## okay to use argname as only seems to be one of them
                key_argname=args_dict[0].keys()[0]
        else:
            raise Exception("need to specify argname if more than one possibility")
        
    
    baseRulefunction=baseRule.function
    baseRuledata=baseRule.data
    
    ## these will be overwritten as we run through
    baseRuleargs=copy(baseRule.args)
    
    variations=dict()
    
    for args_dict in list_of_args_dict:
        if key_argname not in args_dict.keys():
            raise Exception("Argname %s missing from at least one set of argument values" % key_argname)
        
        for arg_name in args_dict.keys():
            baseRuleargs[arg_name]=args_dict[arg_name]
            
        rule_variation=tradingRule(baseRulefunction, baseRuledata, baseRuleargs)
        var_name=nameformat % (basename, str(args_dict[key_argname]))
        
        variations[var_name]=rule_variation
        
    return variations

def tupilise_forecast_config(forecasting_config):
    """
    We strictly limit config objects to be dictionaries and lists
    
    But we need 4-tuples to create sets of trading rules
    
    forecasting_config is a dict of dicts. Each dict element must contain keys: function (usually string), data (a list), args (a dict)
    
    Note if eithier data or args is missing then we create them
    """
    
    def _tupilise_trading_rule(tradingrule_dict):
        try:
            rule_function=tradingrule_dict['function']
        except KeyError:
            raise Exception("")
        
        if "data" in tradingrule_dict:
            rule_data=tradingrule_dict['data']
            if type(rule_data) is str:
                ## if only one kind of data won't get parsed properly
                rule_data=[rule_data]
        else:
            rule_data=[]
        
        if "args" in tradingrule_dict:
            rule_args=tradingrule_dict['args']
            
        else:
            rule_args=dict()
        
        return (rule_function, rule_data, rule_args)
        
    forecasting_config=dict([(rulename, _tupilise_trading_rule(forecasting_config[rulename])) for rulename in forecasting_config])
    
    return forecasting_config