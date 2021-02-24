from sysdata.data_blob import dataBlob
from syscore.objects import arg_not_supplied

class dataGeneric(object):
    def __init__(self, data: dataBlob = arg_not_supplied):
        if data is arg_not_supplied:
            data = dataBlob()

        data = self._add_required_classes_to_data(data)
        self._data = data


    @property
    def data(self):
        return self._data

    def _add_required_classes_to_data(self, data) -> dataBlob:

        return data