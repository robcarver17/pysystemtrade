import numpy as np


def relative_momentum(
    normalised_price_this_instrument,
    normalised_price_for_asset_class,
    horizon=250,
    ewma_span=None,
):
    """
    Cross sectional mean reversion within asset class

    :param normalised_price_this_instrument: pd.Series
    :param normalised_price_for_asset_class: pd.Series
    :return: pd.Series
    """

    if ewma_span is None:
        ewma_span = int(horizon / 4.0)

    ewma_span = max(ewma_span, 2)

    outperformance = (
        normalised_price_this_instrument.ffill()
        - normalised_price_for_asset_class.ffill()
    )
    outperformance[outperformance == 0] = np.nan
    average_outperformance_over_horizon = (
        outperformance - outperformance.shift(horizon)
    ) / horizon

    forecast = average_outperformance_over_horizon.ewm(span=ewma_span).mean()

    return forecast
