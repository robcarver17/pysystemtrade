from syscore.fileutils import get_filename_for_package
from syscore.objects import arg_not_supplied
from sysdata.production.roll_state_storage import rollStateData
from syslogdiag.log import logtoscreen


class csvRollStateData(rollStateData):
    """
    Get data about roll state

    """

    def __init__(self, datapath=arg_not_supplied,
                 log=logtoscreen("csvRollStateData")):

        super().__init__()

        if datapath is arg_not_supplied:
            raise Exception("Datapath needs to be passed")

        self._config_file = get_filename_for_package(
            datapath, "roll_state.csv")
        self.name = "Roll state data from %s" % self._config_file
        self.log = logtoscreen

    def __repr__(self):
        return self.name

    def write_all_instrument_data(self, instrument_data):
        instrument_data.to_csv(self._config_file, index_label="Instrument")
