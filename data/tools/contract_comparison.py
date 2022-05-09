from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysobjects.contracts import futuresContract
import pandas as pd


class ContractComparison:
    """Class for comparing futures contracts side by side on different dimensions"""

    def __init__(self, resample_period: str = "D"):
        """
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.
        If parameter is None original time frequency is returned
        """

        self.resample_period = resample_period

    def generate_contract_object(self, instrument_code: str, date_str: str):
        """
        :param instrument_code: symbol for instrument.
        :param date_str: Contract ID - for example; "20220500"

        :return: a pysystemtrade futures contract object
        """

        return futuresContract(instrument_object=instrument_code, contract_date_object=date_str)

    def get_contract_prices(self, futures_contract: futuresContract):
        """
        :param futures_contract: pysystemtrade futures contract object

        :return: a pysystemtrade dataframe with recorded prices for the contract
        """

        contract_prices = arcticFuturesContractPriceData()
        return contract_prices.get_prices_for_contract_object(futures_contract)

    def merge_contract_objects(self, price_prices: pd.DataFrame, forward_prices: pd.DataFrame):
        """
        :param price_prices: a pysystemtrade dataframe with recorded prices for the priced contract
        :param forward_prices: a pysystemtrade dataframe with recorded prices for the forward contract

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  columns separated with suffixes _price and _forward
        """

        return pd.merge(price_prices, forward_prices, how='outer', left_index=True, right_index=True,
                        suffixes=('_price', '_forward'))

    def create_comparison(self, instrument_code: str, price_date_str: str, forward_date_str: str):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  columns separated with suffixes _price and _forward
        """

        price_contract = self.generate_contract_object(instrument_code=instrument_code, date_str=price_date_str)
        forward_contract = self.generate_contract_object(instrument_code=instrument_code, date_str=forward_date_str)

        price_prices = self.get_contract_prices(futures_contract=price_contract)
        forward_prices = self.get_contract_prices(futures_contract=forward_contract)

        return self.merge_contract_objects(price_prices=price_prices, forward_prices=forward_prices)

    def create_volume_comparison(self, instrument_code: str, price_date_str: str, forward_date_str: str):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "VOLUME_price", "VOLUME_forward"
        """

        comparison_df = self.create_comparison(instrument_code=instrument_code,
                                               price_date_str=price_date_str,
                                               forward_date_str=forward_date_str)

        volume_comparison = comparison_df.drop(
            columns=['OPEN_price', 'OPEN_forward', 'HIGH_price', 'HIGH_forward', 'LOW_price', 'LOW_forward',
                     'FINAL_price', 'FINAL_forward'])

        if self.resample_period is not None:
            return volume_comparison.resample(self.resample_period).sum()

        else:
            return volume_comparison

    def create_price_comparison(self, instrument_code: str, price_date_str: str, forward_date_str: str):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "FINAL_price", "FINAL_forward"
        """

        comparison_df = self.create_comparison(instrument_code=instrument_code,
                                               price_date_str=price_date_str,
                                               forward_date_str=forward_date_str)

        volume_comparison = comparison_df.drop(
            columns=['OPEN_price', 'OPEN_forward', 'HIGH_price', 'HIGH_forward', 'LOW_price', 'LOW_forward',
                     'VOLUME_price', 'VOLUME_forward'])

        if self.resample_period is not None:
            return volume_comparison.resample(self.resample_period).sum()

        else:
            return volume_comparison

    def create_price_volume_comparison(self, instrument_code: str, price_date_str: str, forward_date_str: str):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "FINAL_price", "FINAL_forward"
        """

        comparison_df = self.create_comparison(instrument_code=instrument_code,
                                               price_date_str=price_date_str,
                                               forward_date_str=forward_date_str)

        volume_comparison = comparison_df.drop(
            columns=['OPEN_price', 'OPEN_forward', 'HIGH_price', 'HIGH_forward', 'LOW_price', 'LOW_forward'])

        if self.resample_period is not None:
            return volume_comparison.resample(self.resample_period).sum()

        else:
            return volume_comparison

    @classmethod
    def get_price_comparison(cls, instrument_code: str, price_date_str: str, forward_date_str: str,
                             resample_period: str = "D"):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.
        If parameter is None original time frequency is returned

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "FINAL_price", "FINAL_forward"
        """

        instance = cls(resample_period=resample_period)
        return instance.create_price_comparison(instrument_code=instrument_code, price_date_str=price_date_str,
                                                forward_date_str=forward_date_str)

    @classmethod
    def get_volume_comparison(cls, instrument_code: str, price_date_str: str, forward_date_str: str,
                              resample_period: str = "D"):
        """
        Convenience wrapper. Removes the need to instanciate the class.

        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.
        If parameter is None original time frequency is returned

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "VOLUME_price", "VOLUME_forward"
        """

        instance = cls(resample_period=resample_period)
        return instance.create_volume_comparison(instrument_code=instrument_code, price_date_str=price_date_str,
                                                 forward_date_str=forward_date_str)

    @classmethod
    def get_price_volume_comparison(cls, instrument_code: str, price_date_str: str, forward_date_str: str,
                                    resample_period: str = "D"):
        """
        Convenience wrapper. Removes the need to instanciate the class.

        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.
        If parameter is None original time frequency is returned

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "VOLUME_price", "VOLUME_forward"
        """

        instance = cls(resample_period=resample_period)
        return instance.create_price_volume_comparison(instrument_code=instrument_code, price_date_str=price_date_str,
                                                       forward_date_str=forward_date_str)
