from scipy.stats import ttest_1samp

import numpy as np
from syscore.dateutils import Frequency
from syscore.constants import missing_data, arg_not_supplied
from systems.accounts.curves.account_curve import accountCurve
from systems.accounts.pandl_calculators.pandl_generic_costs import (
    GROSS_CURVE,
    NET_CURVE,
    COSTS_CURVE,
)


def _from_freq_str_to_frequency(freq_str):
    LOOKUP_DICT = dict(
        daily=Frequency.BDay,
        weekly=Frequency.Week,
        monthly=Frequency.Month,
        annual=Frequency.Year,
    )

    return LOOKUP_DICT[freq_str]


def _from_curve_str_to_curve_type(curve_type_str):
    LOOKUP_DICT = dict(gross=GROSS_CURVE, net=NET_CURVE, costs=COSTS_CURVE)

    return LOOKUP_DICT[curve_type_str]


class statsDict(dict):
    def __init__(
        self,
        account_curve_group: "accountCurveGroup",
        item="sharpe",
        freq="daily",
        curve_type="net",
        percent=True,
    ):

        dict_of_results_by_stat = self.dict_of_results_by_asset_name(
            item=item,
            account_curve_group=account_curve_group,
            freq_str=freq,
            curve_type_str=curve_type,
            is_percentage=percent,
        )

        super().__init__(dict_of_results_by_stat)

        self._account_curve_group = account_curve_group
        self._item = item

    def dict_of_results_by_asset_name_equal_weighted(
        self,
        item: str = arg_not_supplied,
        account_curve_group: "accountCurveGroup" = arg_not_supplied,
        freq_str: str = "daily",
        curve_type_str="net",
        is_percentage=True,
    ):

        weight = 1.0 / len(self.keys())
        unweighted_results = self.dict_of_results_by_asset_name(
            item=item,
            account_curve_group=account_curve_group,
            freq_str=freq_str,
            curve_type_str=curve_type_str,
            is_percentage=is_percentage,
        )

        weighted_results = dict(
            [
                (asset_name, weight * unweighted_results[asset_name])
                for asset_name in unweighted_results.keys()
            ]
        )

        return weighted_results

    def dict_of_results_by_asset_name_timeweighted(
        self,
        item: str = arg_not_supplied,
        account_curve_group: "accountCurveGroup" = arg_not_supplied,
        freq_str: str = "daily",
        curve_type_str="net",
        is_percentage=True,
    ):

        time_weights_dict = self._time_weights()
        unweighted_results = self.dict_of_results_by_asset_name(
            item=item,
            account_curve_group=account_curve_group,
            freq_str=freq_str,
            curve_type_str=curve_type_str,
            is_percentage=is_percentage,
        )

        weighted_results = dict(
            [
                (
                    asset_name,
                    time_weights_dict[asset_name] * unweighted_results[asset_name],
                )
                for asset_name in unweighted_results.keys()
            ]
        )

        return weighted_results

    def dict_of_results_by_asset_name(
        self,
        item: str = arg_not_supplied,
        account_curve_group: "accountCurveGroup" = arg_not_supplied,
        freq_str: str = "daily",
        curve_type_str="net",
        is_percentage=True,
    ):

        if account_curve_group is arg_not_supplied:
            account_curve_group = self.account_curve_group

        dict_of_results_by_stat = dict(
            [
                (
                    asset_name,
                    self.statresult_for_item(
                        asset_name=asset_name,
                        item=item,
                        account_curve_group=account_curve_group,
                        freq_str=freq_str,
                        curve_type_str=curve_type_str,
                        is_percentage=is_percentage,
                    ),
                )
                for asset_name in account_curve_group.asset_columns
            ]
        )

        return dict_of_results_by_stat

    def statresult_for_item(
        self,
        asset_name: str,
        item: str = arg_not_supplied,
        account_curve_group: "accountCurveGroup" = arg_not_supplied,
        freq_str: str = "daily",
        curve_type_str="net",
        is_percentage=True,
    ):

        if item is arg_not_supplied:
            item = self.item

        account_curve = self.account_curve_for_asset(
            account_curve_group=account_curve_group,
            asset_name=asset_name,
            freq_str=freq_str,
            curve_type_str=curve_type_str,
            is_percentage=is_percentage,
        )

        method_to_call = getattr(account_curve, item, missing_data)
        return method_to_call()

    def account_curve_for_asset(
        self,
        asset_name: str,
        account_curve_group: "accountCurveGroup" = arg_not_supplied,
        freq_str: str = "daily",
        curve_type_str="net",
        is_percentage=True,
    ) -> accountCurve:

        if account_curve_group is arg_not_supplied:
            account_curve_group = self.account_curve_group

        frequency = _from_freq_str_to_frequency(freq_str)
        curve_type = _from_curve_str_to_curve_type(curve_type_str)

        account_curve = accountCurve(
            account_curve_group.get_pandl_calculator_for_item(asset_name),
            curve_type=curve_type,
            is_percentage=is_percentage,
            frequency=frequency,
        )

        return account_curve

    def mean(self, timeweighted=True):
        if timeweighted:
            results = self.dict_of_results_by_asset_name_timeweighted()
        else:
            results = self.dict_of_results_by_asset_name_equal_weighted()

        results_values = list(results.values())

        return np.nanmean(results_values)

    def std(self, timeweighted=True):
        if timeweighted:
            results = self.dict_of_results_by_asset_name_timeweighted()
        else:
            results = self.dict_of_results_by_asset_name_equal_weighted()

        results_values = list(results.values())

        return np.nanstd(results_values)

    def tstat(self, timeweighted=True):
        if timeweighted:
            results = self.dict_of_results_by_asset_name_timeweighted()
        else:
            results = self.dict_of_results_by_asset_name_equal_weighted()

        results_values = list(results.values())

        return ttest_1samp(results_values, 0.0).statistic

    def pvalue(self, timeweighted=True):
        if timeweighted:
            results = self.dict_of_results_by_asset_name_timeweighted()
        else:
            results = self.dict_of_results_by_asset_name_equal_weighted()

        results_values = list(results.values())

        return ttest_1samp(results_values, 0.0).pvalue

    def _time_weights(self) -> dict:
        dict_of_time_lengths = dict(
            [
                (
                    asset_name,
                    self.account_curve_for_asset(
                        asset_name=asset_name
                    ).length_in_months,
                )
                for asset_name in self.keys()
            ]
        )
        average_length = np.mean(list(dict_of_time_lengths.values()))
        dict_of_time_weights = dict(
            [
                (asset_name, dict_of_time_lengths[asset_name] / average_length)
                for asset_name in dict_of_time_lengths.keys()
            ]
        )

        return dict_of_time_weights

    @property
    def account_curve_group(self):
        return self._account_curve_group

    @property
    def item(self):
        return self._item
