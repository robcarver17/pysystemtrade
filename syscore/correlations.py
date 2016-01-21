'''
Correlations are important and used a lot
'''
import numpy as np
import pandas as pd

from copy import copy

from syscore.genutils import str2Bool
from syscore.dateutils import generate_fitting_dates, fit_dates_object

def nearPSD(A,epsilon=0):
    """
    Find the nearest PSD matrix to A
    
    http://www.quarchome.org/correlationmatrix.pdf 
    via http://stackoverflow.com/questions/10939213/how-can-i-calculate-the-nearest-positive-semi-definite-matrix

    :param A: matrix
    :type A: Square 2-dim np.array

    :param epsilon: control error on nearest
    :type epsilon: float

    :returns: Square 2-dim np.array

    
    """ 
        
    n = A.shape[0]
    eigval, eigvec = np.linalg.eig(A)
    val = np.matrix(np.maximum(eigval,epsilon))
    vec = np.matrix(eigvec)
    T = 1/(np.multiply(vec,vec) * val.T)
    T = np.matrix(np.sqrt(np.diag(np.array(T).reshape((n)) )))
    B = T * vec * np.diag(np.array(np.sqrt(val)).reshape((n)))
    out = B*B.T
    
    return(out)

def group_dict_from_natural(dict_group):
    """
    If we're passed a natural grouping dict (eg dict(bonds=["US10", "KR3", "DE10"], equity=["SP500"])) 
    Returns the dict optimised for algo eg dict(US10=["KR3", "DE10"], SP500=[], ..)

    :param dict_group: dictionary of groupings
    :type dict_group: dict

    :returns: dict

    
    >>> a=dict(bonds=["US10", "KR3", "DE10"], equity=["SP500"])
    >>> group_dict_from_natural(a)['KR3']
    ['US10', 'DE10']
    """
    if len(dict_group)==0:
        return dict()
    
    all_names=list(set(sum([dict_group[groupname] for groupname in dict_group.keys()], [])))
    all_names.sort()
    
    def _return_without(name, group):
        if name in group:
            g2=copy(group)
            g2.remove(name)
            return g2
        else:
            return None

    def _return_group(name, dict_group):
        ans=[_return_without(name, dict_group[groupname]) for groupname in dict_group.keys()]
        ans=[x for x in ans if x is not None]
        if len(ans)==0:
            return []
        
        ans=ans[0]
        return ans
    
    gdict=dict([(name, _return_group(name, dict_group)) for name in all_names])
    
    return gdict

def clean_correlation(corrmat, corr_with_no_data, column_names, must_haves, group_dict):
    """
    Make's sure we *always* have some kind of correlation matrix
    
    If corrmat is all nans, return corr_with_no_data
    
    FIX ME - OTHER STUFF FOR FUTURE PROOFING

    :param corrmat: The correlation matrix to clea
    :type corrmat: 2-dim square np.array

    :param corr_with_no_data: The correlation matrix to use if this one all nans
    :type corr_with_no_data: 2-dim square np.array

    :param column_names: The column labels for the matrix
    :type column_names: List of str

    :param must_haves: Columns we must have data for
    :type must_haves: List of str

    :param group_dict: dictionary of groupings; used to replace missing values
    :type group_dict: dict

    :returns: 2-dim square np.array

    
    """
    ### 
    if not np.any(np.isnan(corrmat)):
        ## no cleaning required
        return corrmat

    if np.all(np.isnan(corrmat)):
        ## this guy guaranteed to be PSD
        return corr_with_no_data
    
    raise Exception("Can't handle incomplete matrix! Need to write code for this")
    
    ## If we're filling in need to get to nearest PSD
    corrmat=nearPSD(corrmat)
    
    
    
    return corrmat


def correlation_single_period(data_for_estimate, corr_with_no_data, must_haves=[], group_dict=dict(),
                              cleaning=True, 
                              using_exponent=True, min_periods=20, ew_lookback=250):
    """
    We generate a correlation from eithier a pd.DataFrame, or a list of them if we're pooling
    
    It's important that forward filling, or index / ffill / diff has been done before we begin
    
    also that we're on the right time frame, eg weekly if that's what we're doing
    
    :param data_for_estimate: Data to get correlations from
    :type data_for_estimate: pd.DataFrame

    :param corr_with_no_data: The correlation matrix to use if this one all nans
    :type corr_with_no_data: 2-dim square np.array

    :param must_haves: Columns we must have data for
    :type must_haves: List of str

    :param group_dict: dictionary of groupings; used to replace missing values
    :type group_dict: dict

    :param using_exponent: Should we use exponential weighting?
    :type using_exponent: bool 

    :param ew_lookback: Lookback, in periods, for exp. weighting
    :type ew_lookback: int 

    :param min_periods: Minimum periods before we get a correlation
    :type min_periods: int 

    :param cleaning: Should we clean the matrix so it always has a value?
    :type cleaning: bool 

    :returns: 2-dim square np.array

    
    """
    ## These may come from config as str
    using_exponent=str2Bool(using_exponent)
    
    if type(data_for_estimate) is list:
        ## pooled
        ## stack everything up
        data_for_estimate=pd.concat(data_for_estimate, axis=0)
        data_for_estimate=data_for_estimate.sort_index()
        
    if using_exponent:
        ## If we stack there will be duplicate dates
        ## So we massage the span so it's correct
        ## This assumes the index is at least daily and on same timestamp
        ## This is an artifact of how we prepare the data
        dindex=data_for_estimate.index
        dlenadj=float(len(dindex))/len(set(list(dindex)))
        ## Usual use for IDM, FDM calculation when whole data set is used
        corrmat=pd.ewmcorr(data_for_estimate, span=int(ew_lookback*dlenadj), min_periods=min_periods)
        
        ## only want the final one
        corrmat=corrmat.values[-1]
    else:
        ## Use normal correlation
        ## Usual use for bootstrapping when only have sub sample
        corrmat=data_for_estimate.corr(min_periods=min_periods)
        corrmat=corrmat.values
    
    ## must_haves: filling in values with average using group_dict
    # use corr_with_no_data if completely empty
    if cleaning:
        corrmat=clean_correlation(corrmat, corr_with_no_data, data_for_estimate.columns, must_haves, group_dict)
    
    return corrmat

def must_have_item(slice_data):
    """
    Returns the columns of slice_data for which we have at least one non nan value  
    
    :param slice_data: Data to get correlations from
    :type slice_data: pd.DataFrame

    :returns: list of str

    """
        
    def _any_data(xseries):
        data_present=[not np.isnan(x) for x in xseries]
        
        return any(data_present)
    
    some_data=slice_data.apply(_any_data, axis=0)
    some_data_names=list(some_data.index)
    some_data_flags=list(some_data.values)
    
    return [name for name,flag in zip(some_data_names, some_data_flags) if flag]

def boring_corr_matrix(size, offdiag=0.99, diag=1.0):
    size_index=range(size)
    def _od(offdag, i, j):
        if i==j:
            return diag
        else:
            return offdiag
    m= [[_od(offdiag, i,j) for i in size_index] for j in size_index]
    m=np.array(m)
    return m

class CorrelationList(object):
    '''
    A correlation list is a list of correlations, packed in with date information about them
    
    '''


    def __init__(self, corr_list, column_names, fit_dates):
        """
        Returns a time series of forecasts for a particular instrument

        :param instrument_code:
        :type str:

        :param rule_variation_list:
        :type list: list of str to get forecasts for, if None uses get_trading_rule_list

        :returns: TxN pd.DataFrames; columns rule_variation_name

        """
        
        setattr(self, "corr_list", corr_list)
        setattr(self, "columns", column_names)
        setattr(self, "fit_dates", fit_dates)
     
        
    def __repr__(self):
        return "%d correlation estimates for %s" % (len(self.corr_list), ",".join(self.columns))
    

class CorrelationEstimator(CorrelationList):
    '''
    
    We generate a correlation list from eithier a pd.DataFrame, or a list of them if we're pooling
    
    The default is to generate correlations annually, from weekly
    
    It's important that forward filling, or index / ffill / diff has been done before we begin

    
    '''


    def __init__(self, data, frequency="W", date_method="expanding", rollyears=20, 
                 dict_group=dict(), boring_offdiag=0.99, cleaning=True, **kwargs):
        """
    
        We generate a correlation from eithier a pd.DataFrame, or a list of them if we're pooling
        
        Its important that forward filling, or index / ffill / diff has been done before we begin
                
        :param data: Data to get correlations from
        :type data: pd.DataFrame
    
        :param frequency: Downsampling frequency. Must be "D", "W" or bigger
        :type frequency: str

        :param date_method: Method to pass to generate_fitting_dates 
        :type date_method: str
    
        :param roll_years: If date_method is "rolling", number of years in window
        :type roll_years: int
    
        :param dict_group: dictionary of groupings; used to replace missing values
        :type dict_group: dict
    
        :param boring_offdiag: Value used in creating 'boring' matrix, for when no data
        :type boring_offdiag: float 
    
        :param **kwargs: passed to correlation_single_period
        
        :returns: CorrelationList
        """

        cleaning=str2Bool(cleaning)
    
        if type(data) is list:
            ## pooled estimate
            pooled=True
        else:
            pooled=False
        
        ## grouping dictionary, convert to faster, algo friendly, form
        group_dict=group_dict_from_natural(dict_group)
        
        if pooled:
            data=[data_item.resample(frequency, how="last") for data_item in data]
            column_names=list(set(sum([list(data_item.columns) for data_item in data],[])))
            column_names.sort()
            ## ensure all are properly aligned
            ## note we don't check that all the columns match here
            data=[data_item[column_names] for data_item in data]
        else:
            data=data.resample(frequency, how="last")
            column_names=data.columns
            
        ### Generate time periods
        fit_dates = generate_fitting_dates(data, date_method=date_method, rollyears=rollyears)

        size=len(column_names)
        corr_with_no_data=boring_corr_matrix(size, offdiag=boring_offdiag)
        
        ## create a list of correlation matrices
        corr_list=[]
        
        ## Now for each time period, estimate correlation
        for fit_period in fit_dates:
            
            if fit_period.no_data:
                ## no data to fit with
                if cleaning:
                    corr_list.append(corr_with_no_data)
                    continue
                else:
                    corr_with_nan=boring_corr_matrix(size, offdiag=np.nan, diag=np.nan)
                    corr_list.append(corr_with_nan)
                    continue
            
            ### Generate 'must have'
            ### note when we use the correlation code for fitting the 'must haves' will come in seperately
            ###  because if we're bootstrapping could be completely different periods
            if pooled:
                ## slice each one individually
                slice_data=[dataitem[fit_period.period_start:fit_period.period_end] 
                            for dataitem in data]
                
                ## 'must have' will be superset of what we need for each individual thing
                must_haves_list=[must_have_item(slice_data_item) 
                                 for slice_data_item in slice_data]
                must_haves=list(set(sum(must_haves_list,[])))
                
                data_for_estimate=[dataitem[fit_period.fit_start:fit_period.fit_end] 
                                   for dataitem in data]
                
            else:
                ## not pooled
                slice_data=data[fit_period.period_start:fit_period.period_end]
                must_haves=must_have_item(slice_data)
                data_for_estimate=data[fit_period.fit_start:fit_period.fit_end]
            
            corrmatrix=correlation_single_period(data_for_estimate, 
                                                 corr_with_no_data,
                                                 must_haves=must_haves, 
                                                 group_dict=group_dict,
                                                 cleaning=cleaning,
                                                 **kwargs)
        
            corr_list.append(corrmatrix)
        
        setattr(self, "corr_list", corr_list)
        setattr(self, "columns", column_names)
        setattr(self, "fit_dates", fit_dates)
        
        
if __name__ == '__main__':
    import doctest
    doctest.testmod()
