## runs on startup

from sysproduction.data.controls import dataControlProcess

def startup():
    data_controls = dataControlProcess()
    data_controls.finish_all_processes()

