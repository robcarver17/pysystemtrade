import scipy.cluster.hierarchy as sch


import numpy as np
import pandas as pd



def ordered_correlation_matrix(corr_matrix: pd.DataFrame):
    clusters = cluster_correlation_matrix(corr_matrix.values)
    unique_clusters = list(set(clusters))
    starting_names = list(corr_matrix.columns)
    ordered_names = []
    for cluster_id  in unique_clusters:
        relevant_names = [column_name for column_name, cluster in zip(starting_names, clusters) if cluster==cluster_id]
        ordered_names = ordered_names + relevant_names

    new_matrix = corr_matrix[ordered_names].reindex(ordered_names)

    return new_matrix

def cluster_correlation_matrix(corr_matrix: np.array, max_cluster_size = 3) -> list:
    d = sch.distance.pdist(corr_matrix)
    L = sch.linkage(d, method="complete")
    ind = sch.fcluster(L, max_cluster_size, criterion="maxclust")
    ind = list(ind)

    return ind



def boring_corr_matrix(size, offdiag=0.99, diag=1.0):
    """
    Create a boring correlation matrix

    :param size: dimensions
    :param offdiag: value to put in off diagonal
    :param diag: value to put in diagonal
    :return: np.array 2 dimensions, size
    """
    size_index = range(size)

    def _od(i, j, offdiag, diag):
        if i == j:
            return diag
        else:
            return offdiag

    m = [[_od(i, j, offdiag, diag) for i in size_index] for j in size_index]
    m = np.array(m)
    return m


class CorrelationList(object):
    """
    A correlation list is a list of correlations, packed in with date information about them
    # FIXME DUPLICATE OF METHOD IN SYSQUANT; USED ONLY BY RISK OVERLAY CODE
    """

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
        return (
            "%d correlation estimates for %s; use .corr_list, .column_names, .fit_dates" %
            (len(
                self.corr_list), ",".join(
                self.columns)))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
