from syslogdiag.log import logtoscreen
from sysdata.production.positions import contractPositionData
from sysdata.futures.contracts import futuresContract
from sysbrokers.IB.ibFuturesContracts import ibFuturesContractData

import pandas as pd

class ibContractPositionData(contractPositionData, ibFuturesContractData):
    def __init__(self, ibconnection, log=logtoscreen("ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB Futures per contract position data %s" % str(self.ibconnection)

    def _contract_tuple_given_contract(self, contract_object):
        key = self._keyname_given_contract_object(contract_object)
        instrument_code, contract_id = self._contract_tuple_given_keyname(key)

        return instrument_code, contract_id

    def get_all_futures_positions_as_list(self):
        all_positions = self.ibconnection.broker_get_positions()

        return all_positions['FUT']

    def get_current_position_for_contract_object(self, contract_object):
        instrument_code, _ = self._contract_tuple_given_contract(contract_object)
        actual_expiry = self.get_actual_expiry_date_for_contract(contract_object)
        ib_symbol = self.get_brokers_instrument_code(instrument_code)
        all_positions = self.get_all_futures_positions_as_list()
        position = [position_entry['position'] for position_entry in all_positions if
                    position_entry['symbol']==ib_symbol and position_entry['expiry']==actual_expiry]
        return position

    def get_list_of_instruments_with_any_position(self):
        all_positions = self.get_all_futures_positions_as_list()
        all_ib_symbols = [position_entry['symbol'] for position_entry in all_positions]
        unique_ib_symbols = list(set(all_ib_symbols))
        resolved_instrument_codes = [self.get_instrument_code_from_broker_code(ib_code)
                                     for ib_code in unique_ib_symbols]
        resolved_instrument_codes.sort()

        return resolved_instrument_codes

    def get_all_current_positions_as_list_with_contract_objects(self):
        all_positions = self.get_all_futures_positions_as_list()
        current_positions = []
        for position_entry in all_positions:
            ib_code =  position_entry['symbol']
            instrument_code = self.get_instrument_code_from_broker_code(ib_code)
            expiry = position_entry['expiry']
            contract = futuresContract(instrument_code, expiry)
            position = position_entry['position']
            if position==0:
                continue
            current_positions.append((contract, position))

        return current_positions


    def get_all_current_positions_as_df(self):
        positions_as_list = self.get_all_current_positions_as_list_with_contract_objects()
        list_instruments = [position[0].instrument_code for position in positions_as_list]
        list_contract_dates = [position[0].date for position in positions_as_list]
        current_positions = [position[1] for position in positions_as_list]

        ans = pd.DataFrame(dict(instrument=list_instruments, contract_date=list_contract_dates,
                                position=current_positions))

        return ans.sort_values(["instrument", "contract_date"])

    def get_position_as_df_for_contract_object(self, *args, **kwargs):
        raise Exception("Only current position data available from IB")

    def update_position_for_contract_object(self, *args, **kwargs):
        raise Exception("IB position data is read only")

    def delete_last_position_for_contract_object(self, *args, **kwargs):
        raise Exception("IB position data is read only")

    def _get_series_for_args_dict(self, *args, **kwargs):
        raise Exception("Only current position data available from IB")

    def _update_entry_for_args_dict(self, *args, **kwargs):
        raise Exception("IB position data is read only")

    def _delete_last_entry_for_args_dict(self, *args, **kwargs):
        raise Exception("IB position data is read only")

