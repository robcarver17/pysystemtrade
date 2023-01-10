from sysdata.arctic.arctic_futures_per_contract_prices import (
    arcticFuturesContractPriceData,
)
from sysobjects.contracts import futuresContract
import pandas as pd


class ContractComparison:
    """Class for comparing futures contracts side by side on different dimensions"""

    def _create_comparison(
        self, instrument_code: str, price_date_str: str, forward_date_str: str
    ):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  columns separated with suffixes _price and _forward
        """
        price_contract = futuresContract(
            instrument_object=instrument_code, contract_date_object=price_date_str
        )
        forward_contract = futuresContract(
            instrument_object=instrument_code, contract_date_object=forward_date_str
        )

        contract_prices = arcticFuturesContractPriceData()
        price_prices = contract_prices.get_merged_prices_for_contract_object(
            price_contract
        )
        forward_prices = contract_prices.get_merged_prices_for_contract_object(
            forward_contract
        )

        merged_contracts = pd.merge(
            price_prices,
            forward_prices,
            how="outer",
            left_index=True,
            right_index=True,
            suffixes=("_price", "_forward"),
        )

        return merged_contracts

    def get_volume_comparison(
        self,
        instrument_code: str,
        price_date_str: str,
        forward_date_str: str,
        resample_period: str = "D",
    ):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.
        If None raw time index for data is given.

        :return: a dataframe where volume data from the priced and forward contracts are merged together.
                  two columns; "VOLUME_price", "VOLUME_forward". If resampled, aggregate volume is shown
        """

        comparison_df = self._create_comparison(
            instrument_code=instrument_code,
            price_date_str=price_date_str,
            forward_date_str=forward_date_str,
        )

        comparison_df = comparison_df.drop(
            columns=[
                "OPEN_price",
                "OPEN_forward",
                "HIGH_price",
                "HIGH_forward",
                "LOW_price",
                "LOW_forward",
                "FINAL_price",
                "FINAL_forward",
            ]
        )

        if resample_period is not None:
            return comparison_df.resample(resample_period).sum()

        else:
            return comparison_df

    def get_price_comparison(
        self,
        instrument_code: str,
        price_date_str: str,
        forward_date_str: str,
        resample_period: str = "D",
    ):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.
        If None raw time index for data is given.

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "FINAL_price", "FINAL_forward" - these are the last price observation per
                  resample_period
        """

        comparison_df = self._create_comparison(
            instrument_code=instrument_code,
            price_date_str=price_date_str,
            forward_date_str=forward_date_str,
        )

        comparison_df = comparison_df.drop(
            columns=[
                "OPEN_price",
                "OPEN_forward",
                "HIGH_price",
                "HIGH_forward",
                "LOW_price",
                "LOW_forward",
                "VOLUME_price",
                "VOLUME_forward",
            ]
        )

        if resample_period is not None:
            return comparison_df.resample(resample_period).last()

        else:
            return comparison_df

    def get_price_volume_comparison(
        self,
        instrument_code: str,
        price_date_str: str,
        forward_date_str: str,
        resample_period: str = "D",
    ):
        """
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.
        If None raw time index for data is given.

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  four columns; "FINAL_price", "FINAL_forward", "VOLUME_price", "VOLUME_forward"
                  volumes are aggregated per resample_period, while prices are last registered price
                  for each resample_period.
        """

        price_comparison_df = self.get_price_comparison(
            instrument_code=instrument_code,
            price_date_str=price_date_str,
            forward_date_str=forward_date_str,
            resample_period=resample_period,
        )

        volume_comparison_df = self.get_volume_comparison(
            instrument_code=instrument_code,
            price_date_str=price_date_str,
            forward_date_str=forward_date_str,
            resample_period=resample_period,
        )

        merged_comparisons = pd.merge(
            price_comparison_df,
            volume_comparison_df,
            how="outer",
            left_index=True,
            right_index=True,
        )

        return merged_comparisons
