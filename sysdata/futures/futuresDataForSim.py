
import pandas as pd

from sysdata.data import simData

OVERIDE_ERROR = "You probably need to replace this method to do anything useful"

class futuresAdjustedPriceData(simData):
    """
    Futures specific stuff related to prices
    """

    def __repr__(self):
        return "futuresPriceData don't use"

    def get_raw_price(self, instrument_code):
        """
        For  futures the price is the backadjusted price

        :param instrument_code:
        :return: price
        """

        return self.get_backadjusted_futures_price(instrument_code)

    def get_backadjusted_futures_price(self, instrument_code):
        """

        :param instrument_code:
        :return:
        """

        self.log.critical(OVERIDE_ERROR)

class futuresMultiplePriceData(simData):
    """
    Futures specific stuff related to carry, and optionally getting forward prices for back adjusting from scratch
    """

    def _get_all_price_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 6 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT, FORWARD_, FORWARD_CONTRACT

        These are specifically needed for futures trading

        We'd inherit from this method for a specific data source

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        """

        self.log.critical(OVERIDE_ERROR)


    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

        These are specifically needed for futures trading

        We'd inherit from this method for a specific data source

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        """

        all_price_data = self._get_all_price_data(instrument_code)

        return all_price_data[['PRICE', 'CARRY', 'PRICE_CONTRACT', 'CARRY_CONTRACT']]

    def get_current_and_forward_price_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, PRICE_CONTRACT, FORWARD_, FORWARD_CONTRACT

        These are required if we want to backadjust from scratch

        We'd inherit from this method for a specific data source

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        """

        all_price_data = self._get_all_price_data(instrument_code)

        return all_price_data[['PRICE', 'FORWARD', 'PRICE_CONTRACT', 'FORWARD_CONTRACT']]


class futuresConfigDataForSim(simData):
    """
    Futures specific configuration data, eg costs etc
    """

    def _get_all_cost_data(self):
        """
        Get a data frame of cost data

        :returns: pd.DataFrame

        """
        self.log.critical(OVERIDE_ERROR)


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



    def _get_instrument_data(self):
        """
        Get a data frame of interesting information about instruments, either
        from a file or cached

        :returns: pd.DataFrame

        """

        self.log.critical(OVERIDE_ERROR)

    def get_instrument_list(self):
        """
        list of instruments in this data set

        :returns: list of str
        """

        instr_data = self._get_instrument_data()

        return list(instr_data.Instrument)

    def get_instrument_asset_classes(self):
        """
        Returns dataframe with index of instruments, column AssetClass
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

        """

        instr_data = self._get_instrument_data()
        currency = instr_data.loc[instrument_code, 'Currency']

        return currency




class futuresSimData(futuresAdjustedPriceData, futuresConfigDataForSim, futuresMultiplePriceData):
    def __repr__(self):
        raise Exception(OVERIDE_ERROR)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
