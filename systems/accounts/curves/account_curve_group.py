from copy import copy
import pandas as pd

from syscore.dateutils import Frequency

from systems.accounts.curves.account_curve import accountCurve
from systems.accounts.curves.dict_of_account_curves import dictOfAccountCurves
from systems.accounts.pandl_calculators.pandl_generic_costs import (
    GROSS_CURVE,
    NET_CURVE,
    COSTS_CURVE,
)
from systems.accounts.curves.stats_dict import statsDict


class accountCurveGroup(accountCurve):
    def __init__(self, dict_of_account_curves: dictOfAccountCurves, capital, **kwargs):

        total_pandl_calculator = dict_of_account_curves.summed_pandl_calculator(
            capital=capital
        )
        super().__init__(total_pandl_calculator, **kwargs)

        self._dict_of_account_curves = dict_of_account_curves
        self._kwargs = _kwargs_with_defaults(kwargs)

    @property
    def asset_columns(self):
        return list(self.dict_of_account_curves.keys())

    def __getitem__(self, item):
        kwargs = self.kwargs
        return accountCurve(self.get_pandl_calculator_for_item(item), **kwargs)

    def get_pandl_calculator_for_item(self, item: str):
        return self.dict_of_account_curves[item].pandl_calculator_with_costs

    def to_frame(self) -> pd.DataFrame:
        asset_columns = self.asset_columns
        data_as_list = [self[asset_name] for asset_name in asset_columns]
        data_as_pd = pd.concat(data_as_list, axis=1)
        data_as_pd.columns = asset_columns

        return data_as_pd

    def get_stats(
        self, stat_name: str, curve_type: str = "net", freq: str = "daily"
    ) -> statsDict:

        return statsDict(self, item=stat_name, freq=freq, curve_type=curve_type)

    ## TO RETURN A 'NEW' ACCOUNT CURVE GROUP
    @property
    def gross(self):
        kwargs = self.kwargs_without_item("curve_type")
        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            curve_type=GROSS_CURVE,
            **kwargs,
        )

    @property
    def net(self):
        kwargs = self.kwargs_without_item("curve_type")

        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            curve_type=NET_CURVE,
            **kwargs,
        )

    @property
    def costs(self):
        kwargs = self.kwargs_without_item("curve_type")
        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            curve_type=COSTS_CURVE,
            **kwargs,
        )

    @property
    def daily(self):
        kwargs = self.kwargs_without_item("frequency")
        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            frequency=Frequency.BDay,
            **kwargs,
        )

    @property
    def weekly(self):
        kwargs = self.kwargs_without_item("frequency")
        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            frequency=Frequency.Week,
            **kwargs,
        )

    @property
    def monthly(self):
        kwargs = self.kwargs_without_item("frequency")
        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            frequency=Frequency.Month,
            **kwargs,
        )

    @property
    def annual(self):
        kwargs = self.kwargs_without_item("frequency")
        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            frequency=Frequency.Year,
            **kwargs,
        )

    @property
    def percent(self):
        kwargs = self.kwargs_without_item("is_percentage")
        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            is_percentage=True,
            **kwargs,
        )

    @property
    def value_terms(self):
        kwargs = self.kwargs_without_item("is_percentage")
        return accountCurveGroup(
            self.dict_of_account_curves,
            capital=self.capital,
            is_percentage=False,
            **kwargs,
        )

    @property
    def dict_of_account_curves(self) -> dictOfAccountCurves:
        return self._dict_of_account_curves

    def kwargs_without_item(self, itemname):
        kwargs = copy(self.kwargs)
        kwargs.pop(itemname)

        return kwargs

    @property
    def kwargs(self) -> dict:
        return self._kwargs


def _kwargs_with_defaults(kwargs: dict) -> dict:
    if "frequency" not in kwargs:
        kwargs["frequency"] = Frequency.BDay
    if "curve_type" not in kwargs:
        kwargs["curve_type"] = NET_CURVE
    if "is_percentage" not in kwargs:
        kwargs["is_percentage"] = False
    if "weighted" not in kwargs:
        kwargs["weighted"] = False

    return kwargs
