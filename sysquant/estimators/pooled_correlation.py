from copy import copy

import syscore.pandas.list_of_df
from syscore.pandas.list_of_df import (
    listOfDataFrames,
    stacked_df_with_added_time_from_list,
)

from sysquant.estimators.correlations import CorrelationList
from sysquant.estimators.correlation_over_time import correlation_over_time


def pooled_correlation_estimator(
    data: listOfDataFrames, frequency="W", forward_fill_data=True, **kwargs
) -> CorrelationList:
    copied_data = copy(data)
    if forward_fill_data:
        # NOTE if we're not pooling passes a list of one
        copied_data = copied_data.ffill()

    downsampled_data = copied_data.resample(frequency)

    ## Will need to keep this to adjust lookbacks
    length_adjustment = len(downsampled_data)

    ## We do this to ensure same frequency throughout once concatenated
    data_at_common_frequency = downsampled_data.reindex_to_common_index()

    # Make into one giant dataframe
    pooled_data = syscore.pandas.list_of_df.stacked_df_with_added_time_from_list(
        data_at_common_frequency
    )

    correlation_list = correlation_over_time(
        pooled_data, **kwargs, length_adjustment=length_adjustment
    )

    return correlation_list
