"""
Get legacy data from .csv files

Used for quick examples / 'scaffolding'
"""

import os

import pandas as pd

from syscore.fileutils import get_pathname_for_package
from syscore.pdutils import pd_readcsv
from syscore.genutils import str_of_int

from sysdata.futuresdata import FuturesData
"""
Static variables to store location of data
"""
LEGACY_DATA_PATH = "sysdata.legacycsv"


class csvFuturesData(FuturesData):
    """
        Get futures specific data from legacy csv files

        Extends the FuturesData class for a specific data source

    """

    def __init__(self, datapath=None, absolute_datapath=None):
        """
        Create a FuturesData object for reading .csv files from datapath
        inherits from FuturesData

        We look for data in .csv files


        :param datapath: relative path to find .csv files (defaults to LEGACY_DATA_MODULE/LEGACY_DATA_DIR
        :type datapath: None or str

        :param absolute_datapath: absolute path to find .csv files (not used if datapath specified)
        :type datapath: None or str


        :returns: new csvFuturesData object

        >>> data=csvFuturesData("sysdata.tests")
        >>> data
        FuturesData object with 3 instruments


        """

        super().__init__()

        ## Use (1) provided relative datapath, (2) absolute_datapath, (3) default relative datapath

        if datapath is not None:
            resolved_datapath = get_pathname_for_package(datapath)
        else:
            if absolute_datapath is not None:
                resolved_datapath = absolute_datapath
            else:
                resolved_datapath = get_pathname_for_package(LEGACY_DATA_PATH)
        """
        Most Data objects that read data from a specific place have a 'source' of some kind
        Here it's a directory
        """
        setattr(self, "_datapath", resolved_datapath)

    def _get_all_cost_data(self):
        """
        Get a data frame of cost data

        :returns: pd.DataFrame

        >>> data=csvFuturesData("sysdata.tests")
        >>> data._get_all_cost_data()
                   Instrument  Slippage  PerBlock  Percentage  PerTrade
        Instrument
        BUND             BUND    0.0050      2.00           0         0
        US10             US10    0.0080      1.51           0         0
        EDOLLAR       EDOLLAR    0.0025      2.11           0         0
        """

        self.log.msg("Loading csv cost file")

        filename = os.path.join(self._datapath, "costs_analysis.csv")
        try:
            instr_data = pd.read_csv(filename)
            instr_data.index = instr_data.Instrument

            return instr_data
        except OSError:
            self.log.warn("Cost file not found %s" % filename)
            return None

    def get_raw_cost_data(self, instrument_code):
        """
        Get's cost data for an instrument

        Get cost data

        Execution slippage [half spread] price units
        Commission (local currency) per block
        Commission - percentage of value (0.01 is 1%)
        Commission (local currency) per block

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: dict of floats

        >>> data=csvFuturesData("sysdata.tests")
        >>> data.get_raw_cost_data("EDOLLAR")['price_slippage']
        0.0025000000000000001
        """

        default_costs = dict(
            price_slippage=0.0,
            value_of_block_commission=0.0,
            percentage_cost=0.0,
            value_of_pertrade_commission=0.0)

        cost_data = self._get_all_cost_data()

        if cost_data is None:
            ##
            return default_costs

        try:
            block_move_value = cost_data.loc[instrument_code, [
                'Slippage', 'PerBlock', 'Percentage', 'PerTrade'
            ]]
        except KeyError:
            self.log.warn(
                "Cost data not found for %s, using zero" % instrument_code)
            return default_costs

        return dict(
            price_slippage=block_move_value[0],
            value_of_block_commission=block_move_value[1],
            percentage_cost=block_move_value[2],
            value_of_pertrade_commission=block_move_value[3])

    def get_raw_price(self, instrument_code):
        """
        Get instrument price

        :param instrument_code: instrument to get prices for
        :type instrument_code: str

        :returns: pd.DataFrame

        >>> data=csvFuturesData("sysdata.tests")
        >>> data.get_raw_price("EDOLLAR").tail(2)
        2015-12-11 17:08:14    97.9675
        2015-12-11 19:33:39    97.9875
        Name: price, dtype: float64
        >>> data["US10"].tail(2)
        2015-12-11 16:06:35    126.914062
        2015-12-11 17:24:06    126.945312
        Name: price, dtype: float64
        """

        # Read from .csv
        self.log.msg(
            "Loading csv data for %s" % instrument_code,
            instrument_code=instrument_code)
        filename = os.path.join(self._datapath, instrument_code + "_price.csv")
        instrpricedata = pd_readcsv(filename)
        instrpricedata.columns = ["price"]
        instrpricedata = instrpricedata.groupby(level=0).last()
        instrpricedata = pd.Series(instrpricedata.iloc[:, 0])
        return instrpricedata

    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

        These are specifically needed for futures trading

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        >>> data=csvFuturesData("sysdata.tests")
        >>> data.get_instrument_raw_carry_data("US10").tail(4)
                                  PRICE  CARRY CARRY_CONTRACT PRICE_CONTRACT
        2015-12-10 23:00:00  126.328125    NaN         201606         201603
        2015-12-11 14:35:15  126.835938    NaN         201606         201603
        2015-12-11 16:06:35  126.914062    NaN         201606         201603
        2015-12-11 17:24:06  126.945312    NaN         201606         201603
        """

        self.log.msg(
            "Loading csv carry data for %s" % instrument_code,
            instrument_code=instrument_code)

        filename = os.path.join(self._datapath,
                                instrument_code + "_carrydata.csv")
        instrcarrydata = pd_readcsv(filename)

        instrcarrydata.CARRY_CONTRACT = instrcarrydata.CARRY_CONTRACT.apply(
            str_of_int)
        instrcarrydata.PRICE_CONTRACT = instrcarrydata.PRICE_CONTRACT.apply(
            str_of_int)

        return instrcarrydata

    def _get_instrument_data(self):
        """
        Get a data frame of interesting information about instruments, either
        from a file or cached

        :returns: pd.DataFrame

        >>> data=csvFuturesData("sysdata.tests")
        >>> data._get_instrument_data()
                   Instrument  Pointsize AssetClass Currency
        Instrument
        EDOLLAR       EDOLLAR       2500       STIR      USD
        US10             US10       1000       Bond      USD
        BUND             BUND       1000       Bond      EUR
        """

        self.log.msg("Loading csv instrument config")

        filename = os.path.join(self._datapath, "instrumentconfig.csv")
        instr_data = pd.read_csv(filename)
        instr_data.index = instr_data.Instrument

        return instr_data

    def get_instrument_list(self):
        """
        list of instruments in this data set

        :returns: list of str

        >>> data=csvFuturesData("sysdata.tests")
        >>> data.get_instrument_list()
        ['EDOLLAR', 'US10', 'BUND']
        >>> data.keys()
        ['EDOLLAR', 'US10', 'BUND']
        """

        instr_data = self._get_instrument_data()

        return list(instr_data.Instrument)

    def get_instrument_asset_classes(self):
        """
        Returns dataframe with index of instruments, column AssetClass

        >>> data=csvFuturesData("sysdata.tests")
        >>> data.get_instrument_asset_classes()
        Instrument
        EDOLLAR    STIR
        US10       Bond
        BUND       Bond
        Name: AssetClass, dtype: object
        """
        instr_data = self._get_instrument_data()
        instr_assets = instr_data.AssetClass

        return instr_assets

    def get_value_of_block_price_move(self, instrument_code):
        """
        How much is a $1 move worth in value terms?

        :param instrument_code: instrument to get value for
        :type instrument_code: str

        :returns: float

        >>> data=csvFuturesData("sysdata.tests")
        >>> data.get_value_of_block_price_move("EDOLLAR")
        2500
        """

        instr_data = self._get_instrument_data()
        block_move_value = instr_data.loc[instrument_code, 'Pointsize']

        return block_move_value

    def get_instrument_currency(self, instrument_code):
        """
        What is the currency that this instrument is priced in?

        :param instrument_code: instrument to get value for
        :type instrument_code: str

        :returns: str

        >>> data=csvFuturesData("sysdata.tests")
        >>> data.get_instrument_currency("US10")
        'USD'
        """

        instr_data = self._get_instrument_data()
        currency = instr_data.loc[instrument_code, 'Currency']

        return currency

    def _get_fx_data(self, currency1, currency2):
        """
        Get fx data

        :param currency1: numerator currency
        :type currency1: str

        :param currency2: denominator currency
        :type currency2: str

        :returns: Tx1 pd.DataFrame, or None if not available

        >>> data=csvFuturesData("sysdata.tests")
        >>> data._get_fx_data("EUR", "USD").tail(2)
        2015-12-09    1.09085
        2015-12-10    1.09641
        Name: FX, dtype: float64
        >>> data._get_fx_cross("EUR", "GBP").tail(2)
        2015-12-09    0.724663
        2015-12-10    0.724463
        Freq: B, Name: FX, dtype: float64
        2015-12-09    0.664311
        2015-12-10    0.660759
        dtype: float64
        >>> data._get_fx_cross( "GBP", "USD").tail(2)
        2015-12-09    1.50532
        2015-12-10    1.51341
        Name: FX, dtype: float64
        """

        self.log.msg("Loading csv fx data", fx="%s%s" % (currency1, currency2))

        if currency1 == currency2:
            return self._get_default_series()

        filename = os.path.join(self._datapath, "%s%sfx.csv" % (currency1,
                                                                currency2))
        try:
            fxdata = pd_readcsv(filename)
        except:
            return None

        fxdata = pd.Series(fxdata.iloc[:, 0])

        return fxdata


if __name__ == '__main__':
    import doctest
    doctest.testmod()
