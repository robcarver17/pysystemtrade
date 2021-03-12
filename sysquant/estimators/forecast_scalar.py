from copy import copy
import pandas as pd
import numpy as np

from syscore.genutils import str2Bool


def forecast_scalar(
        cs_forecasts: pd.DataFrame,
        target_abs_forecast: float = 10.0,
        window: int=250000, ## JUST A VERY LARGE NUMBER TO USE ALL DATA
        min_periods=500, # MINIMUM PERIODS BEFORE WE ESTIMATE A SCALAR,
        backfill=True ## BACKFILL OUR FIRST ESTIMATE, SLIGHTLY CHEATING, BUT...
    ) -> pd.Series:
    """
    Work out the scaling factor for xcross such that T*x has an abs value of 10 (or whatever the average absolute forecast is)

    :param cs_forecasts: forecasts, cross sectionally
    :type cs_forecasts: pd.DataFrame TxN

    :param span:
    :type span: int

    :param min_periods:


    :returns: pd.DataFrame
    """
    backfill = str2Bool(backfill)  # in yaml will come in as text

    # Remove zeros/nans
    copy_cs_forecasts = copy(cs_forecasts)
    copy_cs_forecasts[copy_cs_forecasts == 0.0] = np.nan

    # Take CS average first
    # we do this before we get the final TS average otherwise get jumps in
    # scalar when new markets introduced
    if copy_cs_forecasts.shape[1] == 1:
        x = copy_cs_forecasts.abs().iloc[:, 0]
    else:
        x = copy_cs_forecasts.ffill().abs().median(axis=1)

    # now the TS
    avg_abs_value = x.rolling(window=window, min_periods=min_periods).mean()
    scaling_factor = target_abs_forecast / avg_abs_value

    if backfill:
        scaling_factor = scaling_factor.fillna(method="bfill")

    return scaling_factor