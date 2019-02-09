from systems.provided.futures_chapter15.basesystem import *
sys = futures_system()
config = sys.config
del(config.instrument_weights) # ensures all instruments are used equally weighted
config.forecast_weights=dict(ewmac16_64=0.333, ewmac32_128=0.333, ewmac64_256=0.3333)
config.use_forecast_div_mult_estimates=True
config.use_instrument_div_mult_estimates=True
config.use_forecast_scale_estimates=False
system = futures_system(config=config)
acc = system.accounts.portfolio()

# for some account
# rolling window

from scipy.stats import ttest_1samp

# dull wrapper function as pandas apply functions have to return a float
def ttest_series(xseries):
    return ttest_1samp(xseries, 0.0).statistic

## given some account curve of monthly returns this will return the series of t-statistics
acc.rolling(24).apply(ttest_series)

axhline(y=2.032, color="red")