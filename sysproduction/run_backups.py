from sysproduction.run_process import processToRun
from sysproduction.backup_arctic_to_csv import backupArcticToCsv
from sysproduction.backup_files import backupFiles
from sysproduction.data.get_data import dataBlob


def run_backups():
    process_name = "run_backups"
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = get_list_of_timer_functions_for_backup()
    backup_process = processToRun(
        process_name, data, list_of_timer_names_and_functions)
    backup_process.main_loop()


def get_list_of_timer_functions_for_backup():
    data_arctic_backups = dataBlob(log_name="backup_arctic_to_csv")
    data_backup_files = dataBlob(log_name="backup_files")

    arctic_backup_object = backupArcticToCsv(data_arctic_backups)
    files_backup_object = backupFiles(data_backup_files)

    list_of_timer_names_and_functions = [
        ("backup_arctic_to_csv", arctic_backup_object),
        ("backup_files", files_backup_object),
    ]

    return list_of_timer_names_and_functions
