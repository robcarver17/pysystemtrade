from syscore.objects import _named_object, success, arg_not_supplied
from sysdata.data import baseData
from syslogdiag.log import logtoscreen
from sysdata.futures.contracts import futuresContract


from sysdata.production.generic_timed_storage import timedEntry, listOfEntries, listOfEntriesData
from syscore.objects import failure

class Position(timedEntry):
    """
    Position, could be for an instrument or a contract

    """

    def _setup_args_data(self):
        self._star_args = ['position'] # compulsory args

    def _name_(self):
        return "Position"

    def _containing_data_class_name(self):
        return "sysdata.production.positions.listPositions"




class listPositions(listOfEntries):
    """
    A list of positions
    """

    def _entry_class(self):
        return Position



class instrumentPositionData(listOfEntriesData):
    """
    Store and retrieve the instrument positions assigned to a particular strategy

    We store the type of list in the data
    """
    def _name(self):
        return "instrumentPositionData"

    def _data_class_name(self):
        return "sysdata.production.positions.listPositions"

    def get_position_as_df_for_strategy_and_instrument(self, strategy_name, instrument_code):
        position_series = self._get_series_for_args_dict(dict(strategy_name = strategy_name,
                                                              instrument_code = instrument_code))
        df_object = position_series.as_pd_df()
        return df_object

    def get_current_position_for_strategy_and_instrument(self, strategy_name, instrument_code):
        current_position_entry = self._get_current_entry_for_args_dict(dict(strategy_name=strategy_name,
                                                                           instrument_code = instrument_code))

        return current_position_entry

    def update_position_for_strategy_and_instrument(self, strategy_name, instrument_code, position,
                                                    date = arg_not_supplied):

        position_entry = Position(position, date=date)
        try:
            self._update_entry_for_args_dict(position_entry, dict(strategy_name = strategy_name,
                                                                 instrument_code = instrument_code))
        except Exception as e:
            self.log.warn(
                "Error %s when updating position for %s/%s with %s" % (str(e), strategy_name,
                                                                    instrument_code, str(position_entry)))
            return failure

    def get_list_of_strategies_and_instruments_with_positions(self):
        list_of_args_dict = self._get_list_of_args_dict()
        strat_instr_tuples =[]
        for arg_entry in list_of_args_dict:
            strat_instr_tuples.append((arg_entry['strategy_name'], arg_entry['instrument_code']))

        return strat_instr_tuples

    def get_list_of_instruments_for_strategy_with_position(self, strategy_name):
        list_of_all_positions = self.get_list_of_strategies_and_instruments_with_positions()
        list_of_instruments = [position[1] for position in list_of_all_positions if position[0]==strategy_name]

        return list_of_instruments

    def delete_last_position_for_strategy_and_instrument(self, strategy_name, instrument_code, are_you_sure=False):
        self._delete_last_entry_for_args_dict(dict(strategy_name=strategy_name,
                                                   instrument_code = instrument_code),
                                                are_you_sure=are_you_sure)

class contractPositionData(listOfEntriesData):
    """
    Store and retrieve the instrument positions held in a particular instrument and contract
    These are *not* strategy specific. Strategies only know about instruments and don't care how their
       position is implemented.

    We store the type of list in the data
    """
    def _name(self):
        return "contractPositionData"

    def _data_class_name(self):
        return "sysdata.production.positions.listPositions"

    def _keyname_given_contract_object(self, futures_contract_object):
        """
        We could do this using the .ident() method of the contract object, but this way we keep control inside this class

        This will also allow us to deal with intramarket 'contracts'

        :param futures_contract_object: futuresContract
        :return: str
        """

        return futures_contract_object.instrument_code + "." + futures_contract_object.date

    def _contract_tuple_given_keyname(self, keyname):
        """
        Extract the two parts of a keyname

        We keep control of how we represent stuff inside the class

        :param keyname: str
        :return: tuple instrument_code, contract_date
        """
        keyname_as_list = keyname.split(".")
        instrument_code, contract_date = tuple(keyname_as_list)

        return instrument_code, contract_date

    def get_position_as_df_for_instrument_and_contract_date(self, instrument_code, contract_date):
        df_object = self._perform_method_for_instrument_and_contract_date("get_position_as_df_for_contract_object",
                                                                          instrument_code,
                                                                          contract_date)

        return df_object

    def get_current_position_for_instrument_and_contract_date(self, instrument_code, contract_date):
        position = self._perform_method_for_instrument_and_contract_date("get_current_position_for_contract_object",
                                                                         instrument_code,
                                                                         contract_date)

        return position

    def update_position_for_instrument_and_contract_date(self, instrument_code, contract_date, position,
                                                         date=arg_not_supplied):
        ans = self._perform_method_for_instrument_and_contract_date("update_position_for_contract_object",
                                                                    instrument_code,
                                                                    contract_date,
                                                                    position, date=date)
        return ans

    def delete_last_position_for_instrument_and_contract_date(self, instrument_code, contract_date, are_you_sure=False):
        ans = self._perform_method_for_instrument_and_contract_date("delete_last_position_for_contract_object",
                                                                    instrument_code,
                                                                    contract_date,
                                                                    are_you_sure=are_you_sure)
        return ans

    def _perform_method_for_instrument_and_contract_date(self, method_name, instrument_code, contract_date,
                                                         *args, **kwargs):
        contract_object = futuresContract(instrument_code, contract_date)
        method = getattr(self, method_name)
        return method(contract_object, *args, **kwargs)

    def get_position_as_df_for_contract_object(self, contract_object):
        contractid = self._keyname_given_contract_object(contract_object)
        position_series = self._get_series_for_args_dict(dict(contractid=contractid))
        df_object = position_series.as_pd_df()

        return df_object

    def get_current_position_for_contract_object(self, contract_object):
        contractid = self._keyname_given_contract_object(contract_object)
        current_position_entry = self._get_current_entry_for_args_dict(dict(contractid=contractid))
        return current_position_entry

    def update_position_for_contract_object(self, contract_object, position, date=arg_not_supplied):
        contractid = self._keyname_given_contract_object(contract_object)
        position_entry = Position(position, date=date)
        try:
            self._update_entry_for_args_dict(position_entry, dict(contractid=contractid))
        except Exception as e:
            self.log.warn(
                "Error %s when updating position for %s with %s" % (str(e), contractid, str(position_entry)))
            return failure
        return success

    def delete_last_position_for_contract_object(self, contract_object, are_you_sure=False):
        contractid = self._keyname_given_contract_object(contract_object)
        self._delete_last_entry_for_args_dict(dict(contractid=contractid),
                                              are_you_sure=are_you_sure)
        return success

    def get_list_of_instruments_with_any_position(self):
        all_positions_dict = self._get_list_of_args_dict()
        instrument_list = [self._contract_tuple_given_keyname(entry['contractid'])[0] for entry in all_positions_dict]

        return list(set(instrument_list))