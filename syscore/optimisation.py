'''
Created on 21 Jan 2016

@author: rob
'''

import pandas as pd
import numpy as np
import datetime
from scipy.optimize import minimize
from copy import copy
import random

from syscore.algos import vol_estimator, mean_estimator
from syscore.correlations import correlation_single_period, boring_corr_matrix
from syscore.dateutils import generate_fitting_dates, BUSINESS_DAYS_IN_YEAR, WEEKS_IN_YEAR, MONTHS_IN_YEAR
from syscore.genutils import str2Bool
from syscore.pdutils import df_from_list, must_have_item
from syscore.objects import resolve_function
from syslogdiag.log import logtoscreen

class GenericOptimiser(object):

    def __init__(self, data, log=logtoscreen("optimiser"), frequency="W", date_method="expanding", 
                         rollyears=20, fit_method="bootstrap", cleaning=True,
                         **passed_params):
        
        """
    
        Optimise weights over some returns data
        
        :param data: Returns data
        :type data: pd.DataFrame or list if pooling
    
        :param frequency: Downsampling frequency. Must be "D", "W" or bigger
        :type frequency: str
    
        :param date_method: Method to pass to generate_fitting_dates 
        :type date_method: str
    
        :param roll_years: If date_method is "rolling", number of years in window
        :type roll_years: int
    
        :param fit_method: Method used for fitting, one of 'bootstrap', 'shrinkage', 'one_period'
        :type fit_method: str
    
        :param cleaning: Should we clean correlations so can use incomplete data?
        :type cleaning: bool
    
        :param *_estimate_params: dicts of **kwargs to pass to moments estimation, and optimisation functions
        
        :returns: pd.DataFrame of weights
        """
        cleaning=str2Bool(cleaning)
        optimise_params=copy(passed_params)
        
        ## A moments estimator works out the mean, vol, correlation
        moments_estimator=momentsEstimator(optimise_params)

        ## The optimiser instance will do the optimation once we have the appropriate data
        optimiser=optimiserWithParams(optimise_params, moments_estimator)
    
        ## annualisation
        ann_dict=dict(D=BUSINESS_DAYS_IN_YEAR, W=WEEKS_IN_YEAR, M=MONTHS_IN_YEAR, Y=1.0)
        annualisation=ann_dict.get(frequency, 1.0)
    
        ## de-pool pooled data    
        data=df_from_list(data)    
            
        ## resample, indexing before and differencing after (returns, remember)
        data=data.cumsum().resample(frequency, how="last").diff()
    
        ## account for change in frequency
        data=data*annualisation
        
        fit_dates = generate_fitting_dates(data, date_method=date_method, rollyears=rollyears)
        setattr(self, "fit_dates", fit_dates)
    
        ## Now for each time period, estimate weights
        ## create a list of weight vectors
        weight_list=[]
        
        ## create a class object for each period
        opt_results=[]
        
        log.terse("Optimising...")
        
        for fit_period in fit_dates:
            log.msg("Optimising for data from %s to %s" % (str(fit_period.period_start), str(fit_period.period_end)))
            ## Do the optimisation for one period, using a particular optimiser instance
            results_this_period=optSinglePeriod(self, data, fit_period, optimiser, cleaning)

            opt_results.append(results_this_period)

            weights=results_this_period.weights
            
            ## We adjust dates slightly to ensure no overlaps
            dindex=[fit_period.period_start+datetime.timedelta(days=1), 
                    fit_period.period_end-datetime.timedelta(days=1)]
            
            ## create a double row to delineate start and end of test period
            weight_row=pd.DataFrame([weights]*2, index=dindex, columns=data.columns)
            weight_list.append(weight_row)

        ## Stack everything up    
        weight_df=pd.concat(weight_list, axis=0)
        
        setattr(self, "results", opt_results)
        setattr(self, "weights", weight_df)

class momentsEstimator(object):
    def __init__(self, optimise_params):
        """
        Create an object which estimates the moments for a single period of data, according to the parameters

        The parameters we need are popped from the config dict
        
        :param optimise_params: Parameters for optimisation
        :type optimise_params: dict
    
        """
        
        corr_estimate_params=copy(optimise_params["correlation_estimate"])
        mean_estimate_params=copy(optimise_params["mean_estimate"])
        vol_estimate_params=copy(optimise_params["vol_estimate"])

        corr_estimate_func=resolve_function(corr_estimate_params.pop("func"))
        mean_estimate_func=resolve_function(mean_estimate_params.pop("func"))
        vol_estimate_func=resolve_function(vol_estimate_params.pop("func"))

        setattr(self, "corr_estimate_params", corr_estimate_params)
        setattr(self, "mean_estimate_params", mean_estimate_params)
        setattr(self, "vol_estimate_params", vol_estimate_params)
        
        setattr(self, "corr_estimate_func", corr_estimate_func)
        setattr(self, "mean_estimate_func", mean_estimate_func)
        setattr(self, "vol_estimate_func", vol_estimate_func)

    def correlation(self, data_for_estimate):
        params=self.corr_estimate_params
        corrmatrix=self.corr_estimate_func(data_for_estimate, **params)

        return corrmatrix
    
    def means(self, data_for_estimate):
        params=self.mean_estimate_params
        mean_list=self.mean_estimate_func(data_for_estimate, **params)

        return mean_list
    
    def vol(self, data_for_estimate):
        params=self.vol_estimate_params
        stdev_list=self.vol_estimate_func(data_for_estimate, **params)

        return stdev_list

    def moments(self, data_for_estimate):
        ans=(self.means(data_for_estimate), self.correlation(data_for_estimate),  self.vol(data_for_estimate))
        return ans



class optimiserWithParams(object):
    def __init__(self, optimise_params, moments_estimator):
        """
        Create an object which does an optimisation for a single period, according to the parameters
        
        :param optimise_params: Parameters for optimisation. Must contain "method"
        :type optimise_params: dict

        :param moments_estimator: An instance of a moments estimator
        :type optimise_params: momentsEstimator
    
        
        """
        fit_method=optimise_params.pop("method")
        fit_method_dict=dict(one_period=markosolver, bootstrap=bootstrap_portfolio, 
                             shrinkage=opt_shrinkage)

        try:        
            opt_func=fit_method_dict[fit_method]
    
        except KeyError:
            raise Exception("Fitting method %s unknown; try one of: %s " % (fit_method, ", ".join(fit_method_dict.keys())))

        setattr(self, "opt_func", resolve_function(opt_func))
        
        setattr(self, "params", optimise_params)
        
        setattr(self, "moments_estimator", moments_estimator)
        
    def call(self, optimise_data, cleaning, must_haves):
        
        params=self.params
        return self.opt_func(optimise_data, self.moments_estimator, cleaning, must_haves, **params)

class optSinglePeriod(object):
    def __init__(self, parent, data, fit_period, optimiser, cleaning):

        if cleaning:
            ### Generate 'must have' from the period we need
            ###  because if we're bootstrapping could be completely different periods
            current_period_data=data[fit_period.period_start:fit_period.period_end] 
            must_haves=must_have_item(current_period_data)
        
        else:
            must_haves=None

        
        if fit_period.no_data:
            ## no data to fit with
            
            diag=None
            
            size=current_period_data.shape[1]
            weights_with_nan=[np.nan/size]*size
            weights=weights_with_nan

            if cleaning:
                weights=clean_weights(weights, must_haves)
            
        else:
            ## we have data
            subset_fitting_data=data[fit_period.fit_start:fit_period.fit_end]
    

            (weights, diag)=optimiser.call(subset_fitting_data, cleaning, must_haves)
            
        ##
        setattr(self, "diag", diag)
        setattr(self, "weights", weights)



def opt_shrinkage(period_subset_data, moments_estimator,  
                   cleaning, must_haves,
                  shrinkage_SR=.9,
                  shrinkage_corr=.5 , 
                  equalise_vols=False,**ignored_args):
    """
    Given dataframe of returns; returns_to_bs, performs a shrinkage optimisation

    :param subset_data: The data to optimise over
    :type subset_data: pd.DataFrame TxN

    :param cleaning: Should we clean correlations so can use incomplete data?
    :type cleaning: bool

    :param equalise_vols: Set all vols equal before optimising (makes more stable)
    :type equalise_vols: bool

    :param shrinkage_SR: Shrinkage factor to use with SR. 1.0 = full shrinkage
    :type shrinkage_SR: float

    :param shrinkage_corr: Shrinkage factor to use with correlations. 1.0 = full shrinkage
    :type shrinkage_corr: float

    Other arguments are kept so we can use **kwargs with other optimisation functions

    *_params passed through to data estimation functions

    :returns: float
    
    """

    rawmoments=moments_estimator.moments(period_subset_data)    
    (mean_list, corrmatrix, stdev_list)=copy(rawmoments)

    
    ## equalise vols first 
    if equalise_vols:
        (mean_list, stdev_list)=vol_equaliser(mean_list, stdev_list)

    ## shrinkage: 
    mean_list=shrink_SR(mean_list, stdev_list, shrinkage_SR)
    corrmatrix=shrink_corr(corrmatrix, shrinkage_corr)

    ## get sigma matrix back    
    sigma=sigma_from_corr_and_std(stdev_list, corrmatrix)
    
    unclean_weights=optimise( sigma, mean_list)
    
    if cleaning:
        weights=clean_weights(unclean_weights, must_haves)
    else:
        weights=unclean_weights
    
    diag=dict(raw=rawmoments, sigma=sigma, mean_list=mean_list, 
              unclean=unclean_weights, weights=weights)
    
    return (weights, diag)

def get_avg_corr(sigma):
    """
    >>> sigma=np.array([[1.0,0.0,0.5], [0.0, 1.0, 0.75],[0.5, 0.75, 1.0]])
    >>> get_avg_corr(sigma) 
    0.41666666666666669
    >>> sigma=np.array([[1.0,np.nan], [np.nan, 1.0]])
    >>> get_avg_corr(sigma)
    nan
    """
    new_sigma=copy(sigma)
    np.fill_diagonal(new_sigma,np.nan)
    if np.all(np.isnan(new_sigma)):
        return np.nan
    
    avg_corr=np.nanmean(new_sigma)

    return avg_corr

def shrink_corr(corrmatrix, shrinkage_corr):
    """
    >>> sigma=np.array([[1.0,0.0,0.5], [0.0, 1.0, 0.75],[0.5, 0.75, 1.0]]) 
    >>> shrink_corr(sigma, 0.5)
    array([[ 1.        ,  0.20833333,  0.45833333],
           [ 0.20833333,  1.        ,  0.58333333],
           [ 0.45833333,  0.58333333,  1.        ]])
    >>> shrink_corr(sigma, 0.0)
    array([[ 1.  ,  0.  ,  0.5 ],
           [ 0.  ,  1.  ,  0.75],
           [ 0.5 ,  0.75,  1.  ]])
    >>> shrink_corr(sigma, 1.0)
    array([[ 1.        ,  0.41666667,  0.41666667],
           [ 0.41666667,  1.        ,  0.41666667],
           [ 0.41666667,  0.41666667,  1.        ]])
    """
    
    avg_corr=get_avg_corr(corrmatrix)
    prior_corr=boring_corr_matrix(corrmatrix.shape[0], offdiag=avg_corr)

    sigma_corr=shrinkage_corr*prior_corr+(1-shrinkage_corr)*corrmatrix
    
    return sigma_corr

def shrink_SR(mean_list, stdev_list, shrinkage_SR):
    """
    >>> shrink_SR([.0,1.], [1.,2.], .5)
    [0.125, 0.75]
    >>> shrink_SR([np.nan, np.nan], [1.,2.], .5)
    [nan, nan]
    """
    SR_list=[asset_mean/asset_stdev for (asset_mean, asset_stdev) in zip(mean_list, stdev_list)]

    if np.all(np.isnan(SR_list)):
        return [np.nan]*len(mean_list)

    avg_SR=np.nanmean(SR_list)

    post_means=[(shrinkage_SR*avg_SR*asset_stdev)+(1-shrinkage_SR)*asset_mean
                for (asset_mean, asset_stdev) in zip(mean_list, stdev_list)] 

    return post_means



def markosolver(period_subset_data, moments_estimator,
                 cleaning, must_haves,
                  equalise_SR=False , equalise_vols=False,
                  **ignored_args): 
    """
    Returns the optimal portfolio for the returns data
    
    If equalise_SR=True then assumes all assets have SR if False uses the asset natural SR    
    
    If equalise_vols=True then normalises returns to have same standard deviation; the weights returned
       will be 'risk weightings'
       
    :param subset_data: The data to optimise over
    :type subset_data: pd.DataFrame TxN

    :param cleaning: Should we clean correlations so can use incomplete data?
    :type cleaning: bool

    :param must_haves: The indices of things we must have weights for, used for cleaning
    :type must_haves: list of bool


    :param equalise_SR: Set all means equal before optimising (makes more stable)
    :type equalise_SR: bool

    :param equalise_vols: Set all vols equal before optimising (makes more stable)
    :type equalise_vols: bool

    Other arguments are kept so we can use **kwargs with other optimisation functions

    *_params passed through to data estimation functions


    :returns: float
    
    """

    rawmoments=moments_estimator.moments(period_subset_data)    
    (mean_list, corrmatrix, stdev_list)=copy(rawmoments)

    ## equalise vols first 
    if equalise_vols:
        (mean_list, stdev_list)=vol_equaliser(mean_list, stdev_list)
        
    if equalise_SR:
        mean_list=SR_equaliser(mean_list, stdev_list)
    
    sigma=sigma_from_corr_and_std(stdev_list, corrmatrix)
    
    unclean_weights=optimise( sigma, mean_list)
    
    if cleaning:
        weights=clean_weights(unclean_weights, must_haves)
    else:
        weights=unclean_weights
    
    diag=dict(raw=rawmoments, sigma=sigma, mean_list=mean_list, 
              unclean=unclean_weights, weights=weights)
    
    return (weights, diag)

def clean_weights(weights,  must_haves=None, fraction=0.5):
    """
    Make's sure we *always* have some weights where they are needed, by replacing nans
    Allocates fraction of pro-rata weight equally
    
    :param weights: The weights to clean
    :type weights: list of float

    :param must_haves: The indices of things we must have weights for
    :type must_haves: list of bool

    :param fraction: The amount to reduce missing instrument weights by
    :type fraction: float

    :returns: list of float

    >>> clean_weights([1.0, np.nan, np.nan],   fraction=1.0)
    [0.33333333333333337, 0.33333333333333331, 0.33333333333333331]
    >>> clean_weights([0.4, 0.6, np.nan],  fraction=1.0)
    [0.26666666666666672, 0.40000000000000002, 0.33333333333333331]
    >>> clean_weights([0.4, 0.6, np.nan],  fraction=0.5)
    [0.33333333333333337, 0.5, 0.16666666666666666]
    >>> clean_weights([np.nan, np.nan, 1.0],  must_haves=[False,True,True], fraction=1.0)
    [0.0, 0.5, 0.5]
    >>> clean_weights([np.nan, np.nan, np.nan],  must_haves=[False,False,True], fraction=1.0)
    [0.0, 0.0, 1.0]
    >>> clean_weights([np.nan, np.nan, np.nan],  must_haves=[False,False,False], fraction=1.0)
    [0.0, 0.0, 0.0]
    """
    ### 
    if not any(np.isnan(weights)):
        ## no cleaning required
        return weights

    if must_haves is None:
        must_haves=[True]*len(weights)
    
    if not any(must_haves):
        return [0.0]*len(weights)
    
    needs_replacing=[(np.isnan(x) or x==0.0) and must_haves[i] for (i,x) in enumerate(weights)]
    keep_empty=[(np.isnan(x) or x==0.0) and not must_haves[i] for (i,x) in enumerate(weights)]
    no_replacement_needed=[(not keep_empty[i]) and (not needs_replacing[i]) for (i,x) in enumerate(weights)]
    
    missing_weights=sum(needs_replacing)

    total_for_missing_weights=fraction*missing_weights/(
        float(np.nansum(no_replacement_needed)+np.nansum(missing_weights)))
    
    adjustment_on_rest=(1.0-total_for_missing_weights)
    
    each_missing_weight=total_for_missing_weights/missing_weights
    
    def _good_weight(value, idx, needs_replacing, keep_empty, 
                     each_missing_weight, adjustment_on_rest):
        
        if needs_replacing[idx]:
            return each_missing_weight
        if keep_empty[idx]:
            return 0.0
        else:
            return value*adjustment_on_rest

    weights=[_good_weight(value, idx, needs_replacing, keep_empty, 
                          each_missing_weight, adjustment_on_rest) 
             for (idx, value) in enumerate(weights)]
    
    ## This process will screw up weights - let's fix them
    xsum=sum(weights)
    weights=[x/xsum for x in weights]
    
    return weights


def vol_equaliser(mean_list, stdev_list):
    """
    Normalises returns so they have the in sample vol
    
    >>> vol_equaliser([1.,2.],[2.,4.])
    ([1.5, 1.5], [3.0, 3.0])
    >>> vol_equaliser([1.,2.],[np.nan, np.nan])
    ([nan, nan], [nan, nan])
    """
    if np.all(np.isnan(stdev_list)):
        return (([np.nan]*len(mean_list), [np.nan]*len(stdev_list)))

    avg_stdev=np.nanmean(stdev_list)

    norm_factor=[asset_stdev/avg_stdev for asset_stdev in stdev_list]
    
    norm_means=[mean_list[i]/norm_factor[i] for (i, notUsed) in enumerate(mean_list)]
    norm_stdev=[stdev_list[i]/norm_factor[i] for (i, notUsed) in enumerate(stdev_list)]
    
    return (norm_means, norm_stdev)


def SR_equaliser(mean_list, stdev_list):
    """
    Normalises returns so they have the same SR
    
    >>> SR_equaliser([1., 2.],[2.,3.])
    [1.1666666666666665, 1.7499999999999998]
    >>> SR_equaliser([np.nan, 2.],[2.,np.nan])
    [nan, nan]
    """
    SR_list=[asset_mean/asset_stdev for (asset_mean, asset_stdev) in zip(mean_list, stdev_list)]
    
    if np.all(np.isnan(SR_list)):
        return [np.nan]*len(SR_list)
    
    avg_SR=np.nanmean(SR_list)
    
    norm_factor=[SR/avg_SR for SR in SR_list]
    
    norm_means=[mean_list[i]/norm_factor[i] for (i, notUsed) in enumerate(mean_list)]
    
    return norm_means


def addem(weights):
    ## Used for constraints
    return 1.0 - sum(weights)

def variance(weights, sigma):
    ## returns the variance (NOT standard deviation) given weights and sigma
    return (np.matrix(weights)*sigma*np.matrix(weights).transpose())[0,0]


def neg_SR(weights, sigma, mus):
    ## Returns minus the Sharpe Ratio (as we're minimising)

    estreturn=(np.matrix(weights)*mus)[0,0]
    std_dev=(variance(weights,sigma)**.5)
    
    return -estreturn/std_dev


def optimise( sigma, mean_list):
    
    mus=np.array(mean_list, ndmin=2).transpose()
    number_assets=sigma.shape[1]
    start_weights=[1.0/number_assets]*number_assets
    
    ## Constraints - positive weights, adding to 1.0
    bounds=[(0.0,1.0)]*number_assets
    cdict=[{'type':'eq', 'fun':addem}]
    ans=minimize(neg_SR, start_weights, (sigma, mus), method='SLSQP', bounds=bounds, constraints=cdict, tol=0.00001)

    return ans['x']


def sigma_from_corr_and_std(stdev_list, corrmatrix):
    stdev=np.array(stdev_list, ndmin=2).transpose()
    sigma=stdev*corrmatrix*stdev

    return sigma



def bootstrap_portfolio(subset_data, moments_estimator,
                cleaning, must_haves,
                  monte_runs=100, bootstrap_length=50,
                  **other_opt_args):
    """
    Given dataframe of returns; returns_to_bs, performs a bootstrap optimisation
    
    We run monte_carlo numbers of bootstraps
    Each one contains monte_length days drawn randomly, with replacement 
    (so *not* block bootstrapping)
    
    The other arguments are passed to the optimisation function markosolver
    
    :param subset_data: The data to optimise over
    :type subset_data: pd.DataFrame TxN

    :param cleaning: Should we clean correlations so can use incomplete data?
    :type cleaning: bool

    :param must_haves: The indices of things we must have weights for when cleaning
    :type must_haves: list of bool

    :param monte_runs: The number of bootstraps to do
    :type monte_runs: list of float

    :param bootstrap_length: Number of periods in each bootstrap
    :type bootstrap_length: int

    *_params passed through to data estimation functions

    **other_opt_args passed to single period optimiser

    :returns: float
    
    """

                
    all_results=[bs_one_time(subset_data, moments_estimator,
                            cleaning, must_haves, 
                            bootstrap_length,
                            **other_opt_args)
                                for unused_index in range(monte_runs)]
        
    ### We can take an average here; only because our weights always add up to 1. If that isn't true
    ###    then you will need to some kind of renormalisation

    weightlist=np.array([x[0] for x in all_results], ndmin=2)
    diaglist=[x[1] for x in all_results]
         
    theweights_mean=list(np.mean(weightlist, axis=0))
    
    diag=dict(bootstraps=diaglist)
    
    return (theweights_mean, diag)

def bs_one_time(subset_data, moments_estimator, 
                 cleaning, must_haves,
                bootstrap_length,
                **other_opt_args
                ):

    """
    Given dataframe of returns; does a single run of the bootstrap optimisation
    
    Each one contains monte_length days drawn randomly, with replacement 
    (so *not* block bootstrapping)
    
    The other arguments are passed to the optimisation function markosolver
    
    :param subset_data: The data to optimise over
    :type subset_data: pd.DataFrame TxN

    :param cleaning: Should we clean correlations so can use incomplete data?
    :type cleaning: bool

    :param must_haves: The indices of things we must have weights for when cleaning
    :type must_haves: list of bool

    :param monte_runs: The number of bootstraps to do
    :type monte_runs: list of float

    :param bootstrap_length: Number of periods in each bootstrap
    :type bootstrap_length: int

    *_params passed through to data estimation functions

    **other_opt_args passed to single period optimiser

    :returns: float
    
    """

    ## choose the data    
    bs_idx=[int(random.uniform(0,1)*len(subset_data)) for notUsed in range(bootstrap_length)]
    
    returns=subset_data.iloc[bs_idx,:] 
    
    (weights, diag)=markosolver(returns, moments_estimator, cleaning, must_haves, 
                       **other_opt_args)

    return (weights, diag)




if __name__ == '__main__':
    import doctest
    doctest.testmod()

