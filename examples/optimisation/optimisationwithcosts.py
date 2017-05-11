from matplotlib.pyplot import show, title

from systems.provided.futures_chapter15.estimatedsystem import futures_system

rule_variations = [
    'carry', 'ewmac2_8', 'ewmac4_16', 'ewmac8_32', 'ewmac16_64', 'ewmac32_128',
    'ewmac64_256'
]
"""
## pool everything, no costs
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['apply_cost_weight']=False
system.config.forecast_cost_estimates['use_pooled_costs']=True
system.config.forecast_weight_estimate['pool_gross_returns']=True
system.config.forecast_weight_estimate['cost_multiplier']=0.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=999.0
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market


## pool everything with costs
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['apply_cost_weight']=False
system.config.forecast_cost_estimates['use_pooled_costs']=True
system.config.forecast_weight_estimate['pool_gross_returns']=True
system.config.forecast_weight_estimate['cost_multiplier']=1.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=999.0
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()


print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

## individual market estimation
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations

system.config.forecast_weight_estimate['apply_cost_weight']=False
system.config.forecast_cost_estimates['use_pooled_costs']=False
system.config.forecast_weight_estimate['pool_gross_returns']=False
system.config.forecast_weight_estimate['cost_multiplier']=1.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=999.0
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

## dont pool costs
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['apply_cost_weight']=False
system.config.forecast_cost_estimates['use_pooled_costs']=False
system.config.forecast_weight_estimate['pool_gross_returns']=True
system.config.forecast_weight_estimate['cost_multiplier']=1.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=999.0
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()


## equalise gross, only use costs
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['apply_cost_weight']=False
system.config.forecast_cost_estimates['use_pooled_costs']=False
system.config.forecast_weight_estimate['pool_gross_returns']=True
system.config.forecast_weight_estimate['cost_multiplier']=1.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=999.0
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=True


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()



## subtract costs from gross return multiply by a factor
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['apply_cost_weight']=False
system.config.forecast_cost_estimates['use_pooled_costs']=False
system.config.forecast_weight_estimate['pool_gross_returns']=True
system.config.forecast_weight_estimate['cost_multiplier']=3.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=999.0
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

## cost weighting
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['apply_cost_weight']=True
system.config.forecast_cost_estimates['use_pooled_costs']=False
system.config.forecast_weight_estimate['pool_gross_returns']=True
system.config.forecast_weight_estimate['cost_multiplier']=0.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=999.0
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

## cost threshold
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['apply_cost_weight']=False
system.config.forecast_cost_estimates['use_pooled_costs']=False
system.config.forecast_weight_estimate['pool_gross_returns']=True
system.config.forecast_weight_estimate['cost_multiplier']=1.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=.13
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()


## favourite
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['apply_cost_weight']=True
system.config.forecast_cost_estimates['use_pooled_costs']=False
system.config.forecast_weight_estimate['pool_gross_returns']=True
system.config.forecast_weight_estimate['cost_multiplier']=0.0
system.config.forecast_weight_estimate['ceiling_cost_SR']=0.13
system.config.forecast_weight_estimate['method']="bootstrap"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()


## shrinkage
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['method']="shrinkage"
system.config.forecast_weight_estimate['equalise_gross']=False


print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

## equal weights
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['method']="equal_weights"
system.config.forecast_weight_estimate['apply_cost_weight']=False

print(system.combForecast.get_forecast_weights("EUROSTX").tail(1)) ## cheap market
system.combForecast.get_forecast_weights("EUROSTX").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()

print(system.combForecast.get_forecast_weights("V2X").tail(1)) ## expensive market
system.combForecast.get_forecast_weights("V2X").iloc[-1,:].loc[rule_variations].plot(kind="barh")
show()



## instruments
system=futures_system()
system.set_logging_level("on")
del(system.config.rule_variations)

system=futures_system()
system.set_logging_level("on")

system.config.rule_variations=rule_variations
system.config.forecast_weight_estimate['method']="shrinkage"

system.config.instrument_weight_estimate['method']="bootstrap"
system.config.instrument_weight_estimate['apply_cost_weight']=True
system.config.instrument_weight_estimate['cost_multiplier']=0.0
system.config.instrument_weight_estimate['ceiling_cost_SR']=0.13
system.config.instrument_weight_estimate['equalise_gross']=False


print(system.portfolio.get_instrument_weights())
system.portfolio.get_instrument_weights().iloc[-1,:].plot(kind="barh")
show()
"""

# instruments - equal weights
system = futures_system()
system.set_logging_level("on")
del (system.config.rule_variations)

system = futures_system()
system.set_logging_level("on")

system.config.rule_variations = rule_variations
system.config.forecast_weight_estimate['method'] = "equal_weights"

system.config.instrument_weight_estimate['method'] = "equal_weights"
system.config.instrument_weight_estimate['apply_cost_weight'] = True
system.config.instrument_weight_estimate['cost_multiplier'] = 0.0
system.config.instrument_weight_estimate['ceiling_cost_SR'] = 0.13
system.config.instrument_weight_estimate['equalise_gross'] = False

print(system.portfolio.get_instrument_weights())
system.portfolio.get_instrument_weights().iloc[-1, :].plot(kind="barh")
show()
