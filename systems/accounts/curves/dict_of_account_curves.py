from systems.accounts.curves.account_curve import accountCurve
from systems.accounts.pandl_calculators.pandl_calculation_dict import (
    dictOfPandlCalculatorsWithGenericCosts,
    pandlCalculationWithoutPositions,
)


class dictOfAccountCurves(dict):
    def summed_pandl_calculator(self, capital) -> pandlCalculationWithoutPositions:
        dict_of_pandl_calculators = self.dict_of_pandl_calculators()
        summed_pandl_calculator = dict_of_pandl_calculators.sum(capital=capital)

        return summed_pandl_calculator

    def dict_of_pandl_calculators(self) -> dictOfPandlCalculatorsWithGenericCosts:
        dict_of_pandl_calculators = dict(
            [
                (asset_name, account_curve.pandl_calculator_with_costs)
                for asset_name, account_curve in self.items()
            ]
        )

        return dictOfPandlCalculatorsWithGenericCosts(dict_of_pandl_calculators)

    @property
    def asset_columns(self) -> list:
        return list(self.keys())

    @property
    def weighted(self) -> bool:
        weighted_list = [acurve.weighted for acurve in self.values()]
        if all(weighted_list):
            return True
        if all(~weighted_list):
            return False
        raise Exception(
            "Can't have a dict of account curves where some are weighted and some are unweighted"
        )


class nestedDictOfAccountCurves(dictOfAccountCurves):
    pass
