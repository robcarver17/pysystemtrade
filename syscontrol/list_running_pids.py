import psutil
import subprocess

from syscore.exceptions import missingData
from sysdata.config.production_config import get_production_config

## IF THIS FILE IS MOVED, NEED TO UPDATE THE NEXT LINE
## WARNING ONLY WORKS ON LINUX??
PID_CODE_HOME = "/home/$USER/pysystemtrade/syscontrol/list_running_pids.py"
DECODE_STR = "utf-8"


def describe_trading_server_login_data() -> str:
    try:
        login_data = get_trading_server_login_data()
    except missingData:
        return "localhost"
    trading_server_username, trading_server_ip, trading_server_ssh_port = login_data
    host_description = "%s@%s port %s" % (
        str(trading_server_username),
        str(trading_server_ip),
        str(trading_server_ssh_port),
    )

    return host_description


def list_of_all_running_pids():
    try:
        trading_server_login_data = get_trading_server_login_data()
    except missingData:
        pid_list = local_list_of_all_running_pids()
    else:
        pid_list = remote_list_of_running_pids(trading_server_login_data)

    return pid_list


def get_trading_server_login_data():
    production_config = get_production_config()
    trading_server_ip = production_config.get_element("trading_server_ip")

    trading_server_username = production_config.trading_server_username
    trading_server_ssh_port = production_config.trading_server_ssh_port

    return trading_server_username, trading_server_ip, trading_server_ssh_port


## ASSUMES WE CAN SSH WITHOUT PASSWORD WILL NEED TO MODIFY IF NOT THE CASE..


def remote_list_of_running_pids(trading_server_login_data):
    (
        trading_server_username,
        trading_server_ip,
        trading_server_ssh_port,
    ) = trading_server_login_data

    raw_text = subprocess.check_output(
        "ssh -p %d %s@%s 'python3 %s'"
        % (
            trading_server_ssh_port,
            trading_server_username,
            trading_server_ip,
            PID_CODE_HOME,
        ),
        stdin=None,
        stderr=subprocess.STDOUT,
        shell=True,
    )

    pid_list = convert_raw_binary_text_output_into_list_of_pid_ints(raw_text)

    return pid_list


def convert_raw_binary_text_output_into_list_of_pid_ints(raw_text):
    raw_text_lines = raw_text.splitlines()
    result_lines_as_txt = [line.decode(DECODE_STR) for line in raw_text_lines]
    pid_list = [int(result_line) for result_line in result_lines_as_txt]

    return pid_list


def local_list_of_all_running_pids():
    psid_list = []
    for proc in psutil.process_iter():
        try:
            processID = proc.pid
            psid_list.append(processID)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return psid_list


if __name__ == "__main__":
    ## useful if getting pid list from running machine
    pid_list = local_list_of_all_running_pids()
    for pid in pid_list:
        print(pid)
