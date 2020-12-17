from syscontrol.data_objects import controlProcess
from sysdata.production.process_control_data import controlProcessData
from syscore.objects import missing_data, arg_not_supplied

from sysdata.mongodb.mongo_generic import mongoDataWithSingleKey
from syslogdiag.log import logtoscreen

PROCESS_CONTROL_COLLECTION = "process_control"
PROCESS_CONTROL_KEY = "process_name"

class mongoControlProcessData(controlProcessData):
    """
    Read and write data class to get process control data


    """

    def __init__(
            self,
            mongo_db=arg_not_supplied,
            log=logtoscreen("mongoControlProcessData")):

        super().__init__(log=log)

        self._mongo_data = mongoDataWithSingleKey(PROCESS_CONTROL_COLLECTION, PROCESS_CONTROL_KEY, mongo_db=mongo_db)

    @property
    def mongo_data(self):
        return self._mongo_data

    def __repr__(self):
        return "Data connection for process control, mongodb %s" % str(self.mongo_data)

    def get_list_of_process_names(self):
        return self.mongo_data.get_list_of_keys()

    def _get_control_for_process_name_without_default(self, process_name):
        result_dict = self.mongo_data.get_result_dict_for_key_without_key_value(process_name)
        if result_dict is missing_data:
            return missing_data

        control_object = controlProcess.from_dict(result_dict)

        return control_object

    def _modify_existing_control_for_process_name(
        self, process_name, new_control_object
    ):
        self.mongo_data.add_data(process_name, new_control_object.as_dict(), allow_overwrite=True)

    def _add_control_for_process_name(self, process_name, new_control_object):
        self.mongo_data.add_data(process_name, new_control_object.as_dict(), allow_overwrite=False)