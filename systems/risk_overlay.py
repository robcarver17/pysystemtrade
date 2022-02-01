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
