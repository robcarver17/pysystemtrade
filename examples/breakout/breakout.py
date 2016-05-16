from syscore.pdutils import turnover
from sysdata.configdata import Config

from systems.provided.futures_chapter15.estimatedsystem import futures_system
from systems.provided.moretradingrules.morerules import breakout

import pandas as pd
import numpy as np
from matplotlib.pyplot import show, legend, matshow


my_config = Config("examples.breakout.breakoutfuturesestimateconfig.yaml")

system = futures_system(config=my_config, log_level="on")

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
