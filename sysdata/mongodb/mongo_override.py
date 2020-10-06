from syscore.objects import missing_data
from sysdata.production.override import overrideData, Override
from sysdata.mongodb.mongo_connection import mongoConnection
from syslogdiag.log import logtoscreen

OVERRIDE_STATUS_COLLECTION = "overide_status"


class mongoOverrideData(overrideData):
    """
    Read and write data class to get override state data


    """

    def __init__(self, mongo_db=None, log=logtoscreen("mongoOverrideData")):
        super().__init__(log=log)

        self._mongo = mongoConnection(
            OVERRIDE_STATUS_COLLECTION, mongo_db=mongo_db)

        self.name = "Data connection for override data, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name,
            self._mongo.collection_name,
            self._mongo.host,
            self._mongo.port,
        )

    def __repr__(self):
        return self.name

    def _get_override_object_for_key(self, dict_name, key):
        override_value = self._get_override_value_for_key(dict_name, key)
        if override_value is missing_data:
            override_value = 1.0
        override = Override.from_float(override_value)

        return override

    def _get_override_value_for_key(self, dict_name, key):
        # return missing_data if nothing found
        result_dict = self._mongo.collection.find_one(
            dict(dict_name=dict_name, key=key)
        )
        if result_dict is None:
            return missing_data

        value = result_dict["value"]

        return value

    def _update_override(self, dict_name, key, new_override_object):
        new_override_as_float = new_override_object.as_float()

        old_override_as_float = self._get_override_value_for_key(
            dict_name, key)

        if old_override_as_float is missing_data:
            # we don't have a value already, let's think about adding one
            if new_override_as_float == 1.0:
                # pointess and a waste of disk space
                result = None
            else:
                result = self._add_override_value(
                    dict_name, key, new_override_as_float)
        else:
            # We have a value, let's think about updating
            if new_override_as_float == 1.0:
                # same as no override, so we delete for tidiness
                result = self._delete_existing_override_value(dict_name, key)
            else:
                # some other value let's update it
                result = self._update_existing_override_value(
                    dict_name, key, new_override_as_float
                )

        return result

    def _add_override_value(self, dict_name, key, override_as_float):
        self.log.msg(
            "Add new override for %s %s to %f" %
            (dict_name, key, override_as_float))
        object_dict = dict(
            dict_name=dict_name,
            key=key,
            value=override_as_float)
        self._mongo.collection.insert_one(object_dict)

    def _update_existing_override_value(
            self, dict_name, key, override_as_float):
        self.log.msg(
            "Update override for %s %s to %f" %
            (dict_name, key, override_as_float))

        find_object_dict = dict(dict_name=dict_name, key=key)
        new_values_dict = {"$set": {"value": override_as_float}}
        self._mongo.collection.update_one(
            find_object_dict, new_values_dict, upsert=True
        )

    def _delete_existing_override_value(self, dict_name, key):
        self.log.msg(
            "Deleting override for %s %s"
            % (
                dict_name,
                key,
            )
        )

        self._mongo.collection.remove(dict(dict_name=dict_name, key=key))

    def _get_dict_of_items_with_overrides(self, dict_name):
        find_object_dict = dict(dict_name=dict_name)
        cursor = self._mongo.collection.find(find_object_dict)
        key_values = [
            (db_entry["key"], Override.from_float(db_entry["value"]))
            for db_entry in cursor
        ]
        result_dict = dict(key_values)

        return result_dict
