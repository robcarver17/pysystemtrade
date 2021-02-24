from sysdata.data_blob import dataBlob
from syscore.objects import arg_not_supplied

class productionDataLayerGeneric(object):
    def __init__(self, data: dataBlob = arg_not_supplied):
        if data is arg_not_supplied:
            data = dataBlob()

        data = self._add_required_classes_to_data(data)
        self._data = data


    @property
    def data(self) -> dataBlob:
        return self._data

    @property
    def log(self):
        return self.data.log

    def _add_required_classes_to_data(self, data) -> dataBlob:

        return data