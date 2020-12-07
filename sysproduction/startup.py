## run on startup

from sysproduction.data.controls import dataBrokerClientIDs
from syscontrol.data_interface import dataControlProcess


def startup():
    data_controls = dataControlProcess()
    data_controls.finish_all_processes()

    data_clientids = dataBrokerClientIDs()
    data_clientids.clear_all_clientids()


