from sysdata.data import Data
from random import gauss
import numpy as np
from syscore.pdutils import create_arbitrary_pdseries
import pandas as pd


class RandomData(Data):
    """
    Generates random data for testing with a saw tooth pattern

    Unlike a normal data object this doesn't have any data when first created

    You need to run generate_random_data which will generate, and then cache, the data
    """

    def __init__(self):
        super().__init__()
        setattr(self, "_price_cache_random_data", dict())

    def __repr__(self):
        return "RandomData object with %d instruments" % len(
            self.get_instrument_list())

    def get_instrument_list(self):

        return list(self._price_cache_random_data.keys())

    def get_raw_price(self, instrument_code):
        """
        Returns a pd.series of prices

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataSeries

        >>> ans=RandomData()
        >>> ans.generate_random_data("wibble", 10, 5, 5, 0.0)

        >>> ans.get_raw_price("wibble")
        1980-01-01    0.0
        1980-01-02    1.0
        1980-01-03    2.0
        1980-01-04    3.0
        1980-01-07    4.0
        1980-01-08    5.0
        1980-01-09    4.0
        1980-01-10    3.0
        1980-01-11    2.0
        1980-01-14    1.0
        Freq: B, dtype: float64

        """

        if instrument_code in self.get_instrument_list():
            ## must have been cached
            return self._price_cache_random_data[instrument_code]

        error_msg = "No price found for %s you need to run .generate_random_data(instrument_code=%s....)" % (
            instrument_code, instrument_code)
        self.log.critical(error_msg)

    def generate_random_data(self,
                             instrument_code,
                             Nlength,
                             Tlength,
                             Xamplitude,
                             Volscale,
                             sines=False,
                             date_start=pd.datetime(1980, 1, 1)):
        """
        Generates a trend of length N amplitude X, plus gaussian noise mean zero std. dev (vol scale * amplitude)
        With an arbitrary datetime index

        If sines=True then generates as a sine wave, otherwise straight line

        :param Nlength: total number of returns to generate
        :type Nlength: int

        :param Tlength: Length of each trend
        :type Tlength: int

        :param Xamplitude: Amplitude of each trend
        :type Xamplitude: float

        :param Volscale: Ratio of volatility to amplitude
        :type Volscale: float

        :param sines: Generate a sine wave (if True), or a saw tooth (False). Default False.
        :type sines: bool

        :param date_start: Start date for arbitrary series
        :type date_start: datetime

        :param instrument_code: made up instrument to create data for
        :type instrument_code: str

        :returns: None

        Also puts results into cache

        """

        random_data = generate_trendy_pdseries(
            Nlength,
            Tlength,
            Xamplitude,
            Volscale,
            sines=sines,
            date_start=date_start)

        self._price_cache_random_data[instrument_code] = random_data

        return None


def generate_siney_trends(Nlength, Tlength, Xamplitude):
    """
    Generates a price process, Nlength returns, underlying trend with length T and amplitude X
    as a sine wave

    :param Nlength: total number of returns to generate
    :type Nlength: int

    :param Tlength: Length of each trend
    :type Tlength: int

    :param Xamplitude: Amplitude of each trend
    :type Xamplitude: float


    :returns: returns a vector of numbers as a list, length Nlength


    """

    halfAmplitude = Xamplitude / 2.0

    cycles = Nlength / Tlength
    cycles_as_pi = cycles * np.pi
    increment = cycles_as_pi / Nlength

    alltrends = [
        np.sin(x) * halfAmplitude
        for x in np.arange(0.0, cycles_as_pi, increment)
    ]
    alltrends = alltrends[:Nlength]

    return alltrends


def generate_trends(Nlength, Tlength, Xamplitude):
    """
    Generates a price process, Nlength returns, underlying trend with length T and amplitude X

    :param Nlength: total number of returns to generate
    :type Nlength: int

    :param Tlength: Length of each trend
    :type Tlength: int

    :param Xamplitude: Amplitude of each trend
    :type Xamplitude: float

    :returns: returns a vector of numbers as a list, length Nlength

    """

    halfAmplitude = Xamplitude / 2.0
    trend_step = Xamplitude / Tlength

    cycles = int(np.ceil(Nlength / Tlength))

    trendup = list(
        np.arange(start=-halfAmplitude, stop=halfAmplitude, step=trend_step))
    trenddown = list(
        np.arange(start=halfAmplitude, stop=-halfAmplitude, step=-trend_step))
    alltrends = [trendup + trenddown] * int(np.ceil(cycles))
    alltrends = sum(alltrends, [])
    alltrends = alltrends[:Nlength]

    return alltrends


def generate_noise(Nlength, stdev):
    """
    Generates a series of gaussian noise as a list Nlength

    :param Nlength: total number of returns to generate
    :type Nlength: int

    :param stdev: Standard deviation of noise
    :type stdev: float

    :returns: returns a vector of numbers as a list, length Nlength

    """

    return [gauss(0.0, stdev) for Unused in range(Nlength)]


def generate_trendy_pdseries(Nlength,
                             Tlength,
                             Xamplitude,
                             Volscale,
                             sines=False,
                             date_start=pd.datetime(1980, 1, 1)):
    """
    Generates a trend of length N amplitude X, plus gaussian noise mean zero std. dev (vol scale * amplitude)
    With an arbitrary datetime index

    If sines=True then generates as a sine wave, otherwise straight line

    :param Nlength: total number of returns to generate
    :type Nlength: int

    :param Tlength: Length of each trend
    :type Tlength: int

    :param Xamplitude: Amplitude of each trend
    :type Xamplitude: float

    :param Volscale: Ratio of volatility to amplitude
    :type Volscale: float

    :param sines: Generate a sine wave (if True), or a saw tooth (False). Default False.
    :type sines: bool

    :param date_start: Start date for arbitrary series
    :type date_start: datetime

    :returns: a pd.Series, length Nlength

    >>> generate_trendy_pdseries(10, 5, 5, 0.0)
    1980-01-01    0.0
    1980-01-02    1.0
    1980-01-03    2.0
    1980-01-04    3.0
    1980-01-07    4.0
    1980-01-08    5.0
    1980-01-09    4.0
    1980-01-10    3.0
    1980-01-11    2.0
    1980-01-14    1.0
    Freq: B, dtype: float64

    >>> generate_trendy_pdseries(10, 5, 5, 0.0, True)
    1980-01-01    0.000000e+00
    1980-01-02    1.469463e+00
    1980-01-03    2.377641e+00
    1980-01-04    2.377641e+00
    1980-01-07    1.469463e+00
    1980-01-08    2.220446e-16
    1980-01-09   -1.469463e+00
    1980-01-10   -2.377641e+00
    1980-01-11   -2.377641e+00
    1980-01-14   -1.469463e+00
    Freq: B, dtype: float64
    """

    stdev = Volscale * Xamplitude
    noise_returns_as_list = generate_noise(Nlength, stdev)

    ## Can use a different process here if desired
    if sines:
        process_as_list = generate_siney_trends(Nlength, Tlength, Xamplitude)
    else:
        process_as_list = generate_trends(Nlength, Tlength, Xamplitude)

    pd_process = create_arbitrary_pdseries(
        process_as_list, date_start=date_start)
    noise_returns = create_arbitrary_pdseries(
        noise_returns_as_list, date_start=date_start)

    process_returns = pd_process.diff()
    combined_returns = noise_returns + process_returns

    combined_returns[0] = 0
    combined_price = combined_returns.cumsum()

    return combined_price

    return pdseries


if __name__ == '__main__':
    import doctest
    doctest.testmod()
