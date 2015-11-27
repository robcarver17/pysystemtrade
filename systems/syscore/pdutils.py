"""
Utilities to help with pandas
"""

import pandas as pd
import numpy as np

def pd_readcsv(filename):
    """
    Reads the pandas dataframe from a filename, given the index is correctly labelled
    """

    
    ans=pd.read_csv(filename)
    
    ans.index=pd.to_datetime(ans['DATETIME'])
    del ans['DATETIME']
    ans.index.name=None
    return ans

def apply_cap(pddataframe, capvalue):
    """
    Applies a cap to the values in a Tx1 pandas dataframe
    """

    ## Will do weird things otherwise

    assert capvalue>0
    max_ts=pd.Series([capvalue]*pddataframe.shape[0], pddataframe.index)
    min_ts=pd.Series([-capvalue]*pddataframe.shape[0], pddataframe.index)
    
    joined_ts=pd.concat([pddataframe, max_ts], axis=1)
    joined_ts=joined_ts.min(axis=1)
    joined_ts=pd.concat([joined_ts, min_ts], axis=1)
    joined_ts=joined_ts.max(axis=1).to_frame()
    
    joined_ts[np.isnan(pddataframe)]=np.nan
    return joined_ts