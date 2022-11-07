import pandas as pd
import numpy as np
from scipy.stats import skew, ttest_1samp, norm

from syscore.dateutils import Frequency, from_frequency_to_times_per_year
from syscore.pdutils import drawdown

from systems.accounts.pandl_calculators.pandl_generic_costs import (
    GROSS_CURVE,
    NET_CURVE,
    COSTS_CURVE,
    pandlCalculationWithGenericCosts,
)

QUANT_PERCENTILE_EXTREME = 0.01
QUANT_PERCENTILE_STD = 0.3
NORMAL_DISTR_RATIO = norm.ppf(QUANT_PERCENTILE_EXTREME) / norm.ppf(QUANT_PERCENTILE_STD)


class accountCurve(pd.Series):
    def __init__(
        self,
        pandl_calculator_with_costs: pandlCalculationWithGenericCosts,
        frequency: Frequency = Frequency.BDay,
        curve_type: str = NET_CURVE,
        is_percentage: bool = False,
        weighted=False,
    ):

        as_pd_series = pandl_calculator_with_costs.as_pd_series_for_frequency(
            percent=is_percentage, curve_type=curve_type, frequency=frequency
        )

        super().__init__(as_pd_series)

        self._as_ts = as_pd_series
        self._pandl_calculator_with_costs = pandl_calculator_with_costs
        self._frequency = frequency  ## frequency type
        self._curve_type = curve_type
        self._is_percentage = is_percentage
        self._weighted = weighted

    def __repr__(self):
        if self.weighted:
            weight_comment = "Weighted"
        else:
            weight_comment = "Unweighted"

        return (
            super().__repr__()
            + "\n %s account curve; use object.stats() to see methods" % weight_comment
        )


    def weight(self, weight: pd.Series):
        pandl_calculator = self.pandl_calculator_with_costs
        weighted_pandl_calculator = pandl_calculator.weight(weight)

        return accountCurve(
            weighted_pandl_calculator,
            curve_type=self.curve_type,
            is_percentage=self.is_percentage,
            frequency=self.frequency,
            weighted=True,
        )

    ## TO RETURN A 'NEW' ACCOUNT CURVE
    @property
    def gross(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=GROSS_CURVE,
            is_percentage=self.is_percentage,
            frequency=self.frequency,
            weighted=self.weighted,
        )

    @property
    def net(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=NET_CURVE,
            is_percentage=self.is_percentage,
            frequency=self.frequency,
            weighted=self.weighted,
        )

    @property
    def costs(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=COSTS_CURVE,
            is_percentage=self.is_percentage,
            frequency=self.frequency,
            weighted=self.weighted,
        )

    @property
    def daily(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=self.curve_type,
            is_percentage=self.is_percentage,
            frequency=Frequency.BDay,
            weighted=self.weighted,
        )

    @property
    def weekly(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=self.curve_type,
            is_percentage=self.is_percentage,
            frequency=Frequency.Week,
            weighted=self.weighted,
        )

    @property
    def monthly(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=self.curve_type,
            is_percentage=self.is_percentage,
            frequency=Frequency.Month,
            weighted=self.weighted,
        )

    @property
    def annual(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=self.curve_type,
            is_percentage=self.is_percentage,
            frequency=Frequency.Year,
            weighted=self.weighted,
        )

    @property
    def percent(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=self.curve_type,
            is_percentage=True,
            frequency=self.frequency,
            weighted=self.weighted,
        )

    @property
    def value_terms(self):
        return accountCurve(
            self.pandl_calculator_with_costs,
            curve_type=self.curve_type,
            is_percentage=False,
            frequency=self.frequency,
            weighted=self.weighted,
        )

    def to_ncg_frame(self) -> pd.DataFrame:
        gross = self.gross
        costs = self.costs
        net = self.net

        as_df = pd.concat([gross, costs, net], axis=1)
        as_df.columns = [GROSS_CURVE, COSTS_CURVE, NET_CURVE]

        return as_df

    @property
    def length_in_months(self) -> int:
        return self.pandl_calculator_with_costs.length_in_months

    @property
    def capital(self) -> pd.Series:
        return self.pandl_calculator_with_costs.capital_as_pd_series_for_frequency(
            self.frequency
        )

    @property
    def pandl_calculator_with_costs(self) -> pandlCalculationWithGenericCosts:
        return self._pandl_calculator_with_costs

    @property
    def as_ts(self) -> pd.Series:
        return self._as_ts

    @property
    def frequency(self) -> str:
        return self._frequency

    @property
    def curve_type(self) -> str:
        return self._curve_type

    @property
    def is_percentage(self) -> bool:
        return self._is_percentage

    @property
    def weighted(self) -> bool:
        return self._weighted

    def curve(self):
        return self.cumsum().ffill()

    def mean(self):
        return float(self.as_ts.mean())

    def std(self):
        return float(self.as_ts.std())

    def ann_mean(self):
        ## If nans, then mean will be biased upwards
        total = self.sum()
        divisor = self.number_of_years_in_data

        return total / divisor

    def ann_std(self):
        period_std = self.std()

        return period_std * self.vol_scalar

    @property
    def number_of_years_in_data(self) -> float:
        return len(self) / self.returns_scalar

    @property
    def returns_scalar(self) -> float:
        return from_frequency_to_times_per_year(self.frequency)

    @property
    def vol_scalar(self) -> float:
        times_per_year = from_frequency_to_times_per_year(self.frequency)
        return times_per_year ** 0.5

    def sharpe(self):
        mean_return = self.ann_mean()
        vol = self.ann_std()
        try:
            sharpe = mean_return / vol
        except ZeroDivisionError:
            sharpe = np.nan
        return sharpe

    def drawdown(self):
        x = self.curve()
        return drawdown(x)

    def avg_drawdown(self):
        dd = self.drawdown()
        return np.nanmean(dd.values)

    def worst_drawdown(self):
        dd = self.drawdown()
        return np.nanmin(dd.values)

    def time_in_drawdown(self):
        dd = self.drawdown().dropna()
        in_dd = float(dd[dd < 0].shape[0])
        return in_dd / float(dd.shape[0])

    def calmar(self):
        return self.ann_mean() / -self.worst_drawdown()

    def avg_return_to_drawdown(self):
        return self.ann_mean() / -self.avg_drawdown()

    def sortino(self):
        period_stddev = np.std(self.losses())

        ann_stdev = period_stddev * self.vol_scalar
        ann_mean = self.ann_mean()

        try:
            sortino = ann_mean / ann_stdev
        except ZeroDivisionError:
            sortino = np.nan

        return sortino

    def vals(self):
        vals = self.values[~np.isnan(self.values)]

        return vals

    ## added args, kwargs for consistency with parent method
    def min(self, *args, **kwargs):
        return np.nanmin(self)

    ## added args, kwargs for consistency with parent method
    def max(self, *args, **kwargs):
        return np.nanmax(self)

    def median(self):
        return np.nanmedian(self)

    def skew(self):
        return skew(self.vals())

    def losses(self):
        x = self.vals()
        return x[x < 0]

    def gains(self):
        x = self.vals()
        return x[x > 0]

    def avg_loss(self):
        return np.mean(self.losses())

    def avg_gain(self):
        return np.mean(self.gains())

    def gaintolossratio(self):
        return self.avg_gain() / -self.avg_loss()

    def profitfactor(self):
        return np.sum(self.gains()) / -np.sum(self.losses())

    def hitrate(self):
        no_gains = float(self.gains().shape[0])
        no_losses = float(self.losses().shape[0])
        return no_gains / (no_losses + no_gains)

    def rolling_ann_std(self, window=40):
        y = self.as_ts.rolling(window, min_periods=4, center=True).std().to_frame()
        return y * self.vol_scalar

    def t_test(self):
        return ttest_1samp(self.vals(), 0.0)

    def t_stat(self):
        return float(self.t_test()[0])

    def p_value(self):
        return float(self.t_test()[1])

    def average_quant_ratio(self):
        upper = self.quant_ratio_upper()
        lower = self.quant_ratio_lower()

        return np.mean([upper, lower])

    def quant_ratio_lower(self):
        return quant_ratio_lower_curve(self)

    def quant_ratio_upper(self):
        return quant_ratio_upper_curve(self)

    def demeaned_remove_zeros(self):
        x = self.as_ts
        return demeaned_remove_zeros(x)

    def stats(self):

        stats_list = [
            "min",
            "max",
            "median",
            "mean",
            "std",
            "skew",
            "ann_mean",
            "ann_std",
            "sharpe",
            "sortino",
            "avg_drawdown",
            "time_in_drawdown",
            "calmar",
            "avg_return_to_drawdown",
            "avg_loss",
            "avg_gain",
            "gaintolossratio",
            "profitfactor",
            "hitrate",
            "t_stat",
            "p_value",
        ]

        build_stats = []
        for stat_name in stats_list:
            stat_method = getattr(self, stat_name)
            ans = stat_method()
            build_stats.append((stat_name, "{0:.4g}".format(ans)))

        comment1 = (
            "You can also plot / print:",
            ["rolling_ann_std", "drawdown", "curve", "percent"],
        )

        return [build_stats, comment1]


def quant_ratio_lower_curve(x: pd.Series):
    demeaned_x = demeaned_remove_zeros(x)
    raw_ratio = demeaned_x.quantile(QUANT_PERCENTILE_EXTREME) / demeaned_x.quantile(
        QUANT_PERCENTILE_STD
    )
    return raw_ratio / NORMAL_DISTR_RATIO

def quant_ratio_upper_curve(x: pd.Series):
    demeaned_x = demeaned_remove_zeros(x)
    raw_ratio = demeaned_x.quantile(1 - QUANT_PERCENTILE_EXTREME) / demeaned_x.quantile(
        1 - QUANT_PERCENTILE_STD
    )
    return raw_ratio / NORMAL_DISTR_RATIO

def demeaned_remove_zeros(x: pd.Series) -> pd.Series:
    x[x == 0] = np.nan
    return x - x.mean()
