
from sysbrokers.IB.ib_client_id import ibClientIdData
from syscore.objects import arg_not_supplied
from sysdata.mongodb.mongo_generic import mongoData
from syslogdiag.log import logtoscreen

IB_CLIENT_COLLECTION = "IBClientTracker"
IB_ID_REF = 'client id'

class mongoIbClientIdData(ibClientIdData):
    """
    Read and write data class to get next used client id
    """

    def __init__(
        self,
        mongo_db=arg_not_supplied,
        idoffset=arg_not_supplied,
        log=logtoscreen("mongoIDTracker"),
    ):

        super().__init__(log=log, idoffset=idoffset)
        self._mongo_data = mongoData(IB_CLIENT_COLLECTION, IB_ID_REF, mongo_db)

    @property
    def mongo_data(self):
        return self._mongo_data

    def _repr__(self):
        return "Tracking IB client IDs, mongodb %" % (str(self.mongo_data))

    def _get_list_of_clientids(self) -> list:
        return self.mongo_data.get_list_of_keys()

    def _lock_clientid(self, next_id: int):
        lock_dict = {IB_ID_REF: next_id}
        self.mongo_data.add_data(lock_dict)
        self.log.msg("Locked IB client ID %d" % next_id)


    def release_clientid(self, clientid: int):
        """
        Delete a client id lock
        :param clientid:
        :return: None
        """
        self.mongo_data.delete_data_without_any_warning(clientid)
        self.log.msg("Released IB client ID %d" % clientid)


def get_next_id_from_current_list(current_list_of_ids: list, id_offset: int = 0) -> int:
    if len(current_list_of_ids) == 0:
        # no IDS in use
        return id_offset

    full_set_of_available_ids = set(
        range(id_offset, max(current_list_of_ids) + 1)
    )

    next_id = get_next_id_from_current_list_and_full_set(current_list_of_ids, full_set_of_available_ids)

    return next_id


def get_next_id_from_current_list_and_full_set(current_list_of_ids: list, full_set_of_available_ids: set) -> int:

    unused_values = full_set_of_available_ids - set(current_list_of_ids)
    if len(unused_values)==0:
        # no gaps, return the higest number plus 1
        return max(current_list_of_ids) + 1
    else:
        # there is a gap, use the lowest numbered one
        return min(unused_values)