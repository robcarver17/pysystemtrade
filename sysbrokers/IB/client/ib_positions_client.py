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

        raw_positions = self.ib.positions()
        dict_of_positions = from_ib_positions_to_dict(
            raw_positions, account_id=account_id
        )

        return dict_of_positions
