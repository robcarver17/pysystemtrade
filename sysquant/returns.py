import pandas as pd
import numpy as np

from systems.accounts.curves.account_curve_group import accountCurveGroup
from syscore.genutils import flatten_list
from syscore.dateutils import ROOT_BDAYS_INYEAR

from syscore.pandas.list_of_df import listOfDataFrames
from syscore.pandas.list_of_df import stacked_df_with_added_time_from_list

SINGLE_NAME = "asset"


class dictOfSR(dict):
    def apply_cost_multiplier(self, cost_multiplier: float = 1.0) -> "dictOfSR":
        column_names = list(self.keys())
        multiplied_dict_of_cost_SR = dict(
            [(column, self[column] * cost_multiplier) for column in column_names]
        )

        multiplied_dict_of_cost_SR = dictOfSR(multiplied_dict_of_cost_SR)

        return multiplied_dict_of_cost_SR


class dictOfSRacrossAssets(dict):
    def get_pooled_SR(self, asset_name) -> dictOfSR:
        column_names = self.get_column_names_for_asset(asset_name)
        column_SR_dict = dict(
            [
                (column, self.get_avg_SR_for_column_name_across_dict(column))
                for column in column_names
            ]
        )

        column_SR_dict = dictOfSR(column_SR_dict)

        return column_SR_dict

    def get_avg_SR_for_column_name_across_dict(self, column: str) -> float:
        list_of_SR = [dict_for_asset[column] for dict_for_asset in self.values()]
        avg_SR = np.mean(list_of_SR)
        return avg_SR

    def get_column_names_for_asset(self, asset_name) -> list:
        return list(self.get_SR_dict_for_asset(asset_name).keys())

    def get_SR_dict_for_asset(self, asset_name) -> dictOfSR:
        return self[asset_name]


class returnsForOptimisation(pd.DataFrame):
    def __init__(self, *args, frequency: str = "W", pooled_length: int = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self._frequency = frequency
        self._pooled_length = pooled_length
        # Any additional attributes need to be added into the reduce below

    def __reduce__(self):
        t = super().__reduce__()
        t[2].update(
            {
                "_is_copy": self._is_copy,
                "_frequency": self._frequency,
                "_pooled_length": self._pooled_length,
            }
        )
        return t[0], t[1], t[2]

    @property
    def frequency(self):
        return self._frequency

    @property
    def pooled_length(self):
        return self._pooled_length


class dictOfReturnsForOptimisation(dict):
    def get_column_names(self) -> list:
        ## all names should match so shouldn't matter
        column_names = list(self.values())[0].keys()
        return column_names

    def equalise_returns(self):
        avg_return = self.get_average_return()
        asset_names = self.keys()

        for asset in asset_names:
            self[asset] = _equalise_average_returns_for_df(
                self[asset], avg_return=avg_return
            )

    def get_average_return(self) -> float:
        column_names = self.get_column_names()
        avg_return_by_column = [
            _get_average_return_in_dict_for_column(self, column)
            for column in column_names
        ]

        avg_return = np.nanmean(avg_return_by_column)

        return avg_return

    def adjust_returns_for_SR_costs(
        self, dict_of_SR_costs: dictOfSR
    ) -> "dictOfReturnsForOptimisation":
        net_returns_dict = dict(
            [
                (
                    asset_name,
                    _adjust_df_for_SR_costs(self[asset_name], dict_of_SR_costs),
                )
                for asset_name in self.keys()
            ]
        )
        net_returns_dict = dictOfReturnsForOptimisation(net_returns_dict)

        return net_returns_dict

    def single_resampled_set_of_returns(self, frequency: str) -> returnsForOptimisation:
        returns_as_list = listOfDataFrames(self.values())
        pooled_length = len(returns_as_list)

        returns_as_list_downsampled = returns_as_list.resample_sum(frequency)
        returns_as_list_common_ts = (
            returns_as_list_downsampled.reindex_to_common_index()
        )

        returns_for_optimisation = stacked_df_with_added_time_from_list(
            returns_as_list_common_ts
        )
        returns_for_optimisation = returnsForOptimisation(
            returns_for_optimisation, frequency=frequency, pooled_length=pooled_length
        )

        return returns_for_optimisation


def _adjust_df_for_SR_costs(gross_returns: pd.DataFrame, dict_of_SR_costs: dictOfSR):
    net_returns_as_dict = dict(
        [
            (
                column_name,
                _adjust_df_column_for_SR_costs(
                    gross_returns, dict_of_SR_costs, column_name
                ),
            )
            for column_name in gross_returns.columns
        ]
    )

    net_returns_as_df = pd.DataFrame(net_returns_as_dict, index=gross_returns.index)

    return net_returns_as_df


def _adjust_df_column_for_SR_costs(
    gross_returns: pd.DataFrame, dict_of_SR_costs: dictOfSR, column_name: str
):
    # Returns always business days

    daily_gross_returns_for_column = gross_returns[column_name]
    daily_gross_return_std = daily_gross_returns_for_column.std()
    daily_SR_cost = dict_of_SR_costs[column_name] / ROOT_BDAYS_INYEAR

    daily_returns_cost = -daily_SR_cost * daily_gross_return_std

    daily_returns_cost_as_list = [daily_returns_cost] * len(gross_returns.index)
    daily_returns_cost_as_ts = pd.Series(
        daily_returns_cost_as_list, index=gross_returns.index
    )

    net_returns = daily_gross_returns_for_column + daily_returns_cost_as_ts

    return net_returns


def _get_average_return_in_dict_for_column(
    returns_dict: dictOfReturnsForOptimisation, column: str
) -> float:
    ## all daily data so can take an average
    series_of_returns = [
        returns_series[column].values for returns_series in returns_dict.values()
    ]
    all_returns = flatten_list(series_of_returns)

    return np.nanmean(all_returns)


def _equalise_average_returns_for_df(
    return_df: pd.DataFrame, avg_return: float = 0.0
) -> pd.DataFrame:
    # preserve 'noise' so standard deviation constant
    return_df = return_df.apply(
        _equalise_average_returns_for_df_column, axis=0, avg_return=avg_return
    )

    return return_df


def _equalise_average_returns_for_df_column(
    return_data: pd.Series, avg_return: float = 0.0
) -> pd.Series:
    current_mean = np.nanmean(return_data.values)
    mean_adjustment = avg_return - current_mean

    new_data = return_data + mean_adjustment

    return new_data


class dictOfReturnsForOptimisationWithCosts(dict):
    def __init__(self, dict_of_returns):
        dict_of_returns = _turn_singular_account_curve_into_dict(dict_of_returns)

        super().__init__(dict_of_returns)

    def get_returns_for_asset_as_single_dict(
        self, asset_name, type: str = "gross"
    ) -> dictOfReturnsForOptimisation:
        returns_for_asset = self[asset_name]
        typed_returns = getattr(returns_for_asset, type)
        new_returns_dict = {SINGLE_NAME: typed_returns}

        new_returns_dict = dictOfReturnsForOptimisation(new_returns_dict)

        return new_returns_dict

    def get_returns_for_all_assets(
        self, type: str = "gross"
    ) -> dictOfReturnsForOptimisation:
        gross_returns_dict = dict(
            [(code, getattr(self[code], type)) for code in self.keys()]
        )
        gross_returns_dict = dictOfReturnsForOptimisation(gross_returns_dict)

        return gross_returns_dict

    def dict_of_SR(self, type: str) -> dictOfSRacrossAssets:
        dict_of_SR = dict(
            [
                (code, returns_for_optimisation.get_annual_SR_dict(type))
                for code, returns_for_optimisation in self.items()
            ]
        )

        dict_of_SR = dictOfSRacrossAssets(dict_of_SR)

        return dict_of_SR

    def get_annual_SR_dict_for_asset(
        self, asset_name: str, type: str = "gross"
    ) -> dictOfSR:
        returns_this_asset = self[asset_name]

        SR_dict = returns_this_asset.get_annual_SR_dict(type)

        return SR_dict


class returnsForOptimisationWithCosts(object):
    def __init__(self, account_curve_group: accountCurveGroup):
        self._from_account_curve_group_to_returns_for_optimisation(account_curve_group)

    def _from_account_curve_group_to_returns_for_optimisation(
        self, account_curve_group: accountCurveGroup
    ):
        for type in ["gross", "costs"]:
            account_curve = getattr(account_curve_group, type).to_frame()

            account_curve = account_curve.resample("1B").sum()

            # avoid understating vol
            account_curve[account_curve == 0.0] = np.nan

            setattr(self, type, account_curve)

    def get_annual_SR_dict(self, type="gross") -> dictOfSR:
        relevant_curve = getattr(self, type)
        list_of_columns = list(relevant_curve.columns)
        SR_dict = dict(
            [
                (
                    column_name,
                    _get_annual_SR_for_returns_for_optimisation(
                        self, column_name, type=type
                    ),
                )
                for column_name in list_of_columns
            ]
        )

        SR_dict = dictOfSR(SR_dict)

        return SR_dict


def _turn_singular_account_curve_into_dict(dict_of_returns) -> dict:
    if _singular_account_curve(dict_of_returns):
        return {SINGLE_NAME: dict_of_returns}
    else:
        return dict_of_returns


def _singular_account_curve(dict_of_returns) -> bool:
    if type(dict_of_returns) is not dict:
        return True
    else:
        return False


def _get_annual_SR_for_returns_for_optimisation(
    returns_for_optimisation: returnsForOptimisationWithCosts,
    column_name: str,
    type: str = "gross",
) -> float:
    gross_curve = returns_for_optimisation.gross[column_name]
    if type == "gross":
        daily_return = gross_curve.mean()
    elif type == "costs":
        cost_curve = returns_for_optimisation.costs[column_name]
        daily_return = cost_curve.mean()
    else:
        raise Exception()

    daily_std = gross_curve.std()

    return annual_SR_from_daily_returns(daily_return, daily_std)


def annual_SR_from_daily_returns(daily_return, daily_std):
    return ROOT_BDAYS_INYEAR * daily_return / daily_std
