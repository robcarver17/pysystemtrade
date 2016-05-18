from syscore.pdutils import turnover
from sysdata.configdata import Config

from systems.provided.futures_chapter15.estimatedsystem import futures_system
from systems.provided.moretradingrules.morerules import breakout

import pandas as pd
import numpy as np
from matplotlib.pyplot import show, legend, matshow


my_config = Config("examples.breakout.breakoutfuturesestimateconfig.yaml")

system = futures_system(config=my_config, log_level="on")

"""
price=system.data.daily_prices("CRUDE_W")

price.plot()
show()

lookback=250

roll_max = pd.rolling_max(price, lookback, min_periods=min(len(price), np.ceil(lookback/2.0)))
roll_min = pd.rolling_min(price, lookback, min_periods=min(len(price), np.ceil(lookback/2.0)))


all=pd.concat([price, roll_max, roll_min], axis=1)
all.columns=["price", "max",  "min"]
all.plot()
legend(loc="top left")
show()

roll_mean = (roll_max+roll_min)/2.0

all=pd.concat([price, roll_max, roll_mean,roll_min], axis=1)
all.columns=["price", "max", "mean", "min"]
all.plot()
legend(loc="top left")
show()


## gives a nice natural scaling
output = 40.0*((price - roll_mean) / (roll_max - roll_min))

output.plot()
show()


print(turnover(output, 10.0))

smooth=int(250/4.0)
smoothed_output = pd.ewma(output, span=smooth, min_periods=np.ceil(smooth/2.0))
print(turnover(smoothed_output, 10.0))

smoothed_output.plot()
show()

## check window size correlation and also turnover properties
outputall=[]

wslist=[4,5,6,7,8,9,10,15,20,25,30,35,40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 
           180, 200, 240, 280, 320, 360, 500]

for ws in wslist:
    smoothed_output = breakout(price, ws)
    
    ## 
    avg_forecast=float(smoothed_output.abs().mean())
    print("WS %d turnover %.2f" % (ws, turnover(smoothed_output, avg_forecast)))
    outputall.append(smoothed_output)

outputall=pd.concat(outputall, axis=1)
outputall.columns=wslist
print(outputall.corr())

print()

outputall.iloc[:,[6, 8, 12, 16, 21, 26]].round(2)

matshow(outputall.iloc[:,[6, 8, 12, 16, 21, 26]].corr())
show()

system.rules.get_raw_forecast("CRUDE_W", "breakout160").plot()
show()
"""


my_config = Config("examples.breakout.breakoutfuturesestimateconfig.yaml")
my_config.forecast_scalar_estimate['pool_instruments']=False

## logging off as printing results
system = futures_system(config=my_config, log_level="off")

instr_list=system.get_instrument_list()
variations=["breakout"+str(ws) for ws in [10, 20, 40, 80, 160, 320]]

for rule_name in variations:
    all_scalars=[]
    for instrument in instr_list:
        scalar=float(system.forecastScaleCap.get_forecast_scalar(instrument, rule_name).tail(1).values)
        all_scalars.append((instrument, scalar))
    all_scalars=sorted(all_scalars, key=lambda x: x[1])
    print("%s: %s %s" % (rule_name, str(all_scalars[0]), str(all_scalars[-1])))
    all_scalar_values=[x[1] for x in all_scalars]
    print("mean %.3f std %.3f min %.3f max %.3f" % (np.nanmean(all_scalar_values), np.nanstd(all_scalar_values),
                                                    np.nanmin(all_scalar_values), np.nanmax(all_scalar_values)))
    
## reload config so we get scalars estimated with pooling behaviour
my_config = Config("examples.breakout.breakoutfuturesestimateconfig.yaml")

## logging off as printing results
system = futures_system(config=my_config, log_level="off" )
for rule_name in variations:
    instrument="CRUDE_W" ## doesn't matter
    scalar=float(system.forecastScaleCap.get_forecast_scalar(instrument, rule_name).tail(1).values)
    print("%s: %.3f" % (rule_name, scalar))

## now turnovers    
for rule_name in variations:
    all_turnovers=[]
    for instrument in instr_list:
        turnover_value=system.accounts.forecast_turnover(instrument, rule_name)
        all_turnovers.append((instrument, turnover_value))
    all_turnovers=sorted(all_turnovers, key=lambda x: x[1])
    print("%s: %s %s" % (rule_name, str(all_turnovers[0]), str(all_turnovers[-1])))
    all_turnover_values=[x[1] for x in all_turnovers]
    print("mean %.3f std %.3f" % (np.nanmean(all_turnover_values), np.nanstd(all_turnover_values)))
    
    
## limit the rules to just breakout for now
my_config = Config("examples.breakout.breakoutfuturesestimateconfig.yaml")
my_config.trading_rules = dict([(rule_name, my_config.trading_rules[rule_name]) for rule_name in variations])

system = futures_system(config=my_config, log_level="on")
