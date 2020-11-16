import pandas as pd

from syscore.objects import data_error
from syscore.pdutils import sumup_business_days_over_pd_series_without_double_counting_of_closing_data, \
    full_merge_of_existing_data, merge_newer_data

PRICE_DATA_COLUMNS = sorted(["OPEN", "HIGH", "LOW", "FINAL", "VOLUME"])
FINAL_COLUMN = "FINAL"
VOLUME_COLUMN = "VOLUME"



class futuresContractPrices(pd.DataFrame):
    """
    simData frame in specific format containing per contract information
    """

    def __init__(self, data):
        """

        :param data: pd.DataFrame or something that could be passed to it
        """

        _validate_price_data(data)
        super().__init__(data)

        data.index.name = "index"  # for arctic compatibility

    @classmethod
    def create_empty(futuresContractPrices):
        """
        Our graceful fail is to return an empty, but valid, dataframe
        """

        data = pd.DataFrame(columns=PRICE_DATA_COLUMNS)

        futures_contract_prices = futuresContractPrices(data)

        return futures_contract_prices

    @classmethod
    def create_from_final_prirces_only(futuresContractPrices, data):
        data = pd.DataFrame(data, columns=[FINAL_COLUMN])
        data = data.reindex(columns=PRICE_DATA_COLUMNS)

        futures_contract_prices = futuresContractPrices(data)

        return futures_contract_prices

    def return_final_prices(self):
        data = self[FINAL_COLUMN]

        return futuresContractFinalPrices(data)

    def volumes(self):
        data = self[VOLUME_COLUMN]

        return data

    def daily_volumes(self):
        volumes = self.volumes()

        # stop double counting
        daily_volumes = sumup_business_days_over_pd_series_without_double_counting_of_closing_data(volumes)

        return daily_volumes

    def merge_with_other_prices(
            self,
            new_futures_per_contract_prices,
            only_add_rows=True,
            check_for_spike=True):
        """
        Merges self with new data.
        If only_add_rows is True,
        Otherwise: Any Nan in the existing data will be replaced (be careful!)

        :param new_futures_per_contract_prices: another futures per contract prices object

        :return: merged futures_per_contract object
        """
        if only_add_rows:
            return self.add_rows_to_existing_data(
                new_futures_per_contract_prices,
                check_for_spike=check_for_spike)
        else:
            return self._full_merge_of_existing_data(
                new_futures_per_contract_prices)

    def _full_merge_of_existing_data(self, new_futures_per_contract_prices):
        """
        Merges self with new data.
        Any Nan in the existing data will be replaced (be careful!)

        :param new_futures_per_contract_prices: the new data
        :return: updated data, doesn't update self
        """

        merged_data = full_merge_of_existing_data(
            self, new_futures_per_contract_prices)

        return futuresContractPrices(merged_data)

    def remove_zero_volumes(self):
        new_data = self[self[VOLUME_COLUMN] > 0]
        return futuresContractPrices(new_data)

    def add_rows_to_existing_data(
        self, new_futures_per_contract_prices, check_for_spike=True
    ):
        """
        Merges self with new data.
        Only newer data will be added

        :param new_futures_per_contract_prices: another futures per contract prices object

        :return: merged futures_per_contract object
        """

        merged_futures_prices = merge_newer_data(
            pd.DataFrame(self),
            new_futures_per_contract_prices,
            check_for_spike=check_for_spike,
            column_to_check=FINAL_COLUMN,
        )

        if merged_futures_prices is data_error:
            return data_error

        merged_futures_prices = futuresContractPrices(merged_futures_prices)

        return merged_futures_prices


class futuresContractFinalPrices(pd.Series):
    """
    Just the final prices from a futures contract
    """

    def __init__(self, data):
        super().__init__(data)

def _validate_price_data(data: pd.DataFrame):
    data_present = sorted(data.columns)

    try:
        assert data_present == PRICE_DATA_COLUMNS
    except AssertionError:
        raise Exception("futuresContractPrices has to conform to pattern")








