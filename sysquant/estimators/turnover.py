from sysquant.returns import SINGLE_NAME


class turnoverDataForAGroupOfItems(dict):
    pass


class turnoverDataAcrossAssets(dict):
    # dict of turnoverDataForAGroupOfItems
    @classmethod
    def from_single_asset(
        turnoverDataAcrossAssets, turnover_data: turnoverDataForAGroupOfItems
    ):
        turnover_dict = {SINGLE_NAME: turnover_data}
        return turnoverDataAcrossAssets(turnover_dict)


class turnoverDataForTradingRule(turnoverDataForAGroupOfItems):
    pass


class turnoverDataAcrossTradingRules(turnoverDataAcrossAssets):
    # dict of turnoverDataForTradingRule
    pass


class turnoverDataAcrossSubsystems(turnoverDataAcrossAssets):
    def __init__(self, turnover_data: dict):
        turnover_dict = {SINGLE_NAME: turnover_data}

        super().__init__(turnover_dict)
