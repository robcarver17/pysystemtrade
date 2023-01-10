import pandas as pd


def get_risk_multiplier(
    risk_overlay_config: dict,
    normal_risk: pd.Series,
    shocked_vol_risk: pd.Series,
    sum_abs_risk: pd.Series,
    leverage: pd.Series,
    percentage_vol_target: float,
):
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
    risk_limit_for_normal_risk = (
        risk_overlay_config["max_risk_fraction_normal_risk"]
        * percentage_vol_target
        / 100.0
    )
    risk_multiplier_for_normal_risk = multiplier_given_series_and_limit(
        risk_measure=normal_risk, risk_limit=risk_limit_for_normal_risk
    )

    risk_limit_for_shocked_risk = (
        risk_overlay_config["max_risk_fraction_stdev_risk"]
        * percentage_vol_target
        / 100.0
    )
    risk_multiplier_for_shocked_stdev = multiplier_given_series_and_limit(
        risk_measure=shocked_vol_risk, risk_limit=risk_limit_for_shocked_risk
    )

    risk_limit_for_sum_abs_risk = (
        risk_overlay_config["max_risk_limit_sum_abs_risk"]
        * percentage_vol_target
        / 100.0
    )
    risk_multiplier_for_sum_abs_risk = multiplier_given_series_and_limit(
        risk_measure=sum_abs_risk, risk_limit=risk_limit_for_sum_abs_risk
    )

    risk_limit_for_leverage = risk_overlay_config["max_risk_leverage"]
    risk_multiplier_for_leverage = multiplier_given_series_and_limit(
        risk_measure=leverage, risk_limit=risk_limit_for_leverage
    )

    all_mult = pd.concat(
        [
            risk_multiplier_for_shocked_stdev,
            risk_multiplier_for_normal_risk,
            risk_multiplier_for_sum_abs_risk,
            risk_multiplier_for_leverage,
        ],
        axis=1,
    )
    all_mult.columns = ["jump vol", "normal", "shock correlation", "leverage"]
    joint_mult = all_mult.min(axis=1)

    return joint_mult


def multiplier_given_series_and_limit(
    risk_measure: pd.Series, risk_limit: float
) -> pd.Series:

    limit_as_series = pd.Series(
        [risk_limit] * len(risk_measure.index), risk_measure.index
    )
    joined_up = pd.concat([limit_as_series, risk_measure], axis=1)
    max_value = joined_up.max(axis=1)
    max_value_as_ratio_to_limit = risk_limit / max_value

    return max_value_as_ratio_to_limit
