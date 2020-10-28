import datetime as datetime

from syscore.objects import missing_contract, arg_not_supplied, missing_data
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysproduction.data.get_data import dataBlob


# Get volume data for the contract we're currently trading, plus what we might roll into, plus the previous one
# This is handy for working out whether to roll


class diagVolumes(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(arcticFuturesContractPriceData)
        self.data = data

    def get_normalised_smoothed_volumes_of_contract_list(
        self, instrument_code, contract_list, span=3
    ):
        """

        :param instrument_code:
        :return: dict, keys are contract names
            Values are normalised volumes, with largest volume contract as 1.0
        """

        smoothed_volumes = self.get_smoothed_volumes_of_contract_list(
            instrument_code, contract_list, span=span
        )
        max_smoothed_volume = max(smoothed_volumes)
        if max_smoothed_volume == 0.0:
            max_smoothed_volume = 0.0001
        normalised_volumes = [
            volume / max_smoothed_volume for volume in smoothed_volumes
        ]

        return normalised_volumes

    def get_smoothed_volumes_of_contract_list(
        self, instrument_code, contract_list, span=3
    ):
        """
        Return list of most recent volumes, exponentially weighted

        :param instrument_code:
        :return: dict, keys are contract names with * (price), ** (forward) suffix. Values are volumes
        """

        smoothed_volumes = [
            self.get_smoothed_volume_for_contract(
                instrument_code, contract_id, span=span
            )
            for contract_id in contract_list
        ]

        return smoothed_volumes

    def get_smoothed_volume_for_contract(
            self, instrument_code, contract_id, span=3):
        if contract_id is missing_contract:
            return 0.0

        volumes = self.get_daily_volumes_for_contract(
            instrument_code, contract_id)

        if volumes is missing_data:
            return 0.0

        # ignore anything more than 2 weeks old (so we don't get stale data)
        two_weeks_ago = datetime.datetime.now() - datetime.timedelta(days=14)
        recent_volumes = volumes[two_weeks_ago:]

        if len(recent_volumes) == 0:
            return 0.0

        final_volume = recent_volumes.ewm(span=span).mean()[-1]

        return final_volume

    def get_daily_volumes_for_contract(self, instrument_code, contract_id):
        data = self.data

        price_data = data.db_futures_contract_price.get_prices_for_instrument_code_and_contract_date(
            instrument_code, contract_id)

        if len(price_data) == 0:
            return missing_data

        volumes = price_data.daily_volumes()

        return volumes
