import pandas as pd

from syscore.objects import arg_not_supplied, missing_data
from sysobjects.contract_dates_and_expiries import listOfContractDateStr


class dictFuturesContractFinalPrices(dict):
    def __repr__(self):
        object_repr = "Dict of final futures contract prices with %d contracts" % len(
            self.keys())
        return object_repr

    def sorted_contract_date_str(self):
        """
        Time sorted contract ids
        :return:
        """

        all_contract_date_str = listOfContractDateStr(self.keys())
        all_contract_date_str_sorted = all_contract_date_str.sorted_date_str()

        return all_contract_date_str_sorted

    def last_contract_date_str(self):

        all_contract_date_str_sorted = self.sorted_contract_date_str()

        return all_contract_date_str_sorted.final_date_str()

    def joint_data(self):

        joint_data = [pd.Series(prices, name=contractid)
                      for contractid, prices in self.items()]
        joint_data = pd.concat(joint_data, axis=1)

        return joint_data

    def matched_prices(self, contracts_to_match=arg_not_supplied) -> pd.DataFrame:
        # Return pd.DataFrame where we only have prices in all contracts

        if contracts_to_match is arg_not_supplied:
            contracts_to_match = self.keys()

        joint_data = self.joint_data()
        joint_data_to_match = joint_data[contracts_to_match]

        matched_data = joint_data_to_match.dropna()

        if len(matched_data) == 0:
            # This will happen if there are no matches
            return missing_data

        return matched_data


class dictFuturesContractVolumes(dictFuturesContractFinalPrices):
    def __repr__(self):
        object_repr = "Dict of futures contract volumes with %d contracts" % len(
            self.keys())
        return object_repr


class dictFuturesContractPrices(dict):
    """
    A dict of futures contract prices

    Keys are contract_objects

    We can use standard dict methods, but convenience methods are included
    """

    def __repr__(self):
        object_repr = "Dict of futures contract prices with %d contracts" % len(
            self.keys())
        return object_repr

    def final_prices(self) ->dictFuturesContractFinalPrices:
        """

        :return: dict of final prices
        """

        all_contract_ids = list(self.keys())
        final_price_dict_as_list = []
        for contract_id in all_contract_ids:
            final_prices = self[contract_id].return_final_prices()
            final_prices.name = contract_id
            final_price_dict_as_list.append((contract_id, final_prices))

        final_prices_dict = dictFuturesContractFinalPrices(
            final_price_dict_as_list)

        return final_prices_dict

    def daily_volumes(self) ->dictFuturesContractVolumes:
        """

        :return: dict of daily volumes
        """

        all_contract_ids = list(self.keys())
        volume_dict_as_list = []
        for contract_id in all_contract_ids:
            volumes = self[contract_id].daily_volumes()
            volumes.name = contract_id
            volume_dict_as_list.append((contract_id, volumes))

        volumes_dict = dictFuturesContractVolumes(volume_dict_as_list)

        return volumes_dict




