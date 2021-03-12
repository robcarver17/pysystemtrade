import pandas as pd
import numpy as np
from systems.portfolio import Portfolios
from systems.system_cache import input, dont_cache, diagnostic, output
from syscore.objects import arg_not_supplied
from syscore.genutils import progressBar
from syscore.optimisation_utils import sigma_from_corr_and_std
from syscore.correlations import boring_corr_matrix, CorrelationList


class portfoliosRiskOverlay(Portfolios):
    """
    Adding risk overlay to portfolios
    """

    @output()
    def get_notional_position(self, instrument_code):
        """
        Override of original method to include risk overlay scaling

        :param instrument_code:
        :return: Tx1 pd.DataFrame
        """

        original_notional_position = self.get_notional_position_before_overlay(
            instrument_code
        )
        risk_multiplier = self.get_risk_multiplier()

        new_notional_position = original_notional_position * risk_multiplier

        return new_notional_position

    @diagnostic()
    def get_notional_position_before_overlay(self, instrument_code):
        """
        Gets the position, accounts for instrument weights and diversification multiplier

        This is the original function that doesn't know about risk overlays

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        """

        self.log.msg(
            "Calculating notional position for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        idm = self.get_instrument_diversification_multiplier()
        instr_weights = self.get_instrument_weights()
        subsys_position = self.get_subsystem_position(instrument_code)

        inst_weight_this_code = instr_weights[instrument_code]

        inst_weight_this_code = inst_weight_this_code.reindex(
            subsys_position.index
        ).ffill()
        idm = idm.reindex(subsys_position.index).ffill()

        notional_position = subsys_position * inst_weight_this_code * idm

        return notional_position

    """
    Rest of the function is calculating the risk overlay
    """

    @diagnostic()
    def get_risk_multiplier(self):
        """
        The risk overlay calculates a risk position multiplier, which is between 0 and 1.
          When this multiplier is one we make no changes to the positions calculated by our system.
          If it was 0.5, then we'd reduce our positions by half. And so on.

        So the overlay acts across the entire portfolio, reducing risk proportionally on all positions at the same time.

        The risk overlay has three components, designed to deal with the following issues:

        - Expected risk that is too high
        - Weird correlation shocks combined with extreme positions
        - Jumpy volatility (non stationary and non Gaussian vol)

        Each component calculates it's own risk multipler, and then we take the lowest (most conservative) value.

        :return:Tx1 pd.DataFrame
        """
        risk_multiplier = self.get_normal_risk_multiplier()
        risk_multiplier_for_correlation = self.get_correlation_risk_multiplier()
        risk_multiplier_for_stdev = self.get_stdev_risk_multiplier()

        all_mult = pd.concat(
            [
                risk_multiplier_for_stdev,
                risk_multiplier,
                risk_multiplier_for_correlation,
            ],
            axis=1,
        )
        joint_mult = all_mult.min(axis=1)

        return joint_mult

    @input
    def get_vol_target_as_number(self):
        return self.parent.config.percentage_vol_target / 100.0

    @input
    def get_risk_overlay_config_dict(self):
        return self.parent.config.risk_overlay

    @diagnostic()
    def get_normal_risk_multiplier(self):
        """
        Risk multiplier assuming estimates are valid

        :return: Tx1 pd.DataFrame
        """

        target_risk = self.get_vol_target_as_number()
        max_risk_allowed = self.get_risk_overlay_config_dict()[
            "max_risk_fraction_normal_risk"
        ]
        estimated_risk = self.get_estimated_portfolio_risk(
            shock_correlations_and_abs_weights=False, shock_vols=False
        )
        risk_scalar = get_risk_scalar(
            estimated_risk,
            target_risk=target_risk,
            max_risk_allowed=max_risk_allowed)

        return risk_scalar

    def get_correlation_risk_multiplier(self):
        """
        Risk multiplier assuming all correlations go to worse possible values

        :return:  Tx1 pd.DataFrame
        """
        target_risk = self.get_vol_target_as_number()
        max_risk_allowed = self.get_risk_overlay_config_dict()[
            "max_risk_fraction_correlation_risk"
        ]
        estimated_risk = self.get_estimated_portfolio_risk(
            shock_correlations_and_abs_weights=True, shock_vols=False
        )
        risk_scalar = get_risk_scalar(
            estimated_risk,
            target_risk=target_risk,
            max_risk_allowed=max_risk_allowed)

        return risk_scalar

    def get_stdev_risk_multiplier(self):
        """
        Risk multiplier assuming standard deviations go to 99% percentile point

        :return:  Tx1 pd.DataFrame
        """

        target_risk = self.get_vol_target_as_number()
        max_risk_allowed = self.get_risk_overlay_config_dict()[
            "max_risk_fraction_stdev_risk"
        ]
        estimated_risk = self.get_estimated_portfolio_risk(
            shock_correlations_and_abs_weights=False, shock_vols=True
        )
        risk_scalar = get_risk_scalar(
            estimated_risk,
            target_risk=target_risk,
            max_risk_allowed=max_risk_allowed)

        return risk_scalar

    def get_estimated_portfolio_risk(
        self, shock_correlations_and_abs_weights=False, shock_vols=False
    ):
        """

        :param shock_correlations_and_abs_weights: if True, set all correlations to 1 and use abs weights
        :param shock_vols: Use 99% percentile volatilities
        :return: Tx1 pd.DataFrame
        """

        positions_as_proportion_of_capital = (
            self.get_positions_as_proportion_of_capital()
        )
        if shock_correlations_and_abs_weights:
            positions_as_proportion_of_capital = (
                positions_as_proportion_of_capital.abs()
            )

        covariance_estimates = self.get_covariance_estimates(
            shock_correlations_and_abs_weights=shock_correlations_and_abs_weights,
            shock_vols=shock_vols,
        )

        expected_risk = calc_expected_risk_over_time(
            covariance_estimates, positions_as_proportion_of_capital
        )

        return expected_risk

    @input
    def get_inputs_for_position_calcs(self):
        """

        :return: tuple of data
        """
        system = self.parent
        returns = self.get_instrument_returns()  # used only for alignment
        positions = get_from_system_and_align(
            system,
            "portfolio",
            "get_notional_position_before_overlay",
            ts_index=returns.index,
        )
        block_sizes = get_from_system_and_align(
            system,
            "data",
            "get_value_of_block_price_move",
            ts_index=positions.index)
        fx_rates = get_from_system_and_align(
            system,
            "data",
            "get_fx_for_instrument",
            ts_index=positions.index,
            more_args=[system.config.base_currency],
        )
        prices = get_from_system_and_align(
            system,
            "rawdata",
            "daily_denominator_price",
            ts_index=positions.index)

        return positions, block_sizes, fx_rates, prices

    @diagnostic()
    def get_positions_as_proportion_of_capital(self):
        """
        Return positions as % of capital

        :return: TxN pd.DataFrame
        """
        positions, block_sizes, fx_rates, prices = self.get_inputs_for_position_calcs()

        capital = self.parent.config.notional_trading_capital

        value_of_each_contract = prices * block_sizes * fx_rates
        value_of_positions = value_of_each_contract * positions
        value_of_positions_proportion_capital = value_of_positions / capital

        return value_of_positions_proportion_capital

    @diagnostic()
    def get_covariance_estimates(
        self, shock_correlations_and_abs_weights=False, shock_vols=False
    ):

        instrument_returns = self.get_instrument_returns()
        if shock_correlations_and_abs_weights:
            rolling_correlations = get_shocked_correlations(instrument_returns)
        else:
            rolling_correlations = get_rolling_correlations(instrument_returns)

        daily_rolling_std = self._get_rolling_daily_stdev()
        if shock_vols:
            rolling_stdev = get_shocked_vols(daily_rolling_std)
        else:
            rolling_stdev = get_rolling_stdev(daily_rolling_std)

        covariance_estimates = combine_list_of_correlations_and_stdev(
            rolling_correlations, rolling_stdev
        )

        return covariance_estimates

    @diagnostic()
    def _get_rolling_daily_stdev(self, span=30):
        instrument_returns = self.get_instrument_returns()
        daily_rolling_std = instrument_returns.ewm(span=span).std()
        return daily_rolling_std

    @input
    def get_instrument_returns(self):
        """
        Get instrument returns as %

        :return: TxN pd.DataFrame
        """
        system = self.parent
        instrument_returns = get_from_system_and_align(
            system, "rawdata", "get_daily_percentage_returns"
        )

        return instrument_returns


def get_shocked_vols(daily_rolling_std):
    # shock them
    rolling_std = apply_vol_shock(daily_rolling_std)
    # resample to monthly
    rolling_std = rolling_std.resample("1M").last()

    return rolling_std


def get_rolling_stdev(daily_rolling_std, span=30):

    # all data is monthly for efficiency
    rolling_std = daily_rolling_std.resample("1M").last()

    return rolling_std


def get_shocked_correlations(instrument_returns):
    # shocked correlations are all 1
    shocked_matrix = get_shocked_corr_matrix(instrument_returns.columns)
    monthly_ts = list(instrument_returns.resample("1M").last().index)
    corr_list = [shocked_matrix] * len(monthly_ts)

    rolling_corr = CorrelationList(
        corr_list, instrument_returns.columns, monthly_ts)
    return rolling_corr


def get_rolling_correlations(instrument_returns, span=26):
    monthly_ts = list(instrument_returns.resample("1M").last().index)[1:]
    weekly_instrument_returns = instrument_returns.resample("7D").sum()
    corr_list = []
    for monthly_timestamp in monthly_ts:
        period_returns = weekly_instrument_returns[:monthly_timestamp]
        corr_matrix = period_returns.tail(span).corr().values
        corr_list.append(corr_matrix)

    rolling_corr = CorrelationList(
        corr_list, instrument_returns.columns, monthly_ts)

    return rolling_corr


def get_method_pd_series_for_instrument(
    method, instrument_code, ts_index=arg_not_supplied, more_args=[]
):
    """
    Get data from some method, making it into a time series if required

    :param method: some functional method
    :param instrument: str
    :param ts_index: pd index, optional. Required if forcing to time series
    :param more_args: optional args apart from instrument_code to pass to method
    :return: Tx1 pd index
    """
    data = method(instrument_code, *more_args)
    data_index = getattr(data, "index", None)
    if data_index is None:
        # convert
        if ts_index is arg_not_supplied:
            raise Exception(
                "Method %s(%s) returns a scalar, need to pass an index"
                % (str(method), instrument_code)
            )
        data = pd.Series([data] * len(ts_index), index=ts_index)

    return data


def get_from_system_and_align(
    system, stage_name, method_name, ts_index=arg_not_supplied, more_args=[]
):
    """
    Return a stage method across instruments, aligned to a particular index

    :param system: system object
    :param stage_name: str
    :param method_name: str
    :param ts_index: pd index or arg_not_passed if not aligning
    :return: TxN pd.DataFrame, aligned to instrument list and index
    """
    list_of_instruments = system.get_instrument_list()
    stage = getattr(system, stage_name)
    method = getattr(stage, method_name)
    method_data = [
        get_method_pd_series_for_instrument(
            method, instrument_code, ts_index=ts_index, more_args=more_args
        )
        for instrument_code in list_of_instruments
    ]

    method_data = pd.concat(method_data, axis=1)
    method_data.columns = list_of_instruments

    if ts_index is not arg_not_supplied:
        method_data = method_data.ffill().reindex(ts_index)

    return method_data


def get_risk_scalar(estimated_risk, target_risk=0.25, max_risk_allowed=2.0):
    """
    Return a risk scalar when the estimated measure of risk relative to target_risk is above max_risk_allowed

    Risk scalars are between 0 and 1

    :param estimated_risk: Tx1 pd.DataFrame
    :param max_risk_allowed: scalar
    :return: Tx1 pd.DataFrame
    """

    risk_vs_average = estimated_risk.ffill() / target_risk
    risk_multiplier = max_risk_allowed / risk_vs_average
    risk_multiplier[risk_multiplier > 1.0] = 1.0

    return risk_multiplier


def combine_list_of_correlations_and_stdev(
        rolling_correlations, rolling_stdev):
    corr_index_dates = rolling_correlations.fit_dates
    std_index_dates = list(rolling_stdev.index)
    sigma_list = []
    for corr_index, index_date in enumerate(corr_index_dates):
        std_dev = rolling_stdev.loc[index_date].values
        std_dev[np.isnan(std_dev)] = 0.0
        cmatrix = rolling_correlations.corr_list[corr_index]
        cmatrix = pd.DataFrame(cmatrix)
        cmatrix[cmatrix.isna()] = 1.0
        cmatrix = np.array(cmatrix)
        sigma = sigma_from_corr_and_std(std_dev, cmatrix)

        sigma_list.append(sigma)

    covariance_estimates = CorrelationList(
        sigma_list, rolling_stdev.columns, corr_index_dates
    )

    return covariance_estimates


def apply_vol_shock(
        rolling_stdev_estimates,
        vol_lookback_days=2500,
        min_periods=10,
        quantile=0.99):
    shocked_vol = (
        rolling_stdev_estimates.ffill()
        .rolling(vol_lookback_days, min_periods=min_periods)
        .quantile(quantile)
    )
    # If no shocked vol use existing

    return shocked_vol


def calc_expected_risk_over_time(
    covariance_estimates, positions_as_proportion_of_capital
):
    positions_index = positions_as_proportion_of_capital.index
    positions_as_proportion_of_capital[positions_as_proportion_of_capital.isna(
    )] = 0.0
    progress = progressBar(len(positions_index))

    mapping_info = get_daily_to_monthly_mapping(
        covariance_estimates, positions_as_proportion_of_capital
    )

    risk = [
        calc_risk_for_date(
            covariance_estimates,
            index_date,
            mapping_info,
            positions_as_proportion_of_capital,
            progress,
        )
        for index_date in positions_index
    ]

    progress.finished()

    variance_series = pd.Series(risk, index=positions_index)
    stdev_series = variance_series ** 0.5
    annualised_stdev_series = stdev_series * 16.0

    return annualised_stdev_series


def calc_risk_for_date(
    covariance_estimates,
    index_date,
    mapping_info,
    positions_as_proportion_capital,
    progress,
):
    weights = positions_as_proportion_capital.loc[index_date].values
    sigma = get_covariance_matrix_for_date(
        covariance_estimates, index_date, mapping_info
    )

    portfolio_variance = weights.dot(sigma).dot(weights.transpose())
    progress.iterate()

    return portfolio_variance


def get_covariance_matrix_for_date(
        covariance_estimates,
        index_date,
        mapping_info):
    map_monthly, daily_index = mapping_info
    daily_location = list(daily_index).index(index_date)
    monthly_location = map_monthly[daily_location]
    cmatrix = covariance_estimates.corr_list[monthly_location]

    return cmatrix


def get_shocked_corr_matrix(list_of_instruments):
    return boring_corr_matrix(len(list_of_instruments), offdiag=1.0)


def get_daily_to_monthly_mapping(rolling_correlation, positions):

    monthly_index = rolling_correlation.fit_dates
    daily_index = positions.index

    map_monthly = []
    place_in_monthly = 0
    length_of_monthly = len(monthly_index)
    for daily_index_value in daily_index:
        if place_in_monthly == length_of_monthly - 1:
            # can't go any further, keep using this value
            pass
        else:
            next_monthly_index_value = monthly_index[place_in_monthly + 1]
            if next_monthly_index_value <= daily_index_value:
                # need the next monthly index
                place_in_monthly = place_in_monthly + 1

        map_monthly.append(place_in_monthly)

    return map_monthly, daily_index
