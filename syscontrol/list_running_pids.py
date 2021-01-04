import psutil


def list_of_all_running_pids():
    psid_list=[]
    for proc in psutil.process_iter():
        try:
            processID = proc.pid
            psid_list.append(processID)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return psid_list


if __name__ == "__main__":
    ## useful if getting pid list from running machine
    pid_list = list_of_all_running_pids()
    for pid in pid_list:
        print(pid)