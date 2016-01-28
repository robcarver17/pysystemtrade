"""
Utilities to help with pandas
"""

import pandas as pd
import numpy as np
from syscore.fileutils import get_filename_for_package

def df_from_list(data):
    """
    data frame from list
    """
    if type(data) is list:        
        column_names=list(set(sum([list(data_item.columns) for data_item in data],[])))
        column_names.sort()
        ## ensure all are properly aligned
        ## note we don't check that all the columns match here
        data=[data_item[column_names] for data_item in data]
    
        ## pooled
        ## stack everything up
        data=pd.concat(data, axis=0)
        data=data.sort_index()
            
    return data


def must_haves_from_list(data):
    must_haves_list=[must_have_item(data_item) 
                     for data_item in data]
    must_haves=list(set(sum(must_haves_list,[])))
    
    return must_haves


def must_have_item(slice_data):
    """
    Returns the columns of slice_data for which we have at least one non nan value  
    
    :param slice_data: Data to get correlations from
    :type slice_data: pd.DataFrame

    :returns: list of bool

    >>>
    """
        
    def _any_data(xseries):
        data_present=[not np.isnan(x) for x in xseries]
        
        return any(data_present)
    
    some_data=slice_data.apply(_any_data, axis=0)
    some_data_flags=list(some_data.values)
    
    return some_data_flags

def pd_readcsv_frompackage(filename):
    """
    Run pd_readcsv on a file in python

    :param args: List showing location in project directory of file eg systems, provided, tests.csv
    :type args: str

    :returns: pd.DataFrame

    """

    full_filename = get_filename_for_package(filename)
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

    """

    ans = pd.read_csv(filename)
    ans.index = pd.to_datetime(ans[date_index_name]).values

    del ans[date_index_name]

    ans.index.name = None

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
                a
    2015-01-01  2
    2015-01-02  5
    2015-01-03 -5
    2015-01-04 -5

    """
    pd.date_range
    # Will do weird things otherwise
    assert capvalue > 0

    # create max and min columns
    max_ts = pd.Series([capvalue] * pd_dataframe.shape[0], pd_dataframe.index)
    min_ts = pd.Series([-capvalue] * pd_dataframe.shape[0], pd_dataframe.index)

    joined_ts = pd.concat([pd_dataframe, max_ts], axis=1)
    joined_ts = joined_ts.min(axis=1)
    joined_ts = pd.concat([joined_ts, min_ts], axis=1)
    joined_ts = joined_ts.max(axis=1).to_frame(pd_dataframe.columns[0])

    joined_ts[np.isnan(pd_dataframe)] = np.nan
    return joined_ts

def align_to_joint(x,y, ffill):
    """
    Align x and y to their joint index
    
    
    
    :param x: Tx1 pandas data frame
    :type x: pd.DataFrame

    :param y: Tx1 pandas data frame
    :type y: pd.DataFrame

    :param ffill: should we ffill x and y respectively
    :type ffill: 2-tuple (bool, bool)
    
    """
    jointindex=list(set(list(x.index)+list(y.index) ))
    
    x=x.reindex(jointindex)
    y=y.reindex(jointindex)
    
    (ffill_x, ffill_y) = ffill
    
    if ffill_x:
        x=x.ffill()
    
    if ffill_y:
        y=y.ffill()
    
    return (x,y)

def index_match(x, y, ffill):
    """
    Join together two pd.DataFrames into a 2xT

    timestamps don't have to match
    The tuple ffill determines if we fill one, or the other before joining

    :param x: Tx1 pandas data frame
    :type x: pd.DataFrame

    :param y: Tx1 pandas data frame
    :type y: pd.DataFrame

    :param ffill: should we ffill x and y respectively
    :type ffill: 2-tuple (bool, bool)

    :returns: pd.DataFrame Tx2
    """

    (ffill_x, ffill_y) = ffill

    ans = pd.concat([x, y], axis=1, join='inner')

    if ffill_x or ffill_y:

        jointts = ans.index

        if ffill_x:
            xnew = x.ffill().reindex(jointts)
        else:
            xnew = x.reindex(jointts)

        if ffill_y:
            ynew = y.ffill().reindex(jointts)
        else:
            ynew = y.reindex(jointts)

        ans = pd.concat([xnew, ynew], axis=1)

    return ans


def divide_df_single_column(x, y, ffill=(False, False)):
    """
    Divide Tx1 dataframe by Tx1 dataframe

    timestamps don't have to match
    The tuple ffill determines if we fill before dividing

    :param x: Tx1 pandas data frame
    :type x: pd.DataFrame

    :param y: Tx1 pandas data frame
    :type y: pd.DataFrame

    :param ffill: should we ffill x and y respectively
    :type ffill: 2-tuple (bool, bool)

    :returns: pd.DataFrame Tx1

    >>> x=pd.DataFrame(dict(a=[2.0, 7.0, -7.0, -7.00]), pd.date_range(pd.datetime(2015,1,1), periods=4))
    >>> y=pd.DataFrame(dict(b=[2.0, 3.5, 2.0, -3.5]), pd.date_range(pd.datetime(2015,1,1), periods=4))
    >>> divide_df_single_column(x,y)
                  a
    2015-01-01  1.0
    2015-01-02  2.0
    2015-01-03 -3.5
    2015-01-04  2.0


    """
    ans = index_match(x, y, ffill)

    ans = ans.iloc[:, 0] / ans.iloc[:, 1]
    ans = ans.to_frame(x.columns[0])

    return ans


def multiply_df_single_column(x, y, ffill=(False, False)):
    """
    Multiply Tx1 dataframe by Tx1 dataframe; time indicies don't have to match

    :param x: Tx1 pandas data frame
    :type x: pd.DataFrame

    :param y: Tx1 pandas data frame
    :type y: pd.DataFrame

    :returns: pd.DataFrame Tx1

    >>> x=pd.DataFrame(dict(a=range(10)), pd.date_range(pd.datetime(2015,1,1), periods=10))
    >>> y=pd.DataFrame(dict(b=range(10)), pd.date_range(pd.datetime(2015,1,5), periods=10))
    >>> multiply_df_single_column(x,y)
                 a
    2015-01-05   0
    2015-01-06   5
    2015-01-07  12
    2015-01-08  21
    2015-01-09  32
    2015-01-10  45

    """

    ans = index_match(x, y, ffill)

    ans = ans.iloc[:, 0] * ans.iloc[:, 1]
    ans = ans.to_frame(x.columns[0])

    return ans


def multiply_df(x, y):
    """
    Multiply TxN dataframe by TxN dataframe

    :param x: Tx1 pandas data frame
    :type x: pd.DataFrame

    :param y: Tx1 pandas data frame
    :type y: pd.DataFrame

    :returns: pd.DataFrame Tx1

    >>> x=pd.DataFrame(dict(a=[2.0, 7.0, -7.0, -7.00]), pd.date_range(pd.datetime(2015,1,1), periods=4))
    >>> y=pd.DataFrame(dict(b=[2.0, 3.0, 2.0, -3.0]), pd.date_range(pd.datetime(2015,1,1), periods=4))
    >>> multiply_df(x,y)
                 a
    2015-01-01   4
    2015-01-02  21
    2015-01-03 -14
    2015-01-04  21
    >>>
    >>> x=pd.DataFrame(dict(a=[2.0, 7.0],b=[ -7.0, -7.00]), pd.date_range(pd.datetime(2015,1,1), periods=2))
    >>> y=pd.DataFrame(dict(c=[-2.0, 2.0],d=[ -3.0, -3.00]), pd.date_range(pd.datetime(2015,1,1), periods=2))
    >>> multiply_df(x,y)
                 a   b
    2015-01-01  -4  21
    2015-01-02  14  21

    """

    assert x.shape == y.shape
    ans = pd.concat([x.iloc[:, cidx] * y.iloc[:, cidx]
                     for cidx in range(x.shape[1])], axis=1)
    ans.columns = x.columns

    return ans


def fix_weights_vs_pdm(weights, pdm):
    """
    Take a matrix of weights and positions/forecasts (pdm)

    Ensure that the weights in each row add up to 1, for active positions/forecasts (not np.nan values after forward filling)

    This deals with the problem of different rules and/or instruments having different history

    :param weights: Weights to
    :type weights: TxK pd.DataFrame (same columns as weights, perhaps different length)

    :param pdm:
    :type pdm: TxK pd.DataFrame (same columns as weights, perhaps different length)

    :returns: TxK pd.DataFrame of adjusted weights

    """

    # forward fill forecasts/positions
    pdm_ffill = pdm.ffill()

    # resample weights
    adj_weights = weights.reindex(pdm_ffill.index, method='ffill')

    # ensure columns are aligned
    adj_weights = adj_weights[pdm.columns]

    # remove weights if nan forecast
    adj_weights[np.isnan(pdm_ffill)] = 0.0

    # change rows so weights add to one
    def _sum_row_fix(weight_row):
        swr = sum(weight_row)
        if swr == 0.0:
            return weight_row
        new_weights = weight_row / swr
        return new_weights

    adj_weights = adj_weights.apply(_sum_row_fix, 1)

    return adj_weights


def drawdown(x):
    """
    Returns a ts of drawdowns for a time series x

    :param x: account curve (cumulated returns)
    :param x: pd.DataFrame or Series

    :returns: pd.DataFrame or Series
    """
    maxx = pd.rolling_max(x, 99999999, min_periods=1)
    return x - maxx


if __name__ == '__main__':
    import doctest
    doctest.testmod()
