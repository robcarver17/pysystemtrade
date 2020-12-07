from sysbrokers.IB.ib_connection import ib_defaults
from syscore.objects import arg_not_supplied
from sysdata.base_data import baseData
from sysdata.mongodb.mongo_connection import mongoDb, mongoConnection
from syslogdiag.log import logtoscreen

IB_CLIENT_COLLECTION = "IBClientTracker"


class mongoIBclientIdData(baseData):
    """
    Read and write data class to get next used client id
    """

    def __init__(
        self,
        mongo_db=arg_not_supplied,
        idoffset=arg_not_supplied,
        log=logtoscreen("mongoIDTracker"),
    ):

        super().__init__(log=log)
        if mongo_db is arg_not_supplied:
            mongo_db = mongoDb()

        if idoffset is arg_not_supplied:
            _notused_ipaddress, _notused_port, idoffset = ib_defaults()

        self._mongo = mongoConnection(IB_CLIENT_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("client_id")

        self.name = "Tracking IB client IDs, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name,
            self._mongo.collection_name,
            self._mongo.host,
            self._mongo.port,
        )

        self._idoffset = idoffset

    @property
    def log(self):
        return self._log

    def __repr__(self):
        return self.name

    def _is_clientid_used(self, clientid):
        """
        Checks if a clientis is in use
        :param clientid: int
        :return: bool
        """
        current_ids = self._get_list_of_clientids()
        if clientid in current_ids:
            return True
        else:
            return False

    def return_valid_client_id(self, clientid_to_try=None):
        """
        If clientid_to_try is None, return the next free ID
        If clientid_to_try is being used, return the next free ID, otherwise allow that to be used
        :param clientid_to_try: int or None
        :return: int
        """
        if clientid_to_try is None:
            clientid_to_use = self.get_next_clientid()

        elif self._is_clientid_used(clientid_to_try):
            # being used, get another one
            # this will also lock it
            clientid_to_use = self.get_next_clientid()
        else:
            # okay it's been passed, and we can use it. So let's lock and use
            # it
            clientid_to_use = clientid_to_try
            self._add_clientid(clientid_to_use)  # lock

        return clientid_to_use

    def get_next_clientid(self) -> int:
        """
        Returns a client id which will be locked so no other use can use it
        The clientid in question is the lowest available unused value
        :return: clientid
        """

        current_list_of_ids = self._get_list_of_clientids()
        next_id = get_next_id_from_current_list(current_list_of_ids, id_offset=self._idoffset)

        # lock
        self._add_clientid(next_id)

        return next_id

    def _get_list_of_clientids(self) -> list:
        cursor = self._mongo.collection.find()
        clientids = [db_entry["client_id"] for db_entry in cursor]

        return clientids

    def _add_clientid(self, next_id):
        self._mongo.collection.insert_one(dict(client_id=next_id))
        self.log.msg("Locked ID %d" % next_id)

    def clear_all_clientids(self):
        """
        Clear all the client ids
        Should be done daily
        :return:
        """
        self._mongo.collection.delete_many({})
        self.log.msg("Released all IDs")

    def release_clientid(self, clientid):
        """
        Delete a client id lock
        :param clientid:
        :return: None
        """

        self._mongo.collection.delete_one(dict(client_id=clientid))
        self.log.msg("Released ID %d" % clientid)


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