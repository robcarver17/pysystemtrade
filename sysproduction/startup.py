## run on startup

from sysproduction.data.controls import dataBrokerClientIDs
from sysproduction.data.control_process import dataControlProcess


def startup():
    data_controls = dataControlProcess()
    data_controls.finish_all_processes()

    data_clientids = dataBrokerClientIDs()
    data_clientids.clear_all_clientids()
