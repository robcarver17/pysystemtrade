"""
Utilities to help with pandas
"""

import pandas as pd
import numpy as np
from syscore.fileutils import get_pathname_for_package
import os

def pd_readcsv_frompackage(package_name, filename, path=[""]):
    """
    Run pd_readcsv on a file in python with optional paths eg path=['path',path2', ...]
    package_name(/path1/path2.., filename

    :param package_name: Name of a package eg syscore that contains
    :type package_name: str

    :param filename: Filename with extension
    :type filename: str

    :param path: List of paths to complete full path structure
    :type path: list of str
    
    
    :returns: pd.DataFrame
    
    >>> pd_readcsv_frompackage("syscore", "pricetestdata.csv", path=["tests"]).tail(1)
                    ADJ
    2015-04-22  159.225
    """
    
    pathname=get_pathname_for_package(package_name, path)
    full_filename= os.path.join(pathname,  filename)
    return pd_readcsv(full_filename)

def pd_readcsv(filename, date_index_name="DATETIME"):
    """ 
    Reads a pandas data frame, with time index labelled 
    package_name(/path1/path2.., filename

    :param filename: Filename with extension
    :type filename: str

    :param date_index_name: Column name of date index
    :type date_index_name: list of str
    
    
    :returns: pd.DataFrame
    
    >>> pd.read_csv("tests/pricetestdata.csv").tail(1)
                    ADJ
    2015-04-22  159.225
    """
    
    ans=pd.read_csv(filename)
    ans.index=pd.to_datetime(ans[date_index_name]).values
    
    del ans[date_index_name]
    
    ans.index.name=None

    return ans

def apply_cap(pd_dataframe, capvalue):
    """
    Applies a cap to the values in a Tx1 pandas dataframe

    :param pd_dataframe: Tx1 pandas data frame
    :type pd_dataframe: pd.DataFrame

    :param capvalue: Maximum absolute value allowed
    :type capvlue: int or float
    
    
    :returns: pd.DataFrame Tx1
    
    >>> x=pd.DataFrame(dict(a=[2.0, 7.0, -7.0, -6.99]), pd.date_range(pd.datetime(2015,1,1), periods=4))
    >>> apply_cap(x, 5.0)
                0
    2015-01-01  2
    2015-01-02  5
    2015-01-03 -5
    2015-01-04 -5
    
    """
    pd.date_range
    ## Will do weird things otherwise
    assert capvalue>0
    
    ## create max and min columns    
    max_ts=pd.Series([capvalue]*pd_dataframe.shape[0], pd_dataframe.index)
    min_ts=pd.Series([-capvalue]*pd_dataframe.shape[0], pd_dataframe.index)
    
    joined_ts=pd.concat([pd_dataframe, max_ts], axis=1)
    joined_ts=joined_ts.min(axis=1)
    joined_ts=pd.concat([joined_ts, min_ts], axis=1)
    joined_ts=joined_ts.max(axis=1).to_frame()
    
    joined_ts[np.isnan(pd_dataframe)]=np.nan
    return joined_ts

def divide_df(x,y):
    """
    Divide Tx1 dataframe by Tx1 dataframe

    :param x: Tx1 pandas data frame
    :type x: pd.DataFrame

    :param y: Tx1 pandas data frame
    :type y: pd.DataFrame
    
    :returns: pd.DataFrame Tx1
    
    >>> x=pd.DataFrame(dict(a=[2.0, 7.0, -7.0, -7.00]), pd.date_range(pd.datetime(2015,1,1), periods=4))
    >>> y=pd.DataFrame(dict(b=[2.0, 3.5, 2.0, -3.5]), pd.date_range(pd.datetime(2015,1,1), periods=4))
    
                  a
    2015-01-01  1.0
    2015-01-02  2.0
    2015-01-03 -3.5
    2015-01-04  2.0
   
    
    """
    ans=x.iloc[:,0]/y.iloc[:,0]
    ans=ans.to_frame()
    ans.columns=[x.columns[0]]
    
    return ans

if __name__ == '__main__':
    import doctest
    doctest.testmod()