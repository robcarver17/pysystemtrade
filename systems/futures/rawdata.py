import numpy as np

from systems.rawdata import RawData
from syscore.objects import update_recalc
from syscore.dateutils import expiry_diff
from syscore.pdutils import uniquets
from systems.system_cache import input, diagnostic, output


class FuturesRawData(RawData):
    """
    A SubSystem that does futures specific raw data calculations

    Name: rawdata
    """

    def __init__(self):
        """
        Create a futures raw data subsystem

        >>> FuturesRawData()
        SystemStage 'rawdata' futures Try objectname.methods()
        """
        super(FuturesRawData, self).__init__()

        setattr(self, "description", "futures")

    @input
    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        KEY INPUT


        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.get_instrument_raw_carry_data("EDOLLAR").tail(2)
                               PRICE  CARRY CARRY_CONTRACT PRICE_CONTRACT
        2015-12-11 17:08:14  97.9675    NaN         201812         201903
        2015-12-11 19:33:39  97.9875    NaN         201812         201903
        """

        instrcarrydata = self.parent.data.get_instrument_raw_carry_data(
            instrument_code)
        return instrcarrydata

    @diagnostic()
    def raw_futures_roll(self, instrument_code):
        """
        Returns the raw difference between price and carry

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.raw_futures_roll("EDOLLAR").ffill().tail(2)
        2015-12-11 17:08:14   -0.07
        2015-12-11 19:33:39   -0.07
        dtype: float64
        """

        carrydata = self.get_instrument_raw_carry_data(instrument_code)
        raw_roll = carrydata.PRICE - carrydata.CARRY

        raw_roll[raw_roll == 0] = np.nan

        raw_roll = uniquets(raw_roll)

        return raw_roll

    @diagnostic()
    def roll_differentials(self, instrument_code):
        """
        Work out the annualisation factor

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.roll_differentials("EDOLLAR").ffill().tail(2)
        2015-12-11 17:08:14   -0.246407
        2015-12-11 19:33:39   -0.246407
        dtype: float64
        """
        carrydata = self.get_instrument_raw_carry_data(instrument_code)
        roll_diff = carrydata.apply(expiry_diff, 1)

        roll_diff = uniquets(roll_diff)

        return roll_diff

    @diagnostic()
    def annualised_roll(self, instrument_code):
        """
        Work out annualised futures roll

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.annualised_roll("EDOLLAR").ffill().tail(2)
        2015-12-11 17:08:14    0.284083
        2015-12-11 19:33:39    0.284083
        dtype: float64
        >>> system.rawdata.annualised_roll("US10").ffill().tail(2)
        2015-12-11 16:06:35    2.320441
        2015-12-11 17:24:06    2.320441
        dtype: float64

        """

        rolldiffs = self.roll_differentials(instrument_code)
        rawrollvalues = self.raw_futures_roll(instrument_code)

        annroll = rawrollvalues / rolldiffs

        return annroll

    @output()
    def daily_annualised_roll(self, instrument_code):
        """
        Resample annualised roll to daily frequency

        We don't resample earlier, or we'll get bad data

        :param instrument_code: instrument to get data for
        :type instrument_code: str

        :returns: Tx4 pd.DataFrame

        KEY OUTPUT

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>> system.rawdata.daily_annualised_roll("EDOLLAR").ffill().tail(2)
        2015-12-10    0.284083
        2015-12-11    0.284083
        Freq: B, dtype: float64
        """

        annroll = self.annualised_roll(instrument_code)
        annroll = annroll.resample("1B").mean()
        return annroll

    @output()
    def daily_denominator_price(self, instrument_code):
        """
        Gets daily prices for use with % volatility
        This won't always be the same as the normal 'price'

        :param instrument_code: Instrument to get prices for
        :type trading_rules: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.tests.testfuturesrawdata import get_test_object_futures
        >>> from systems.basesystem import System
        >>> (data, config)=get_test_object_futures()
        >>> system=System([FuturesRawData()], data)
        >>>
        >>> system.rawdata.daily_denominator_price("EDOLLAR").ffill().tail(2)
        2015-12-10    97.8800
        2015-12-11    97.9875
        Freq: B, Name: PRICE, dtype: float64
        """
        prices = self.get_instrument_raw_carry_data(instrument_code).PRICE
        daily_prices = prices.resample("1B").last()
        return daily_prices


if __name__ == '__main__':
    import doctest
    doctest.testmod()
