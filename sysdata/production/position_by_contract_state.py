from syscore.objects import _named_object, success
from sysdata.data import baseData
from syslogdiag.log import logtoscreen
from sysdata.futures.contracts import futuresContract

default_position = 0
no_position_available = _named_object("No position")

class positionByContractData(baseData):
    """
    Store and retrieve the position we currently have in a given futures contract

    """
    def __init__(self, log=logtoscreen("rollStateData")):

        super().__init__(log=log)

        self._roll_dict={}
        self.name = "positionByContractData"

    def get_position_for_instrument_and_contract_date(self, instrument_code, contract_date):
        contract_object = futuresContract(instrument_code, contract_date)

        position = self.get_position_for_contract(contract_object)

        return position

    def update_position_for_instrument_and_contract_date(self, instrument_code, contract_date, new_position):
        contract_object = futuresContract(instrument_code, contract_date)
        self.update_position(contract_object, new_position)

        return success

    def get_position_for_contract(self, contract_object):
        position = self._get_position_for_contract_no_default(contract_object)
        if position is no_position_available:
            position = default_position
            self.update_position(contract_object, position)

        position = int(position)

        return position

    def _get_position_for_contract_no_default(self, contract_object):
        raise NotImplementedError("")

    def update_position(self, contract_object, new_position):
        raise NotImplementedError("Need to use inheriting class")

    def get_list_of_instruments(self):
        raise NotImplementedError("Need to use inheriting class")

    def get_all_positions_for_instrument(self, instrument_code):
        """

        :return: dict, keys are contract_date YYYYMMDD, positions are values
        """

        list_of_contract_ids = self.get_list_of_contracts_with_positions(instrument_code)
        dict_of_positions = dict([
            (contract_id, self.get_position_for_instrument_and_contract_date(instrument_code, contract_id))
            for contract_id in list_of_contract_ids])

        return dict_of_positions

    def get_list_of_contracts_with_positions(self, instrument_code):
        """

        :return: list of str contract_date YYYYMMDD
        """
        raise NotImplementedError("Need to use inheriting class")