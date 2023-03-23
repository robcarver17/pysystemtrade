from syscore.constants import arg_not_supplied

from sysdata.mongodb.mongo_generic import mongoDataWithMultipleKeys
from syslogdiag.log_to_screen import logtoscreen


OPTIMAL_POSITION_COLLECTION = "optimal_positions"


class mongoOptimalPositionData(object):
    def __init__(self, mongo_db=arg_not_supplied, log=logtoscreen("")):
        self._log = log
        self._mongo_data = mongoDataWithMultipleKeys(
            OPTIMAL_POSITION_COLLECTION, mongo_db=mongo_db
        )

    @property
    def mongo_data(self):
        return self._mongo_data

    @property
    def log(self):
        return self._log
