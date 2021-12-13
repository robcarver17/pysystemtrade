import numpy as np


from sysquant.returns import (
    dictOfReturnsForOptimisationWithCosts,
    dictOfSRacrossAssets,
    dictOfSR,
    dictOfReturnsForOptimisation,
    SINGLE_NAME,
)
from sysquant.estimators.turnover import turnoverDataForAGroupOfItems


class returnsPreProcessor(object):
    def __init__(
        self,
        dict_of_returns: dictOfReturnsForOptimisationWithCosts,
        log,
        turnovers: turnoverDataForAGroupOfItems,
        frequency: str = "W",
        pool_gross_returns: bool = True,
        use_pooled_costs: bool = False,
        use_pooled_turnover: bool = True,
        equalise_gross: bool = False,
        cost_multiplier: float = 1.0,
        **_ignored_kwargs,
    ):

        self._dict_of_returns = dict_of_returns

        self._frequency = frequency
        self._pool_gross_returns = pool_gross_returns
        self._use_pooled_costs = use_pooled_costs
        self._use_pooled_turnover = use_pooled_turnover
        self._cost_multiplier = cost_multiplier
        self._turnovers = turnovers
        self._log = log
        self._equalise_gross = equalise_gross

    # PROPERTIES
    @property
    def log(self):
        return self._log

    @property
    def turnovers(self) -> turnoverDataForAGroupOfItems:
        return self._turnovers

    @property
    def dict_of_returns(self) -> dictOfReturnsForOptimisationWithCosts:
        return self._dict_of_returns

    @property
    def list_of_asset_names(self) -> list:
        return list(self.dict_of_returns.keys())

    @property
    def pool_gross_returns(self) -> bool:
        if self.singular_account_curve:
            return False
        return self._pool_gross_returns

    @property
    def use_pooled_costs(self) -> bool:
        if self.singular_account_curve:
            return False
        return self._use_pooled_costs

    @property
    def use_pooled_turnover(self) -> bool:
        if self.singular_account_curve:
            return False
        return self._use_pooled_turnover

    @property
    def cost_multiplier(self) -> float:
        return self._cost_multiplier

    @property
    def equalise_gross(self) -> bool:
        return self._equalise_gross

    @property
    def length_adjustment(self) -> int:
        ## Used if gross returns are pooled, to ensure estimators are consistent
        return getattr(self, "_length_adjustment", 1)

    @property
    def frequency(self) -> str:
        return self._frequency

    @property
    def singular_account_curve(self) -> bool:
        return len(self.dict_of_returns) == 1

    ## METHODS
    def get_net_returns(self, asset_name: str = SINGLE_NAME):
        net_returns_dict = self.get_dict_of_net_returns(asset_name)

        net_returns = net_returns_dict.single_resampled_set_of_returns(self.frequency)

        return net_returns

    def get_dict_of_net_returns(
        self, asset_name: str = SINGLE_NAME
    ) -> dictOfReturnsForOptimisation:
        gross_returns_dict = self.get_gross_returns_for_asset_name(asset_name)
        dict_of_SR_costs = self.get_dict_of_multiplied_cost_SR_for_asset_name(
            asset_name
        )

        net_returns_dict = gross_returns_dict.adjust_returns_for_SR_costs(
            dict_of_SR_costs
        )

        return net_returns_dict

    def get_gross_returns_for_asset_name(
        self, asset_name: str
    ) -> dictOfReturnsForOptimisation:
        gross_returns_dict = self.get_gross_returns_for_asset_name_before_equalisation(
            asset_name
        )
        if self.equalise_gross:
            gross_returns_dict.equalise_returns()

        return gross_returns_dict

    def get_gross_returns_for_asset_name_before_equalisation(
        self, asset_name: str
    ) -> dictOfReturnsForOptimisation:

        if self.pool_gross_returns:
            return self.get_pooled_gross_returns_dict()
        else:
            return self.get_unpooled_gross_returns_dict_for_asset_name(asset_name)

    def get_pooled_gross_returns_dict(self) -> dictOfReturnsForOptimisation:
        self.log.msg("Using pooled gross returns")
        dict_of_returns = self.dict_of_returns

        gross_returns_dict = dict_of_returns.get_returns_for_all_assets()

        return gross_returns_dict

    def get_unpooled_gross_returns_dict_for_asset_name(
        self, asset_name: str
    ) -> dictOfReturnsForOptimisation:
        self.log.msg("Using only returns of %s for gross returns" % asset_name)

        gross_returns_dict = self.dict_of_returns.get_returns_for_asset_as_single_dict(
            asset_name, type="gross"
        )

        return gross_returns_dict

    def get_dict_of_multiplied_cost_SR_for_asset_name(
        self, asset_name: str
    ) -> dictOfSR:
        dict_of_cost_SR = self.get_dict_of_unadjusted_cost_SR_for_asset_name(asset_name)
        cost_multiplier = self.cost_multiplier
        if cost_multiplier != 1.0:
            self.log.msg("Applying cost multiplier of %f" % cost_multiplier)
            dict_of_cost_SR = dict_of_cost_SR.apply_cost_multiplier(
                cost_multiplier=cost_multiplier
            )

        return dict_of_cost_SR

    def get_dict_of_unadjusted_cost_SR_for_asset_name(
        self, asset_name: str
    ) -> dictOfSR:
        if self.use_pooled_costs:
            return self.get_dict_of_pooled_SR_costs(asset_name)

        elif self.use_pooled_turnover:
            return self.get_pooled_SR_costs_using_turnover(asset_name)

        else:
            return self.get_unpooled_cost_SR_for_asset_name(asset_name)

    def get_dict_of_pooled_SR_costs(self, asset_name: str) -> dictOfSR:
        self.log.msg("Using pooled cost SR")

        dict_of_costs = self.get_dict_of_cost_dicts_by_asset_name()

        pooled_dict_of_costs = dict_of_costs.get_pooled_SR(asset_name)

        return pooled_dict_of_costs

    def get_pooled_SR_costs_using_turnover(self, asset_name: str) -> dictOfSR:
        self.log.msg("Using pooled turnover cost SR for %s" % asset_name)
        ## Costs we use are: costs for our instrument, multiplied by average turnover across instruments
        dict_of_costs = self.get_dict_of_cost_dicts_by_asset_name()

        # a dict, keys are forecasts, each entry is a list ordered by instrument code
        turnovers = self.turnovers
        costs = _calculate_pooled_turnover_costs(
            asset_name, turnovers=turnovers, dict_of_costs=dict_of_costs
        )

        return costs

    def get_unpooled_cost_SR_for_asset_name(self, asset_name) -> dictOfSR:
        self.log.msg("Using unpooled cost SR for %s" % asset_name)

        costs = self.dict_of_returns.get_annual_SR_dict_for_asset(
            asset_name, type="costs"
        )

        return costs

    def get_dict_of_cost_dicts_by_asset_name(self) -> dictOfSRacrossAssets:
        dict_of_returns = self.dict_of_returns
        dict_of_costs = dict_of_returns.dict_of_SR("costs")
        return dict_of_costs


def _calculate_pooled_turnover_costs(
    asset_name: str, turnovers: dict, dict_of_costs: dictOfSRacrossAssets
) -> dictOfSR:

    column_names = turnovers.keys()
    column_SR_dict = dict(
        [
            (
                column,
                _calculate_pooled_turnover_cost_for_column(
                    asset_name,
                    turnovers=turnovers,
                    column_name=column,
                    dict_of_costs=dict_of_costs,
                ),
            )
            for column in column_names
        ]
    )

    column_SR_dict = dictOfSR(column_SR_dict)

    return column_SR_dict


def _calculate_pooled_turnover_cost_for_column(
    asset_name: str, turnovers: dict, dict_of_costs: dict, column_name
) -> float:

    cost_per_turnover_this_asset = _calculate_cost_per_turnover(
        asset_name,
        column_name=column_name,
        dict_of_costs=dict_of_costs,
        turnovers=turnovers,
    )

    average_turnover_across_assets = _average_turnover(turnovers, column_name)

    return cost_per_turnover_this_asset * average_turnover_across_assets


def _average_turnover(turnovers, column_name):
    all_turnovers = turnovers[column_name]
    return np.nanmean(list(all_turnovers.values()))


def _calculate_cost_per_turnover(
    asset_name: str, column_name: str, turnovers: dict, dict_of_costs: dict
):

    turnover = _turnover_for_asset_and_column(asset_name, column_name, turnovers)
    if turnover > 0:
        cost = _cost_for_asset_and_column(asset_name, column_name, dict_of_costs)
        return cost / turnover
    else:
        print(
            f"No turnover for asset:rule combination {asset_name}:{column_name} in sysquant.optimisation.pre_processing._calculate_cost_per_turnover"
        )
        return np.nan


def _turnover_for_asset_and_column(asset_name: str, column_name: str, turnovers: dict):

    return turnovers[column_name][asset_name]


def _cost_for_asset_and_column(asset_name: str, column_name: str, dict_of_costs: dict):

    return dict_of_costs[asset_name][column_name]
