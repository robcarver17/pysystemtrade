from systems.provided.futures_chapter15.basesystem import futures_system
from copy import copy
from pickle import dump, load

base_system=futures_system()
base_config = base_system.config
## run all possible combinations of TF to get base performance

instruments = base_system.get_instrument_list()

results = dict()
wlist = [1,2,3,4,5,6,7,8,9,10,15,20,25,30,35,40,45,50,60,70,80,90,100,125,150,175,200,250]
#wlist = [1,250]

instrument_list = base_system.get_instrument_list()

from syscore.genutils import progressBar
thing=progressBar(len(wlist)*len(wlist)*len(instrument_list))

for Aspeed in wlist:
    for Bspeed in wlist:

        if Aspeed==Bspeed:
            continue

        config=copy(base_config)
        trading_rules = dict(rule=dict(function='systems.provided.futures_chapter15.rules.ewmac', data=['rawdata.get_daily_prices', 'rawdata.daily_returns_volatility'
        ], other_args=dict(Lfast=Aspeed, Lslow=Bspeed)))

        config.trading_rules = trading_rules
        config.use_forecast_scale_estimates = True

        new_system=futures_system(config=config)

        for instrument in instrument_list:
            results_key = (Aspeed, Bspeed, instrument)
            acc=new_system.accounts.pandl_for_instrument_forecast(instrument, "rule").gross.as_ts()

            results[results_key]=acc
            thing.iterate()

f = open('/home/rob/results.pck', "wb")
dump(results, f)
f.close()

