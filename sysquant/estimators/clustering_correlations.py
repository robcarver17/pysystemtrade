import numpy as np
from scipy.cluster import hierarchy as sch

from syscore.genutils import flatten_list
from sysquant.estimators.correlations import correlationEstimate


def assets_in_cluster_order(corr_matrix: correlationEstimate, cluster_size: int = 2):
    clusters_as_names = cluster_correlation_matrix(
        corr_matrix, cluster_size=cluster_size
    )

    return flatten_list(clusters_as_names)


def cluster_correlation_matrix(corr_matrix: correlationEstimate, cluster_size: int = 2):

    if corr_matrix.is_boring:
        # Boring correlation will break if we try and cluster
        corr_as_np = corr_matrix.values
        clusters = arbitrary_split_of_correlation_matrix(
            corr_as_np, cluster_size=cluster_size
        )
    else:
        clusters = get_list_of_clusters_for_non_boring_correlation_matrix(
            corr_matrix, cluster_size=cluster_size
        )
    clusters_as_names = from_cluster_index_to_asset_names(clusters, corr_matrix)

    return clusters_as_names


def get_list_of_clusters_for_non_boring_correlation_matrix(
    corr_matrix: np.array, cluster_size: int = 2
) -> list:
    corr_as_np = corr_matrix.values
    try:
        clusters = get_list_of_clusters_for_correlation_matrix(
            corr_as_np, cluster_size=cluster_size
        )
    except:
        clusters = arbitrary_split_of_correlation_matrix(
            corr_as_np, cluster_size=cluster_size
        )

    return clusters


def get_list_of_clusters_for_correlation_matrix(
    corr_as_np: np.array, cluster_size: int = 2
) -> list:
    d = sch.distance.pdist(corr_as_np)
    L = sch.linkage(d, method="complete")

    cutoff = cutoff_distance_to_guarantee_N_clusters(
        corr_as_np, L=L, cluster_size=cluster_size
    )
    ind = sch.fcluster(L, cutoff, "distance")
    ind = list(ind)

    if max(ind) > cluster_size:
        raise Exception("Couldn't cluster into %d clusters" % cluster_size)

    return ind


def cutoff_distance_to_guarantee_N_clusters(
    corr_as_np: np.array, L: np.array, cluster_size: int = 2
):
    # assert cluster_size==2

    N = len(corr_as_np)
    return L[N - cluster_size][2] - 0.000001


def arbitrary_split_of_correlation_matrix(
    corr_matrix: np.array, cluster_size: int = 2
) -> list:
    # split correlation of 3 or more assets
    count_assets = len(corr_matrix)
    return arbitrary_split_for_asset_length(count_assets, cluster_size=cluster_size)


def arbitrary_split_for_asset_length(count_assets: int, cluster_size: int = 2) -> list:

    return [(x % cluster_size) + 1 for x in range(count_assets)]


def from_cluster_index_to_asset_names(
    clusters: list, corr_matrix: correlationEstimate
) -> list:

    all_clusters = list(set(clusters))
    asset_names = corr_matrix.columns
    list_of_asset_clusters = [
        get_asset_names_for_cluster_index(cluster_id, clusters, asset_names)
        for cluster_id in all_clusters
    ]

    return list_of_asset_clusters


def get_asset_names_for_cluster_index(
    cluster_id: int, clusters: list, asset_names: list
):

    list_of_assets = [
        asset for asset, cluster in zip(asset_names, clusters) if cluster == cluster_id
    ]

    return list_of_assets
