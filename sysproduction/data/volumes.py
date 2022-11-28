import datetime as datetime
import pandas as pd
from syscore.objects import missing_contract, arg_not_supplied, missing_data
from sysdata.arctic.arctic_futures_per_contract_prices import (
    arcticFuturesContractPriceData,
)
from sysdata.futures.futures_per_contract_prices import futuresContractPriceData
from sysobjects.contracts import futuresContract
from sysdata.data_blob import dataBlob

from sysproduction.data.generic_production_data import productionDataLayerGeneric

# Get volume data for the contract we're currently trading, plus what we might roll into, plus the previous one
# This is handy for working out whether to roll

NOTIONALLY_ZERO_VOLUME = 0.0001


class diagVolumes(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_object(arcticFuturesContractPriceData)
        return data

    @property
    def db_futures_contract_price_data(self) -> futuresContractPriceData:
        return self.data.db_futures_contract_price

    def get_normalised_smoothed_volumes_of_contract_list(
        self, instrument_code: str, contract_date_str_list: list
    ) -> list:
        """

        :param instrument_code:
        :return: dict, keys are contract names
            Values are normalised volumes, with largest volume contract as 1.0
        """

        smoothed_volumes = self.get_smoothed_volumes_of_contract_list(
            instrument_code, contract_date_str_list
        )
        normalised_volumes = normalise_volumes(smoothed_volumes)

        return normalised_volumes

    def get_smoothed_volumes_of_contract_list(
        self, instrument_code: str, contract_date_str_list: list
    ) -> list:
        """
        Return list of most recent volumes, exponentially weighted

        :param instrument_code:
        :return: dict, keys are contract names with * (price), ** (forward) suffix. Values are volumes
        """

        smoothed_volumes = [
            self.get_smoothed_volume_for_contract(instrument_code, contract_date_str)
            for contract_date_str in contract_date_str_list
        ]

        return smoothed_volumes

    def get_smoothed_volume_for_contract(
        self, instrument_code: str, contract_date_str: str
    ) -> float:

        if contract_date_str is missing_contract:
            return 0.0
        contract = futuresContract(instrument_code, contract_date_str)
        volumes = self.get_daily_volumes_for_contract(contract)
        final_volume = get_smoothed_volume_ignoring_old_data(volumes)

        return final_volume

    def get_daily_volumes_for_contract(self, contract: futuresContract) -> pd.Series:
        price_data = self.db_futures_contract_price_data.get_merged_prices_for_contract_object(
            contract
        )

        if len(price_data) == 0:
            return missing_data

        volumes = price_data.daily_volumes()

        return volumes


def normalise_volumes(smoothed_volumes: list) -> list:
    ## normalise to first contract, normally priced
    normalised_to_volume = smoothed_volumes[0]
    if normalised_to_volume == 0.0:
        normalised_to_volume = NOTIONALLY_ZERO_VOLUME
    normalised_volumes = [volume / normalised_to_volume for volume in smoothed_volumes]

    return normalised_volumes


def get_smoothed_volume_ignoring_old_data(
    volumes: pd.Series, ignore_before_days=14, span: int = 3
) -> float:
    if volumes is missing_data:
        return 0.0

    # ignore anything more than say 2 weeks old (so we don't get stale data)
    two_weeks_ago = datetime.datetime.now() - datetime.timedelta(
        days=ignore_before_days
    )
    recent_volumes = volumes[two_weeks_ago:]

    if len(recent_volumes) == 0:
        return 0.0

    smoothed_recent_volumes = recent_volumes.ewm(span=span).mean()
    final_volume = smoothed_recent_volumes[-1]

    return final_volume
