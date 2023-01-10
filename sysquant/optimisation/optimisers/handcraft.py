import numpy as np

from sysquant.estimators.clustering_correlations import cluster_correlation_matrix
from sysquant.estimators.estimates import Estimates
from sysquant.estimators.correlations import correlationEstimate
from sysquant.optimisation.SR_adjustment import adjust_weights_for_SR
from sysquant.optimisation.weights import (
    portfolioWeights,
    estimatesWithPortfolioWeights,
    one_over_n_weights_given_asset_names,
)

from sysquant.estimators.diversification_multipliers import (
    diversification_mult_single_period,
)

## This is a cut down and rewritten version of the original code,
##   for example it does not do risk targeting
##   and as it splits portfolios into subgroups of 2 doesn't worry about data history
##    for correlations


def handcraft_optimisation(
    estimates: Estimates,
    equalise_SR: bool = False,
    equalise_vols: bool = True,
    **_ignored_weighting_kwargs,
) -> estimatesWithPortfolioWeights:

    weights = get_handcrafted_portfolio_weights_for_valid_data(
        estimates, equalise_vols=equalise_vols, equalise_SR=equalise_SR
    )

    estimates_and_portfolio_weights = estimatesWithPortfolioWeights(
        weights=weights, estimates=estimates
    )

    return estimates_and_portfolio_weights


def get_handcrafted_portfolio_weights_for_valid_data(
    estimates: Estimates, equalise_vols: bool = True, equalise_SR: bool = False
) -> portfolioWeights:

    handcraft_portfolio = handcraftPortfolio(estimates)
    risk_weights = handcraft_portfolio.risk_weights(equalise_SR=equalise_SR)

    if equalise_vols:
        ## no cash weights
        return risk_weights
    else:
        raise Exception("Non equalised vols not supported")


FIXED_CLUSTER_SIZE = 2  # Do not change


class handcraftPortfolio(object):
    def __init__(self, estimates: Estimates):

        self._estimates = estimates

    @property
    def estimates(self) -> Estimates:
        return self._estimates

    @property
    def correlation(self) -> correlationEstimate:
        return self.estimates.correlation

    @property
    def mean(self) -> list:
        return self.estimates.mean_list

    @property
    def stdev(self) -> list:
        return self.estimates.stdev_list

    @property
    def sharpe_ratio(self) -> list:
        return [mean / stdev for mean, stdev in zip(self.mean, self.stdev)]

    @property
    def data_length_years(self) -> float:
        return self.estimates.data_length_years

    @property
    def boring_correlation(self) -> bool:
        return self.estimates.correlation.is_boring

    @property
    def size(self) -> int:
        return len(self.mean)

    @property
    def avg_correlation(self) -> float:
        return self.estimates.correlation.average_corr()

    @property
    def asset_names(self) -> list:
        return self.estimates.asset_names

    def risk_weights(self, equalise_SR: bool = False) -> portfolioWeights:
        if self.size <= FIXED_CLUSTER_SIZE:
            # don't cluster one or two assets
            raw_weights = self.risk_weights_this_portfolio()
        else:
            raw_weights = self.aggregated_risk_weights()

        if equalise_SR or len(raw_weights) == 1:
            return raw_weights
        else:
            adjusted_weights = adjust_weights_for_SR_on_handcrafted_portfolio(
                raw_weights=raw_weights, handcraft_portfolio=self
            )

            return adjusted_weights

    def risk_weights_this_portfolio(self) -> portfolioWeights:

        asset_names = self.asset_names
        raw_weights = one_over_n_weights_given_asset_names(asset_names)

        return raw_weights

    def aggregated_risk_weights(self):
        sub_portfolios = create_sub_portfolios_from_portfolio(self)
        aggregate_risk_weights = aggregate_risk_weights_over_sub_portfolios(
            sub_portfolios
        )

        return aggregate_risk_weights

    def div_mult(self, weights: portfolioWeights):
        asset_names = self.asset_names
        weights_aligned = weights.reorder(asset_names)
        correlation = self.estimates.correlation

        div_mult = diversification_mult_single_period(
            weights=weights_aligned, corrmatrix=correlation
        )

        return div_mult

    def subset(self, subset_of_asset_names: list):
        return handcraftPortfolio(self.estimates.subset(subset_of_asset_names))


## SR ADJUSTMENT


def adjust_weights_for_SR_on_handcrafted_portfolio(
    raw_weights: portfolioWeights, handcraft_portfolio: handcraftPortfolio
) -> portfolioWeights:

    SR_list = handcraft_portfolio.sharpe_ratio
    avg_correlation = handcraft_portfolio.avg_correlation
    years_of_data = handcraft_portfolio.data_length_years
    asset_names = handcraft_portfolio.asset_names

    weights_as_list = raw_weights.as_list_given_keys(asset_names)

    weights = adjust_weights_for_SR(
        SR_list=SR_list,
        avg_correlation=avg_correlation,
        years_of_data=years_of_data,
        weights_as_list=weights_as_list,
    )

    weights = portfolioWeights.from_weights_and_keys(
        list_of_weights=weights, list_of_keys=asset_names
    )

    return weights


## SUB PORTFOLIOS


def create_sub_portfolios_from_portfolio(handcraft_portfolio: handcraftPortfolio):

    clusters_as_names = cluster_correlation_matrix(handcraft_portfolio.correlation)

    sub_portfolios = create_sub_portfolios_given_clusters(
        clusters_as_names, handcraft_portfolio
    )

    return sub_portfolios


def create_sub_portfolios_given_clusters(
    clusters_as_names: list, handcraft_portfolio: handcraftPortfolio
) -> list:
    list_of_sub_portfolios = [
        handcraft_portfolio.subset(subset_of_asset_names)
        for subset_of_asset_names in clusters_as_names
    ]

    return list_of_sub_portfolios


def aggregate_risk_weights_over_sub_portfolios(
    sub_portfolios: list,
) -> portfolioWeights:
    # sub portfolios guaranteed to be 2 long
    # We allocate half to each, adjusted for IDM
    # *We don't adjust for SR here*, but after we've aggregated
    # This is quicker and simpler

    assert len(sub_portfolios) == 2
    subportfolio_weights = [0.5, 0.5]

    risk_weights_by_portfolio = [
        sub_portfolio.risk_weights(equalise_SR=True) for sub_portfolio in sub_portfolios
    ]

    div_mult_by_portfolio = [
        sub_portfolio.div_mult(sub_weights)
        for sub_portfolio, sub_weights in zip(sub_portfolios, risk_weights_by_portfolio)
    ]

    multiplied_out_risk_weights = [
        multiplied_out_risk_weight_for_sub_portfolios(
            weights,
            div_mult_for_portfolio=div_mult,
            weight_for_subportfolio=weight_for_subportfolio,
        )
        for weights, div_mult, weight_for_subportfolio in zip(
            risk_weights_by_portfolio, div_mult_by_portfolio, subportfolio_weights
        )
    ]

    aggregate_weights = portfolioWeights.from_list_of_subportfolios(
        multiplied_out_risk_weights
    )

    return aggregate_weights


def multiplied_out_risk_weight_for_sub_portfolios(
    weights_for_portfolio: portfolioWeights,
    div_mult_for_portfolio: float = 1.0,
    weight_for_subportfolio: float = 0.5,
) -> portfolioWeights:

    asset_names = list(weights_for_portfolio.keys())
    mult_weights = portfolioWeights(
        [
            (
                asset_name,
                weight_for_subportfolio
                * div_mult_for_portfolio
                * weights_for_portfolio[asset_name],
            )
            for asset_name in asset_names
        ]
    )

    return mult_weights
