import numpy as np
from dataclasses import dataclass

from syscore.genutils import str2Bool, flatten_list
from syscore.pandas.frequency import how_many_times_a_year_is_pd_frequency

from sysquant.estimators.correlations import correlationEstimate
from sysquant.estimators.mean_estimator import meanEstimates
from sysquant.estimators.stdev_estimator import stdevEstimates


@dataclass
class Estimates:
    correlation: correlationEstimate
    mean: meanEstimates
    stdev: stdevEstimates
    data_length: int
    frequency: str

    @property
    def size(self):
        # assume all same size
        return len(self.mean)

    @property
    def asset_names(self) -> list:
        list_of_asset_names = list(self.correlation.columns)
        return list_of_asset_names

    @property
    def mean_list(self) -> list:
        mean = self.mean
        list_of_asset_names = self.asset_names
        mean_list = [mean[asset_name] for asset_name in list_of_asset_names]

        return mean_list

    @property
    def stdev_list(self) -> list:
        stdev = self.stdev
        list_of_asset_names = self.asset_names
        stdev_list = [stdev[asset_name] for asset_name in list_of_asset_names]

        return stdev_list

    @property
    def correlation_matrix(self) -> np.array:
        return self.correlation.values

    @property
    def data_length_years(self) -> float:
        data_length_years = float(
            self.data_length
        ) / how_many_times_a_year_is_pd_frequency(self.frequency)

        return data_length_years

    def equalise_estimates(
        self,
        equalise_SR: bool = True,
        ann_target_SR: float = 0.5,
        equalise_vols: bool = True,
    ):

        return equalise_estimates(
            self,
            equalise_SR=equalise_SR,
            ann_target_SR=ann_target_SR,
            equalise_vols=equalise_vols,
        )

    def shrink_correlation_to_average(self, shrinkage_corr: float):
        self.correlation = self.correlation.shrink_to_average(shrinkage_corr)
        return self

    def shrink_means_to_SR(self, shrinkage_SR: float = 0.90, ann_target_SR=0.5):
        self.mean = shrink_means_to_SR(
            self, shrinkage_SR=shrinkage_SR, target_SR=ann_target_SR
        )

        return self

    def subset_with_available_data(self):
        assets_with_available_data = self.assets_with_available_data()
        return self.subset(assets_with_available_data)

    def subset(self, subset_of_asset_names: list):
        return Estimates(
            correlation=self.correlation.subset(subset_of_asset_names),
            mean=self.mean.subset(subset_of_asset_names),
            stdev=self.stdev.subset(subset_of_asset_names),
            frequency=self.frequency,
            data_length=self.data_length,
        )

    def assets_with_missing_data(self) -> list:
        missing_correlations = self.correlation.assets_with_missing_data()
        missing_means = self.mean.assets_with_missing_data()
        missing_stdev = self.stdev.assets_with_missing_data()

        missing_assets = list(
            set(flatten_list([missing_stdev, missing_means, missing_correlations]))
        )

        return missing_assets

    def assets_with_available_data(self) -> list:
        return list(np.setdiff1d(self.asset_names, self.assets_with_missing_data()))


def equalise_estimates(
    estimates: Estimates,
    equalise_SR: bool = True,
    ann_target_SR: float = 0.5,
    equalise_vols: bool = True,
) -> Estimates:

    list_of_asset_names = estimates.asset_names
    mean_list = estimates.mean_list
    stdev_list = estimates.stdev_list

    equalised_mean_list, equalised_stdev_list = equalise_estimates_from_lists(
        mean_list=mean_list,
        stdev_list=stdev_list,
        equalise_SR=equalise_SR,
        ann_target_SR=ann_target_SR,
        equalise_vols=equalise_vols,
    )

    equalised_means = meanEstimates(
        [
            (asset_name, mean_value)
            for asset_name, mean_value in zip(list_of_asset_names, equalised_mean_list)
        ]
    )

    equalised_stdev = stdevEstimates(
        [
            (asset_name, stdev_value)
            for asset_name, stdev_value in zip(
                list_of_asset_names, equalised_stdev_list
            )
        ]
    )

    estimates.mean = equalised_means
    estimates.stdev = equalised_stdev

    return estimates


def equalise_estimates_from_lists(
    mean_list: list,
    stdev_list: list,
    equalise_SR: bool = True,
    ann_target_SR: float = 0.5,
    equalise_vols: bool = True,
) -> list:

    equalise_vols = str2Bool(equalise_vols)
    equalise_SR = str2Bool(equalise_SR)

    if equalise_vols:
        mean_list, stdev_list = vol_equaliser(
            mean_list=mean_list, stdev_list=stdev_list
        )

    if equalise_SR:
        mean_list = SR_equaliser(stdev_list, target_SR=ann_target_SR)

    return mean_list, stdev_list


def SR_equaliser(stdev_list, target_SR: float = 0.5):
    """
    Normalises returns so they have the same SR

    >>> SR_equaliser([1., 2.],.5)
    [1.1666666666666665, 1.7499999999999998]
    >>> SR_equaliser([np.nan, 2.],.5)
    [nan, 1.0]
    """
    return [target_SR * asset_stdev for asset_stdev in stdev_list]


def vol_equaliser(mean_list, stdev_list):
    """
    Normalises returns so they have the in sample vol

    >>> vol_equaliser([1.,2.],[2.,4.])
    ([1.5, 1.5], [3.0, 3.0])
    >>> vol_equaliser([1.,2.],[np.nan, np.nan])
    ([nan, nan], [nan, nan])
    """
    if np.all(np.isnan(stdev_list)):
        return ([np.nan] * len(mean_list), [np.nan] * len(stdev_list))

    avg_stdev = np.nanmean(stdev_list)

    norm_factor = [asset_stdev / avg_stdev for asset_stdev in stdev_list]

    with np.errstate(invalid="ignore"):
        norm_means = [
            mean_list[i] / norm_factor[i] for (i, notUsed) in enumerate(mean_list)
        ]
        norm_stdev = [
            stdev_list[i] / norm_factor[i] for (i, notUsed) in enumerate(stdev_list)
        ]

    return (norm_means, norm_stdev)


def shrink_means_to_SR(
    estimates: Estimates, shrinkage_SR: float = 1.0, target_SR=0.5
) -> meanEstimates:

    list_of_asset_names = estimates.asset_names
    mean_list = estimates.mean_list
    stdev_list = estimates.stdev_list

    shrunk_mean_list = shrink_SR_with_lists(
        mean_list=mean_list,
        stdev_list=stdev_list,
        shrinkage_SR=shrinkage_SR,
        target_SR=target_SR,
    )

    shrunk_means = meanEstimates(
        [
            (asset_name, mean_value)
            for asset_name, mean_value in zip(list_of_asset_names, shrunk_mean_list)
        ]
    )

    return shrunk_means


def shrink_SR_with_lists(
    mean_list: list, stdev_list: list, shrinkage_SR: float = 1.0, target_SR=0.5
):
    """
    >>> shrink_SR([.0,1.], [1.,2.], .5)
    [0.25, 1.0]
    >>> shrink_SR([np.nan, np.nan], [1.,2.], .5)
    [nan, nan]
    """
    SR_estimates = [
        asset_mean / asset_stdev
        for (asset_mean, asset_stdev) in zip(mean_list, stdev_list)
    ]

    if np.all(np.isnan(SR_estimates)):
        return [np.nan] * len(mean_list)

    post_SR_list = [
        (shrinkage_SR * target_SR) + (1 - shrinkage_SR) * estimatedSR
        for estimatedSR in SR_estimates
    ]

    post_means = [
        asset_SR * asset_stdev
        for (asset_SR, asset_stdev) in zip(post_SR_list, stdev_list)
    ]

    return post_means
