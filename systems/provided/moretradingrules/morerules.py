import pandas as pd

def breakout(price, lookback):
    """
    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.DataFrame

    :param lookback: Lookback in days
    :type lookback: int

    :returns: pd.DataFrame -- unscaled, uncapped forecast

    """
    roll_max = pd.rolling_max(price, lookback, min_periods=min(len(price), int(lookback/2)))
    roll_min = pd.rolling_min(price, lookback, min_periods=min(len(price), int(lookback/2)))
    
    roll_mean = (roll_max+roll_min)/2.0

    ## gives a nice natural scaling
    output = 40.0*((price - roll_mean) / (roll_max - roll_min))
    smoothed_output = pd.ewma(output, span=max(int(lookback/4.0), 1), min_periods=int(lookback/8.0))

    return smoothed_output

