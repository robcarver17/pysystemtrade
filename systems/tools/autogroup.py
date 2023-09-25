from syscore.genutils import list_intersection
from syscore.constants import arg_not_supplied
from typing import Union
from copy import copy

WEIGHT_FLAG = "weight"
APPROX_IDM_PARAMETER = "use_approx_DM"


def calculate_autogroup_weights_given_parameters(
    auto_group_weights: dict,
    auto_group_parameters: dict = arg_not_supplied,
    keys_to_exclude: list = arg_not_supplied,
) -> dict:
    ## Example:
    """
    auto_group_weights = dict(trendy = dict(weight=.7,
                               accel=dict(weight=.3, accel1=.5, accel2=.5),
                               mom=dict(weight=.7, mom1=1.0)),
    carry = dict(weight=.3, carry1=1.0))
    """
    if keys_to_exclude is arg_not_supplied:
        keys_to_exclude = []

    tree_of_weights = autoGroupPortfolioWeight(
        auto_group_weights=auto_group_weights,
        auto_group_parameters=auto_group_parameters,
    )
    tree_of_weights.remove_excluded_keys_and_reweight(keys_to_exclude)

    tree_of_weights.resolve_weights()

    collapsed_weights = _collapse_tree_of_weights(tree_of_weights)

    return collapsed_weights


class autoGroupPortfolioWeight(dict):
    def __init__(
        self, auto_group_weights: dict, auto_group_parameters: dict = arg_not_supplied
    ):

        copy_auto_group_weights = copy(auto_group_weights)
        group_weight = copy_auto_group_weights.pop(WEIGHT_FLAG, 1.0)
        auto_group_weights_without_weight_entry = copy_auto_group_weights

        super().__init__(auto_group_weights_without_weight_entry)

        self.group_weight = group_weight
        if auto_group_parameters is arg_not_supplied:
            auto_group_parameters = {}
        self._parameters = auto_group_parameters

        ## Must call on __init__ or does_not_contain_portfolio will fail
        self._create_tree_below()

    def _create_tree_below(self):
        ## Always call on __init__
        for key, value in self.items():
            if type(value) is dict:
                self[key] = autoGroupPortfolioWeight(value, self.parameters)

    def remove_excluded_keys_and_reweight(self, keys_to_exclude: list):
        if self.contains_portfolios:
            self._remove_excluded_keys_and_reweight_over_subportfolios(keys_to_exclude)
        else:
            self._remove_excluded_keys_and_reweight_for_atomic_portfolio(
                keys_to_exclude
            )

        ## Need to deal with completely empty dicts

    def resolve_weights(self, level: int = 1, cumulative_multiplier: float = 1.0):
        if self.already_weighted:
            raise Exception("Can't resolve weights more than once")

        approx_dm = self._approx_dm_if_required(level)
        group_weight = self.group_weight
        new_multiplier = cumulative_multiplier * approx_dm * group_weight

        if self.contains_portfolios:
            self._resolve_weights_with_subportfolios(
                level=level, cumulative_multiplier=new_multiplier
            )
        else:
            self._resolve_weights_for_atomic_portfolio(
                cumulative_multiplier=new_multiplier
            )

        self.flag_as_weighted()

    def _remove_excluded_keys_and_reweight_over_subportfolios(
        self, keys_to_exclude: list
    ):
        for sub_portfolio in self.sub_portfolios():
            sub_portfolio.remove_excluded_keys_and_reweight(keys_to_exclude)
        ## remove empty portfolios and reweight
        self._remove_empty_portfolios_one_level_down_and_reweight()

    def _remove_excluded_keys_and_reweight_for_atomic_portfolio(
        self, keys_to_exclude: list
    ):
        ## eg if we had a=.3, b=.4, c=.3 and we lost c
        keys_to_remove = list_intersection(keys_to_exclude, self.list_of_keys)
        for key in keys_to_remove:
            self.pop(key)

        self.reweight_atomic_portfolio()

    def _resolve_weights_with_subportfolios(
        self, level: int, cumulative_multiplier: float
    ):
        new_level = level + 1
        for sub_portfolio in self.sub_portfolios():
            sub_portfolio.resolve_weights(
                level=new_level, cumulative_multiplier=cumulative_multiplier
            )

    def _resolve_weights_for_atomic_portfolio(self, cumulative_multiplier: float):
        self._apply_multiplier_to_atomic_portfolio(cumulative_multiplier)

    def _approx_dm_if_required(self, level: int) -> float:
        if self.use_approx_dm:
            ## At top level we assume zero correlation, at lower levels correlation will rise
            ##   and DM will get smaller
            size = len(self)
            approx_dm = size ** (0.5 / level)
        else:
            approx_dm = 1.0

        return approx_dm

    def reweight_atomic_portfolio(self):
        if self.is_empty:
            pass
        else:
            total_weight = self.total_weight_in_atomic_portfolio
            self._apply_multiplier_to_atomic_portfolio(1.0 / total_weight)

    def _apply_multiplier_to_atomic_portfolio(self, multiplier: float):
        assert self.does_not_contain_portfolios
        for key, value in self.items():
            self[key] = value * multiplier

    def _remove_empty_portfolios_one_level_down_and_reweight(self):
        assert self.contains_portfolios
        ## not recursive so has to be called within a recursive
        initial_list_of_keys = self.list_of_keys
        for key in initial_list_of_keys:
            sub_portfolio = self[key]
            if sub_portfolio.is_empty:
                self.pop(key)

        self._reweight_subportfolios()

    def _reweight_subportfolios(self):
        if self.is_empty:
            pass
        else:
            total_weight = self.total_weight_of_subportfolios
            self._apply_multiplier_to_subportfolios(1.0 / total_weight)

    def _apply_multiplier_to_subportfolios(self, multiplier: float):
        for sub_portfolio in self.sub_portfolios():
            sub_portfolio.group_weight = sub_portfolio.group_weight * multiplier

    @property
    def total_weight_of_subportfolios(self) -> float:
        assert self.contains_portfolios
        total_weight_in_portfolio = sum(
            [sub_portfolio.group_weight for sub_portfolio in self.sub_portfolios()]
        )
        return total_weight_in_portfolio

    def sub_portfolios(self) -> list:
        assert self.contains_portfolios
        return list(self.values())

    @property
    def total_weight_in_atomic_portfolio(self) -> float:
        assert self.does_not_contain_portfolios
        total_weight_in_portfolio = sum(self.values())
        return total_weight_in_portfolio

    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    @property
    def list_of_keys(self) -> list:
        return list(self.keys())

    @property
    def use_approx_dm(self) -> bool:
        return self.parameters.get(APPROX_IDM_PARAMETER, False)

    @property
    def parameters(self) -> dict:
        return self._parameters

    @property
    def does_not_contain_portfolios(self) -> bool:
        return not self.contains_portfolios

    @property
    def contains_portfolios(self) -> bool:
        ## low level
        any_portfolios_in_self = any(
            [type(value) is autoGroupPortfolioWeight for value in self.values()]
        )
        return any_portfolios_in_self

    @property
    def group_weight(self) -> float:
        return self._group_weight

    @group_weight.setter
    def group_weight(self, group_weight):
        self._group_weight = group_weight

    @property
    def already_weighted(self) -> bool:
        return getattr(self, "_already_weighted", False)

    def flag_as_weighted(self):
        self._already_weighted = True

    def __repr__(self):
        return "Group weight %f: %s " % (self.group_weight, str(dict(self)))


def _collapse_tree_of_weights(
    tree_of_weights: autoGroupPortfolioWeight,
) -> autoGroupPortfolioWeight:
    weights_as_dict = {}
    for key, sub_portfolio in tree_of_weights.items():
        if sub_portfolio.contains_portfolios:
            weights_this_sub_portfolio = _collapse_tree_of_weights(sub_portfolio)
        else:
            weights_this_sub_portfolio = dict(sub_portfolio)

        weights_as_dict.update(weights_this_sub_portfolio)

    return weights_as_dict


AUTO_WEIGHTING_FLAG = "auto_weight_from_grouping"
AUTO_WEIGHTING_PARAMETERS = "parameters"
AUTO_WEIGHTING_GROUP_LABEL = "groups"


def config_is_auto_group(forecast_weights_config: dict) -> bool:
    flag = forecast_weights_config.get(AUTO_WEIGHTING_FLAG, None)
    auto_weighting_flag_in_config_dict = flag is not None

    return auto_weighting_flag_in_config_dict


def resolve_config_into_parameters_and_weights_for_autogrouping(
    forecast_weights_config: dict,
) -> tuple:
    try:
        auto_group_config = copy(forecast_weights_config[AUTO_WEIGHTING_FLAG])
        auto_group_parameters = auto_group_config.pop(AUTO_WEIGHTING_PARAMETERS)
        auto_group_weights = auto_group_config.pop(AUTO_WEIGHTING_GROUP_LABEL)
    except:
        error_msg = "Auto weighting should contain two elements: %s and %s" % (
            AUTO_WEIGHTING_PARAMETERS,
            AUTO_WEIGHTING_GROUP_LABEL,
        )
        raise Exception(error_msg)

    return auto_group_parameters, auto_group_weights
