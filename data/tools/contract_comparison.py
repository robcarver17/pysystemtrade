from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysobjects.contracts import futuresContract
import pandas as pd


class contractComparison:
    '''Class for comparing futures contracts side by side on different dimensions'''

    def _create_comparison(self, instrument_code: str, price_date_str: str, forward_date_str: str,
                           resample_period: str = "D"):
        '''
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  columns separated with suffixes _price and _forward
        '''
        price_contract = futuresContract(instrument_object=instrument_code, contract_date_object=date_str)
        forward_contract = futuresContract(instrument_object=instrument_code, contract_date_object=date_str)

        contract_prices = arcticFuturesContractPriceData()
        price_prices = contract_prices.get_prices_for_contract_object(price_contract)
        forward_prices = contract_prices.get_prices_for_contract_object(forward_contract)

        merged_contracts = pd.merge(price_prices,
                                    forward_prices,
                                    how='outer',
                                    left_index=True,
                                    right_index=True,
                                    suffixes=('_price', '_forward'))

        if resample_period is not None:
            return merged_contracts.resample(resample_period).sum()

        else:
            return merged_contracts

    def get_volume_comparison(self, instrument_code: str, price_date_str: str, forward_date_str: str,
                              resample_period: str = "D"):
        '''
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "VOLUME_price", "VOLUME_forward"
        '''

        comparison_df = self._create_comparison(instrument_code=instrument_code,
                                                price_date_str=price_date_str,
                                                forward_date_str=forward_date_str,
                                                resample_period=resample_period)

        return comparison_df.drop(
            columns=['OPEN_price', 'OPEN_forward', 'HIGH_price', 'HIGH_forward', 'LOW_price', 'LOW_forward',
                     'FINAL_price', 'FINAL_forward'])

    def get_price_comparison(self, instrument_code: str, price_date_str: str, forward_date_str: str,
                             resample_period: str = "D"):
        '''
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "FINAL_price", "FINAL_forward"
        '''

        comparison_df = self._create_comparison(instrument_code=instrument_code,
                                                price_date_str=price_date_str,
                                                forward_date_str=forward_date_str,
                                                resample_period=resample_period)

        return comparison_df.drop(
            columns=['OPEN_price', 'OPEN_forward', 'HIGH_price', 'HIGH_forward', 'LOW_price', 'LOW_forward',
                     'VOLUME_price', 'VOLUME_forward'])

    def get_price_volume_comparison(self, instrument_code: str, price_date_str: str, forward_date_str: str,
                                    resample_period: str = "D"):
        '''
        :param instrument_code: symbol for instrument.
        :param price_date_str: Contract ID for the priced contract - for example; "20220500"
        :param forward_date_str: Contract ID for the forward contract - for example; "20220500"
        :param resample_period: Contract prices are recorded at hourly intervals. For
        comparison the frequency is resampled. Parameter specifies frequency. Default "D" is day.

        :return: a dataframe where prices from the priced and forward contracts are merged together.
                  two columns; "FINAL_price", "FINAL_forward"
        '''

        comparison_df = self._create_comparison(instrument_code=instrument_code,
                                                price_date_str=price_date_str,
                                                forward_date_str=forward_date_str,
                                                resample_period=resample_period)

        return comparison_df.drop(
            columns=['OPEN_price', 'OPEN_forward', 'HIGH_price', 'HIGH_forward', 'LOW_price', 'LOW_forward'])
