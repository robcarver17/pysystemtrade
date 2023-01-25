import pandas as pd
import numpy as np
import datetime
from dataclasses import dataclass


from syscore.genutils import flatten_list
from syscore.pandas.find_data import get_row_of_df_aligned_to_weights_as_dict

from sysquant.estimators.estimates import Estimates
from sysquant.estimators.correlation_estimator import correlationEstimate
from sysquant.estimators.stdev_estimator import stdevEstimates


class portfolioWeights(dict):
    @classmethod
    def allzeros(portfolioWeights, list_of_keys: list):
        return portfolioWeights.all_one_value(list_of_keys, value=0.0)

    @classmethod
    def allnan(portfolioWeights, list_of_keys: list):
        return portfolioWeights.all_one_value(list_of_keys, value=np.nan)

    @classmethod
    def all_one_value(portfolioWeights, list_of_keys: list, value=0.0):
        return portfolioWeights.from_weights_and_keys(
            list_of_weights=[value] * len(list_of_keys), list_of_keys=list_of_keys
        )

    @classmethod
    def from_weights_and_keys(
        portfolioWeights, list_of_weights: list, list_of_keys: list
    ):
        assert len(list_of_keys) == len(list_of_weights)
        pweights_as_list = [
            (key, weight) for key, weight in zip(list_of_keys, list_of_weights)
        ]

        return portfolioWeights(pweights_as_list)

    @property
    def assets(self) -> list:
        return list(self.keys())

    def all_weights_are_zero(self):
        return all([x == 0.0 for x in self.values()])

    def subset(self, asset_names: list):
        return self.reorder(asset_names)

    def reorder(self, asset_names: list):
        return portfolioWeights([(key, self[key]) for key in asset_names])

    def replace_weights_with_ints(self):
        new_weights_as_dict = dict(
            [
                (instrument_code, _int_from_nan(value))
                for instrument_code, value in self.items()
            ]
        )

        return portfolioWeights(new_weights_as_dict)

    def as_np(self) -> np.array:
        as_list = self.as_list()
        return np.array(as_list)

    def as_list(self) -> list:
        keys = list(self.keys())
        as_list = self.as_list_given_keys(keys)

        return as_list

    def as_list_given_keys(self, list_of_keys: list):
        return [self[key] for key in list_of_keys]

    def product_with_stdev(self, stdev: stdevEstimates):
        stdev_align_list = stdev.list_in_key_order(self.assets)
        self_align_list = self.as_list()

        product = list(np.array(stdev_align_list) * np.array(self_align_list))

        return self.from_weights_and_keys(
            list_of_weights=product, list_of_keys=self.assets
        )

    @classmethod
    def from_list_of_subportfolios(portfolioWeights, list_of_portfolio_weights):
        list_of_unique_asset_names = list(
            set(
                flatten_list(
                    [
                        list(subportfolio.keys())
                        for subportfolio in list_of_portfolio_weights
                    ]
                )
            )
        )

        portfolio_weights = portfolioWeights.allzeros(list_of_unique_asset_names)

        for subportfolio_weights in list_of_portfolio_weights:
            for asset_name in list(subportfolio_weights.keys()):
                portfolio_weights[asset_name] = (
                    portfolio_weights[asset_name] + subportfolio_weights[asset_name]
                )

        return portfolio_weights

    def with_zero_weights_for_missing_keys(self, list_of_asset_names):
        all_assets = list(set(list_of_asset_names + list(self.keys())))
        return portfolioWeights(dict([(key, self.get(key, 0)) for key in all_assets]))

    def with_zero_weights_instead_of_nan(self):
        all_assets = self.keys()

        def _replace(x):
            if np.isnan(x):
                return 0.0
            else:
                return x

        return portfolioWeights(
            dict([(key, _replace(self[key])) for key in all_assets])
        )

    def assets_with_data(self) -> list:
        return [key for key, value in self.items() if not np.isnan(value)]

    def __truediv__(self, other: "portfolioWeights"):
        return self._operate_on_other(other, "__truediv__")

    def __mul__(self, other: "portfolioWeights"):
        return self._operate_on_other(other, "__mul__")

    def __sub__(self, other):
        return self._operate_on_other(other, "__sub__")

    def _operate_on_other(self, other: "portfolioWeights", func_to_use):
        asset_list = self.assets
        np_self = np.array(self.as_list_given_keys(asset_list))
        np_other = np.array(other.as_list_given_keys(asset_list))

        np_func = getattr(np_self, func_to_use)
        np_results = np_func(np_other)

        return portfolioWeights.from_weights_and_keys(
            list_of_weights=list(np_results), list_of_keys=asset_list
        )

    def portfolio_stdev(self, cmatrix: correlationEstimate):
        valid_assets = list(
            set(self.assets_with_data()).intersection(set(cmatrix.assets_with_data()))
        )
        weights_valid = self.subset(valid_assets)
        corr_valid = cmatrix.subset(valid_assets)

        weights_np = weights_valid.as_np()
        corr_np = corr_valid.as_np()

        variance = weights_np.dot(corr_np).dot(weights_np)

        risk = variance**0.5

        return risk


class seriesOfPortfolioWeights(pd.DataFrame):
    def get_weights_on_date(self, relevant_date: datetime.datetime) -> portfolioWeights:
        weights_as_dict = get_row_of_df_aligned_to_weights_as_dict(
            df=self, relevant_date=relevant_date
        )

        return portfolioWeights(weights_as_dict)

    def get_sum_leverage(self) -> pd.Series:
        return self.abs().sum(axis=1)


def _int_from_nan(x: float):
    if np.isnan(x):
        return 0
    else:
        return int(x)


@dataclass()
class estimatesWithPortfolioWeights:
    estimates: Estimates
    weights: portfolioWeights


def one_over_n_portfolio_weights_from_estimates(
    estimate: Estimates,
) -> portfolioWeights:
    mean_estimate = estimate.mean
    asset_names = list(mean_estimate.keys())
    return one_over_n_weights_given_asset_names(asset_names)


def one_over_n_weights_given_data(data: pd.DataFrame):
    list_of_asset_names = list(data.columns)

    return one_over_n_weights_given_asset_names(list_of_asset_names)


def one_over_n_weights_given_asset_names(list_of_asset_names: list) -> portfolioWeights:
    weight = 1.0 / len(list_of_asset_names)
    return portfolioWeights(
        [(asset_name, weight) for asset_name in list_of_asset_names]
    )
