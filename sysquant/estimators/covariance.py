from sysquant.estimators.correlations import correlationEstimate
from sysquant.estimators.stdev_estimator import stdevEstimates
from sysquant.optimisation.shared import sigma_from_corr_and_std

class covarianceEstimate(correlationEstimate):
    def assets_with_missing_data(self) -> list:
        na_row_count = self.as_pd().isna().all(axis=1)
        return [keyname for keyname in na_row_count.keys() if na_row_count[keyname]]

def covariance_from_stdev_and_correlation(correlation_estimate: correlationEstimate,
                                          stdev_estimate: stdevEstimates) -> covarianceEstimate:

    list_of_assets = list(correlation_estimate.columns)
    aligned_stdev_list = stdev_estimate.list_in_key_order(list_of_assets)
    sigma = sigma_from_corr_and_std(aligned_stdev_list, correlation_estimate.values)

    return covarianceEstimate(sigma, list_of_assets)
