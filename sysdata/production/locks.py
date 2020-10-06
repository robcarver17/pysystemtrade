from syslogdiag.log import logtoscreen

lock_on = "ON"
lock_off = "OFF"


class lockData(object):
    def __init__(self, log=logtoscreen("Locks")):
        self.log = log
        self._locks = dict()

    def is_instrument_locked(self, instrument_code):
        if self.get_lock_for_instrument(instrument_code) == lock_on:
            return True
        else:
            return False

    def get_lock_for_instrument(self, instrument_code):
        self._locks.get(instrument_code, lock_off)

    def add_lock_for_instrument(self, instrument_code):
        self._locks[instrument_code] = lock_on

    def remove_lock_for_instrument(self, instrument_code):
        if self.is_instrument_locked(instrument_code):
            self._locks.pop(instrument_code)

    def get_list_of_locked_instruments(self):
        return self._locks.keys()
