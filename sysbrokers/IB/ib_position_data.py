from syslogdiag.log import logtoscreen
from sysbrokers.IB.ib_futures_contracts import ibFuturesContractData
from syscore.objects import arg_not_supplied, missing_contract
from sysdata.production.historic_positions import contractPositionData
from sysdata.production.current_positions import (
    listOfContractPositions,
    contractPosition,
)


class ibContractPositionData(contractPositionData):
    def __init__(self, ibconnection, log=logtoscreen(
            "ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB Futures per contract position data %s" % str(
            self.ibconnection)

    @property
    def futures_contract_data(self):
        return ibFuturesContractData(self.ibconnection)

    def _contract_tuple_given_contract(self, contract_object):
        key = self._keyname_given_contract_object(contract_object)
        instrument_code, contract_id = self._contract_tuple_given_keyname(key)

        return instrument_code, contract_id

    def _get_all_futures_positions_as_raw_list(
            self, account_id=arg_not_supplied):
        self.ibconnection.refresh()
        all_positions = self.ibconnection.broker_get_positions(
            account_id=account_id)
        positions = all_positions.get("FUT", [])
        return positions

    def get_current_position_for_contract_object(
        self, contract_object, account_id=arg_not_supplied
    ):
        instrument_code, _ = self._contract_tuple_given_contract(
            contract_object)
        actual_expiry = self.futures_contract_data.get_actual_expiry_date_for_contract(
            contract_object)
        if actual_expiry is missing_contract:
            return 0
        ib_symbol = self.futures_contract_data.get_brokers_instrument_code(
            instrument_code
        )
        all_positions = self._get_all_futures_positions_as_raw_list(
            account_id=account_id
        )
        position = [
            position_entry["position"]
            for position_entry in all_positions
            if position_entry["symbol"] == ib_symbol
            and position_entry["expiry"] == actual_expiry
        ]
        return sum(position)

    def get_list_of_instruments_with_any_position(
            self, account_id=arg_not_supplied):
        all_positions = self._get_all_futures_positions_as_raw_list(
            account_id=account_id
        )
        all_ib_symbols = [position_entry["symbol"]
                          for position_entry in all_positions]
        unique_ib_symbols = list(set(all_ib_symbols))
        resolved_instrument_codes = sorted([
            self.futures_contract_data.get_instrument_code_from_broker_code(ib_code)
            for ib_code in unique_ib_symbols
        ])

        return resolved_instrument_codes

    def get_all_current_positions_as_list_with_contract_objects(
        self, account_id=arg_not_supplied
    ):
        all_positions = self._get_all_futures_positions_as_raw_list(
            account_id=account_id
        )
        current_positions = []
        for position_entry in all_positions:
            ib_code = position_entry["symbol"]
            instrument_code = (
                self.futures_contract_data.get_instrument_code_from_broker_code(ib_code))
            expiry = position_entry["expiry"]
            position = position_entry["position"]
            if position == 0:
                continue
            contract_position_object = contractPosition(
                position, instrument_code, expiry
            )
            current_positions.append(contract_position_object)

        list_of_contract_positions = listOfContractPositions(current_positions)

        return list_of_contract_positions

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
