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

    def get_instrument_list(self):
        """
        list of instruments in this data set

        :returns: list of str
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

    def get_all_multiple_prices(self, instrument_code: str):
        all_price_data = self._get_all_price_data(instrument_code)

        return all_price_data


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

        return all_price_data[["PRICE", "CARRY",
                               "PRICE_CONTRACT", "CARRY_CONTRACT"]]

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

        return all_price_data[
            ["PRICE", "FORWARD", "PRICE_CONTRACT", "FORWARD_CONTRACT"]
        ]


class futuresConfigDataForSim(simData):
    """
    Futures specific configuration data, eg costs etc
    """

    def _get_default_costs(self):
        """
        Default costs, if we don't find any

        :return: dict
        """
        default_costs = dict(
            price_slippage=0.0,
            value_of_block_commission=0.0,
            percentage_cost=0.0,
            value_of_pertrade_commission=0.0,
        )

        return default_costs

    def _get_instrument_object_with_cost_data(self, instrument_code):
        """
        Get a futures instrument where the meta data is cost data

        :returns: futuresInstrument

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

        cost_data_object = self._get_instrument_object_with_cost_data(
            instrument_code)

        if cost_data_object.empty():
            return self._get_default_costs()

        cost_dict = dict(
            price_slippage=cost_data_object.meta_data.Slippage,
            value_of_block_commission=cost_data_object.meta_data.PerBlock,
            percentage_cost=cost_data_object.meta_data.Percentage,
            value_of_pertrade_commission=cost_data_object.meta_data.PerTrade,
        )

        return cost_dict

    def get_all_instrument_data(self):
        """
        Get a data frame of interesting information about instruments, either
        from a file or cached

        :returns: pd.DataFrame

        """

        self.log.critical(OVERIDE_ERROR)

    def get_instrument_object(self, instrument_code):
        """
        Get data about an instrument, as a futuresInstrument

        :param instrument_code:
        :return: futuresInstrument object
        """

        self.log.critical(OVERIDE_ERROR)

    def get_instrument_asset_classes(self):
        """
        Returns dataframe with index of instruments, column AssetClass
        """
        instr_data = self.get_all_instrument_data()
        instr_assets = instr_data.AssetClass

        return instr_assets

    def get_value_of_block_price_move(self, instrument_code):
        """
        How much is a $1 move worth in value terms?

        :param instrument_code: instrument to get value for
        :type instrument_code: str

        :returns: float

        """

        instr_object = self.get_instrument_object(instrument_code)
        meta_data = instr_object.meta_data
        block_move_value = meta_data.Pointsize

        return block_move_value

    def get_instrument_currency(self, instrument_code):
        """
        What is the currency that this instrument is priced in?

        :param instrument_code: instrument to get value for
        :type instrument_code: str

        :returns: str

        """
        instr_object = self.get_instrument_object(instrument_code)
        meta_data = instr_object.meta_data
        currency = meta_data.Currency

        return currency


"""
This class isn't used; instead it shows the pattern for creating source specific versions of futuresSimData

These would inherit directly from source specific versions of futuresAdjustedPriceData... etc
"""


class futuresSimData(
    futuresAdjustedPriceData, futuresConfigDataForSim, futuresMultiplePriceData
):
    def __repr__(self):
        raise Exception(OVERIDE_ERROR)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
