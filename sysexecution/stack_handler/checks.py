from syscore.constants import arg_not_supplied

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore

from sysobjects.production.tradeable_object import futuresContract

from sysproduction.data.positions import diagPositions
from sysproduction.data.controls import dataLocks
from sysproduction.data.broker import dataBroker


class stackHandlerChecks(stackHandlerCore):
    # Do various checks
    # If really bad things happen we warn the user, and for some things do not allow any more trading to take place
    # until fixed.
    # We do these regularly, but also at the end of the day (daily reporting)

    def check_internal_position_break(self):
        diag_positions = diagPositions(self.data)
        breaks = (
            diag_positions.get_list_of_breaks_between_contract_and_strategy_positions()
        )
        for tradeable_object in breaks:
            self.log.critical(
                "Internal break for %s not locking just warning"
                % (str(tradeable_object))
            )

    def check_external_position_break(self):
        data_broker = dataBroker(self.data)
        breaks = (
            data_broker.get_list_of_breaks_between_broker_and_db_contract_positions()
        )

        self.log_and_lock_new_breaks(breaks)
        self.clear_position_locks_where_breaks_fixed(breaks)

    def log_and_lock_new_breaks(self, breaks: list):
        for contract in breaks:
            self.log_and_lock_position_break(contract)

        return breaks

    def log_and_lock_position_break(self, contract: futuresContract):
        instrument_code = contract.instrument_code
        data_locks = dataLocks(self.data)
        if data_locks.is_instrument_locked(instrument_code):
            # already locked
            return None
        else:
            self.log.critical("Break for %s: locking instrument" % (str(contract)))
            data_locks.add_lock_for_instrument(instrument_code)

    def clear_position_locks_where_breaks_fixed(self, breaks: list):
        data_locks = dataLocks(self.data)
        locked_instruments = data_locks.get_list_of_locked_instruments()
        instruments_with_breaks = [
            tradeable_object.instrument_code for tradeable_object in breaks
        ]
        for instrument in locked_instruments:
            instrument_is_locked_but_no_longer_has_a_break = (
                instrument not in instruments_with_breaks
            )
            if instrument_is_locked_but_no_longer_has_a_break:
                self.log.debug("Clearing lock for %s" % instrument)
                data_locks.remove_lock_for_instrument(instrument)
            else:
                # instrument has a break and needs a break
                pass

    def clear_position_locks_no_checks(self, instrument_code: str = arg_not_supplied):
        data_locks = dataLocks(self.data)
        if instrument_code is arg_not_supplied:
            locked_instruments = data_locks.get_list_of_locked_instruments()
        else:
            locked_instruments = [instrument_code]
        for instrument in locked_instruments:
            self.log.debug("Clearing lock for %s" % instrument)
            data_locks.remove_lock_for_instrument(instrument)
