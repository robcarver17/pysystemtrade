 

Here is a whistlestop tour of what pysystemtrade can currently do. 

# A simple trading rule

As systematic traders we believe that the future will be at least a bit like the past. So first of all we need some past data. In principle past data can come from many places, but to begin with we'll get it from some pre-baked .csv files: 

```python
from sysdata.csvdata import csvFuturesData
data=csvFuturesData()
data
```

```
FuturesData object with 38 instruments
```

What instruments have we got?

```python
data.get_instrument_list()
```

```
['CORN', 'LEANHOG', 'LIVECOW', 'SOYBEAN', 'WHEAT', 'KR10', 'KR3', 'BOBL', 'BTP', 'BUND', 'OAT', 'SHATZ', 'US10', 'US2', 'US20', 'US5', 'V2X', 'VIX', 'KOSPI', 'AEX', 'CAC', 'SMI', 'NASDAQ', 'SP500', 'AUD', 'EUR', 'GBP', 'JPY', 'MXP', 'NZD', 'COPPER', 'GOLD', 'PALLAD', 'PLAT', 'CRUDE_W', 'GAS_US', 'EDOLLAR', 'EUROSTX']
```

And what kind of data can we get for them?

```python
data.get_instrument_price("EDOLLAR").tail(5)
```

```
              price
2015-04-16  97.9350
2015-04-17  97.9400
2015-04-20  97.9250
2015-04-21  97.9050
2015-04-22  97.8325
```

This is old data, but it's sufficient for playing with.  

*I'll update the data at some point, as well as including methods for you to get your own data*

*Technical note: This is the 'back-adjusted' price for the future, formed from stiching adjacent contracts together using the 'panama' method*

**data** objects behave a bit like dicts (though they don't formally inherit from them). So these both work:

```python
data.keys() ## equivalent to data.get_instrument_list
data['SP500'] ## equivalent to data.get_instrument_price
```

Price data is useful, but is there any other data available? For futures, yes, we can get the data we need to implement a carry rule:

```python
data.get_instrument_raw_carry_data("US10").tail(5)
```

```
                 PRICE       CARRY CARRY_CONTRACT PRICE_CONTRACT
2015-04-16  129.250000  129.656250         201509         201506
2015-04-17  129.437500  129.718750         201509         201506
2015-04-20  129.109375  129.562500         201509         201506
2015-04-21  129.000000  129.390625         201509         201506
2015-04-22         NaN  128.867188         201509         201506
```

Let's create a simple trading rule. 


```python

import pandas as pd
from syscore.algos import robust_vol_calc
from syscore.pdutils import divide_df_single_column

def calc_ewmac_forecast(price, Lfast, Lslow=None):
    
    
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback
    
    Assumes that 'price' is daily data
    """
    ## price: This is the stitched price series
    ## We can't use the price of the contract we're trading, or the volatility will be jumpy
    ## And we'll miss out on the rolldown. See http://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html

    if Lslow is None:
        Lslow=4*Lfast
    
    ## We don't need to calculate the decay parameter, just use the span directly
    
    fast_ewma=pd.ewma(price, span=Lfast)
    slow_ewma=pd.ewma(price, span=Lslow)
    raw_ewmac=fast_ewma - slow_ewma
    
    vol=robust_vol_calc(price.diff())    
    
    return divide_df_single_column(raw_ewmac, vol)

```
Let's run it and look at the output

```python
instrument_code='EDOLLAR'
price=data.get_instrument_price(instrument_code)
ewmac=calc_ewmac_forecast(price, 4, 16)
ewmac.tail(5)

from matplotlib.pyplot import show
ewmac.plot()
show()
```

```
               price
2015-04-16  0.919245
2015-04-17  1.003627
2015-04-20  0.939076
2015-04-21  0.768698
2015-04-22  0.268149
```

Did we make any money?

```python
from syscore.accounting import pandl
account=pandl(price, forecast=ewmac)

## Get the sharpe ratio (annualised, based on daily returns)
account.sharpe()
```

```

account.curve().plot() ## plot the cumulative account curve
```


Looks like we did. **account**, by the way inherits from a pandas data frame. Here are some other things we can do with it:

```



