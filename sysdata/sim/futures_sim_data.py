import pandas as pd

from syscore.constants import missing_instrument
from sysdata.sim.sim_data import simData

from sysobjects.adjusted_prices import futuresAdjustedPrices
from sysobjects.instruments import (
    assetClassesAndInstruments,
    instrumentCosts,
    futuresInstrumentWithMetaData,
)
from sysobjects.multiple_prices import futuresMultiplePrices
from sysobjects.dict_of_named_futures_per_contract_prices import (
    price_name,
    carry_name,
    forward_name,
    contract_name_from_column_name,
)
from sysobjects.rolls import rollParameters

price_contract_name = contract_name_from_column_name(price_name)
carry_contract_name = contract_name_from_column_name(carry_name)
forward_contract_name = contract_name_from_column_name(forward_name)


class futuresSimData(simData):
    def __repr__(self):
        return "futuresSimData object with %d instruments" % len(
            self.get_instrument_list()
        )

    def all_asset_classes(self) -> list:
        asset_class_data = self.get_instrument_asset_classes()

        return asset_class_data.all_asset_classes()

    def all_instruments_in_asset_class(self, asset_class: str) -> list:
        """
        Return all the instruments in a given asset class

        :param asset_class: str
        :return: list of instrument codes
        """
        asset_class_data = self.get_instrument_asset_classes()
        list_of_instrument_codes = self.get_instrument_list()
        asset_class_instrument_list = asset_class_data.all_instruments_in_asset_class(
            asset_class, must_be_in=list_of_instrument_codes
        )

        return asset_class_instrument_list

    def asset_class_for_instrument(self, instrument_code: str) -> str:
        """
        Which asset class is some instrument in?

        :param instrument_code:
        :return: str
        """

        asset_class_data = self.get_instrument_asset_classes()
        asset_class = asset_class_data[instrument_code]

        return asset_class

    def length_of_history_in_days_for_instrument(self, instrument_code: str) -> int:
        return len(self.daily_prices(instrument_code))

    def get_raw_price_from_start_date(
        self, instrument_code: str, start_date
    ) -> pd.Series:
        """
        For  futures the price is the backadjusted price

        :param instrument_code:
        :return: price
        """
        price = self.get_backadjusted_futures_price(instrument_code)

        return price[start_date:]

    def get_instrument_raw_carry_data(self, instrument_code: str) -> pd.DataFrame:
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

        These are specifically needed for futures trading

        We'd inherit from this method for a specific data source

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        """

        all_price_data = self.get_multiple_prices(instrument_code)
        carry_data = all_price_data[
            [price_name, carry_name, price_contract_name, carry_contract_name]
        ]

        return carry_data

    def get_current_and_forward_price_data(self, instrument_code: str) -> pd.DataFrame:
        """
        Returns a pd. dataframe with the 4 columns PRICE, PRICE_CONTRACT, FORWARD_, FORWARD_CONTRACT

        These are required if we want to backadjust from scratch

        We'd inherit from this method for a specific data source

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        """

        all_price_data = self.get_multiple_prices(instrument_code)

        return all_price_data[
            [price_name, forward_name, price_contract_name, forward_contract_name]
        ]

    def get_rolls_per_year(self, instrument_code: str) -> int:
        roll_parameters = self.get_roll_parameters(instrument_code)
        rolls_per_year = roll_parameters.rolls_per_year_in_hold_cycle()

        return rolls_per_year

    def get_raw_cost_data(self, instrument_code: str) -> instrumentCosts:
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

        cost_data_object = self.get_instrument_object_with_meta_data(instrument_code)

        if cost_data_object is missing_instrument:
            self.log.warn(
                "Cost data missing for %s will use zero costs" % instrument_code
            )
            return instrumentCosts()

        instrument_meta_data = cost_data_object.meta_data
        instrument_costs = instrumentCosts.from_meta_data(instrument_meta_data)

        return instrument_costs

    def get_value_of_block_price_move(self, instrument_code: str) -> float:
        """
        How much is a $1 move worth in value terms?

        :param instrument_code: instrument to get value for
        :type instrument_code: str

        :returns: float

        """

        instr_object = self.get_instrument_object_with_meta_data(instrument_code)
        meta_data = instr_object.meta_data
        block_move_value = meta_data.Pointsize

        return block_move_value

    def get_instrument_currency(self, instrument_code: str) -> str:
        """
        What is the currency that this instrument is priced in?

        :param instrument_code: instrument to get value for
        :type instrument_code: str

        :returns: str

        """
        instr_object = self.get_instrument_object_with_meta_data(instrument_code)
        meta_data = instr_object.meta_data
        currency = meta_data.Currency

        return currency

    def get_instrument_asset_classes(self) -> assetClassesAndInstruments:
        """

        :return: A pd.Series, row names are instruments, content is asset class
        """

        raise NotImplementedError()

    def get_backadjusted_futures_price(
        self, instrument_code: str
    ) -> futuresAdjustedPrices:
        """

        :param instrument_code:
        :return:
        """

        raise NotImplementedError()

    def get_multiple_prices(self, instrument_code: str) -> futuresMultiplePrices:
        start_date = self.start_date_for_data()

        return self.get_multiple_prices_from_start_date(
            instrument_code, start_date=start_date
        )

    def get_multiple_prices_from_start_date(
        self, instrument_code: str, start_date
    ) -> futuresMultiplePrices:
        raise NotImplementedError()

    def get_instrument_meta_data(
        self, instrument_code
    ) -> futuresInstrumentWithMetaData:
        """
        Get a futures instrument where the meta data is cost data

        :returns: futuresInstrument

        """
        raise NotImplementedError()

    def get_roll_parameters(self, instrument_code: str) -> rollParameters:
        raise NotImplementedError

    def get_instrument_object_with_meta_data(
        self, instrument_code: str
    ) -> futuresInstrumentWithMetaData:
        """
        Get data about an instrument, as a futuresInstrument

        :param instrument_code:
        :return: futuresInstrument object
        """

        raise NotImplementedError()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
