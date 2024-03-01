"""
This little utility allows you to keep up with your various sets of instruments, basically designed for those that add a
big load of instruments in one go as is my wont

"""
import pandas as pd
from syscore.interactive.progress_bar import progressBar
from sysproduction.data.prices import diagPrices


diag_prices = diagPrices()

all_instruments_with_prices = diag_prices.get_list_of_instruments_with_contract_prices()
all_instruments_with_prices.sort()

## check for high correlations, likely to be repeats


def check_for_high_correlations():

    checked=[]
    all_dups = []
    returns = dict()
    p =progressBar((len(all_instruments_with_prices)**2)/2)
    for instrument1 in all_instruments_with_prices:
        if instrument1 not in returns.keys():
            returns[instrument1] = weekly_perc_returns_last_year(instrument1)
        for instrument2 in all_instruments_with_prices:
            if instrument1==instrument2:
                continue
            if (instrument2, instrument1) in checked:
                continue
            checked.append((instrument1, instrument2))
            if instrument2 not in returns.keys():
                returns[instrument2] = weekly_perc_returns_last_year(instrument2)

            ret1 = returns[instrument1]
            ret2 = returns[instrument2]
            both = pd.concat([ret1, ret2], axis=1)
            both.columns=['1','2']
            both = both.dropna()
            corr = both.corr()['1']['2']
            if corr>0.9:
                all_dups.append("Possible duplicates %s %s corr %.3f" % (instrument1,
                                                     instrument2, corr))
                print(all_dups)

            p.iterate()

    return all_dups

def weekly_perc_returns_last_year(instrument_code):
    weekly_prices = diag_prices.get_adjusted_prices(instrument_code).resample("1W").ffill()
    weekly_prices_last_year=weekly_prices[-52:]
    return (weekly_prices_last_year/ weekly_prices_last_year.shift(1))-1
