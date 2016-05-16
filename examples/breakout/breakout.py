from sysdata.configdata import Config

from systems.provided.futures_chapter15.estimatedsystem import futures_system
from systems.provided.moretradingrules.morerules import breakout

import pandas as pd
import numpy as np
from matplotlib.pyplot import show, legend

my_config = Config("examples.breakout.breakoutfuturesestimateconfig.yaml")

system = futures_system(config=my_config, log_level="on")

price=system.data.daily_prices("CRUDE_W")

lookback=100

roll_max = pd.rolling_max(price, lookback, min_periods=min(len(price), np.ceil(lookback/2.0)))
roll_min = pd.rolling_min(price, lookback, min_periods=min(len(price), np.ceil(lookback/2.0)))


roll_mean = (roll_max+roll_min)/2.0

all=pd.concat([price, roll_max, roll_mean,roll_min], axis=1)
all.columns=["price", "max", "mean", "min"]
all.plot()
legend(loc="top left")
show()


## gives a nice natural scaling
output = 40.0*((price - roll_mean) / (roll_max - roll_min))
