from syscore.constants import arg_not_supplied
from sysbrokers.IB.client.ib_client import ibClient
from sysbrokers.IB.ib_positions import from_ib_positions_to_dict, positionsFromIB


class ibPositionsClient(ibClient):
    def broker_get_positions(
        self, account_id: str = arg_not_supplied
    ) -> positionsFromIB:
        # Get all the positions
        # We return these as a dict of pd DataFrame
        # dict entries are asset classes, columns are IB symbol, contract ID,
        # contract expiry

        list_of_raw_positions = self.ib.positions()
        raw_positions_with_codes = self.add_exchange_codes_to_list_of_raw_ib_positions(
            list_of_raw_positions
        )
        dict_of_positions = from_ib_positions_to_dict(
            raw_positions_with_codes, account_id=account_id
        )

        return dict_of_positions

    def add_exchange_codes_to_list_of_raw_ib_positions(
        self, list_of_raw_positions: list
    ) -> list:
        raw_positions_with_codes = [
            self.add_exchange_code_to_raw_ib_position(raw_position)
            for raw_position in list_of_raw_positions
        ]

        return raw_positions_with_codes

    def add_exchange_code_to_raw_ib_position(self, raw_ib_position):
        try:
            ib_contract = raw_ib_position.contract
            list_of_contract_details = self.ib.reqContractDetails(ib_contract)
            if len(list_of_contract_details) > 1:
                self.log.critical("Position should only have one contract associated")
            contract_details = list_of_contract_details[0]
            exchange_code = contract_details.validExchanges
        except:
            exchange_code = ""

        setattr(raw_ib_position, "exchange", exchange_code)

        return raw_ib_position
