from systems.provided.futures_chapter15.basesystem import *
import pandas as pd
from matplotlib.pyplot import show, plot

system=futures_system()

## 

price=system.data.daily_prices("BTP")
overlay=pd.TimeSeries([float(price.values[-20]), float(price.values[-1])],index=[price.index[-20], price.index[-1]]) 
overlay.columns=['one month return']
ans=pd.concat([price, overlay], axis=1)
ans.sort()
ans.interpolate().plot()
print(ans)
show()

from systems.forecasting import TradingRule
from syscore.pdutils import divide_df_single_column

def trading_rule_func(price, volatility, lookback):
    ans=divide_df_single_column(price - price.shift(lookback), volatility, ffill=(False, True))
    
    return ans
    

draw_a_line=TradingRule(trading_rule_func, ["rawdata.get_daily_prices","rawdata.daily_returns_volatility"], other_args=dict(lookback=20))

system=futures_system(trading_rules=dict(draw20=draw_a_line))
