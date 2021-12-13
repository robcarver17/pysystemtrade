import pandas as pd

from syscore.genutils import progressBar

from syslogdiag.log_to_screen import logtoscreen, logger

from sysquant.fitting_dates import generate_fitting_dates, listOfFittingDates
from sysquant.optimisation.portfolio_optimiser import portfolioOptimiser
from sysquant.returns import returnsForOptimisation


class optimiseWeightsOverTime(object):
    def __init__(
        self,
        net_returns: returnsForOptimisation,
        date_method="expanding",
        rollyears=20,
        log: logger = logtoscreen("optimiser"),
        **kwargs
    ):

        # Generate time periods
        fit_dates = generate_fitting_dates(
            net_returns, date_method=date_method, rollyears=rollyears
        )

        optimiser_for_one_period = portfolioOptimiser(net_returns, log=log, **kwargs)

        self._fit_dates = fit_dates
        self._optimiser = optimiser_for_one_period

    @property
    def fit_dates(self) -> listOfFittingDates:
        return self._fit_dates

    @property
    def optimiser(self) -> portfolioOptimiser:
        return self._optimiser

    def weights(self) -> pd.DataFrame:
        fit_dates = self.fit_dates
        optimiser = self.optimiser

        progress = progressBar(len(fit_dates), "Optimising weights")

        weight_list = []
        # Now for each time period, estimate weights
        for fit_period in fit_dates:
            progress.iterate()
            weight_dict = optimiser.calculate_weights_for_period(fit_period)
            weight_list.append(weight_dict)

        weight_index = fit_dates.list_of_starting_periods()
        weights = pd.DataFrame(weight_list, index=weight_index)

        return weights
