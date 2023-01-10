from systems.accounts.curves.account_curve_group import accountCurveGroup
from systems.accounts.curves.dict_of_account_curves import nestedDictOfAccountCurves

from syscore.dateutils import Frequency

from systems.accounts.pandl_calculators.pandl_generic_costs import (
    NET_CURVE,
    GROSS_CURVE,
    COSTS_CURVE,
)


class nestedAccountCurveGroup(accountCurveGroup):
    def __init__(
        self,
        nested_dict_of_account_curves: nestedDictOfAccountCurves,
        capital,
        **kwargs,
    ):

        super().__init__(nested_dict_of_account_curves, capital=capital, **kwargs)

        self._nested_dict_of_account_curves = nested_dict_of_account_curves

    def __getitem__(self, item) -> accountCurveGroup:
        return self.get_account_curve_dict_for_item(item)

    def get_account_curve_dict_for_item(self, item: str) -> accountCurveGroup:
        return self.nested_account_curves[item]

    ## TO RETURN A 'NEW' ACCOUNT CURVE GROUP
    @property
    def gross(self):
        kwargs = self.kwargs_without_item("curve_type")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            curve_type=GROSS_CURVE,
            **kwargs,
        )

    @property
    def net(self):
        kwargs = self.kwargs_without_item("curve_type")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            curve_type=NET_CURVE,
            **kwargs,
        )

    @property
    def costs(self):
        kwargs = self.kwargs_without_item("curve_type")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            curve_type=COSTS_CURVE,
            **kwargs,
        )

    @property
    def daily(self):
        kwargs = self.kwargs_without_item("frequency")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            frequency=Frequency.BDay,
            **kwargs,
        )

    @property
    def weekly(self):
        kwargs = self.kwargs_without_item("frequency")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            frequency=Frequency.Week,
            **kwargs,
        )

    @property
    def monthly(self):
        kwargs = self.kwargs_without_item("frequency")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            frequency=Frequency.Month,
            **kwargs,
        )

    @property
    def annual(self):
        kwargs = self.kwargs_without_item("frequency")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            frequency=Frequency.Year,
            **kwargs,
        )

    @property
    def percent(self):
        kwargs = self.kwargs_without_item("is_percentage")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            is_percentage=True,
            **kwargs,
        )

    @property
    def value_terms(self):
        kwargs = self.kwargs_without_item("is_percentage")
        return nestedAccountCurveGroup(
            self.nested_account_curves,
            capital=self.capital,
            is_percentage=False,
            **kwargs,
        )

    @property
    def nested_account_curves(self) -> nestedDictOfAccountCurves:
        return self._nested_dict_of_account_curves
