def cross_sectional_mean_reversion(
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
    relative_return = outperformance.diff()
    outperformance_over_horizon = relative_return.rolling(horizon).mean()

    forecast = -outperformance_over_horizon.ewm(span=ewma_span).mean()

    return forecast
