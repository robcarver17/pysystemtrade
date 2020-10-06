import os
import sys
from syscore.objects import missing_data
from sysdata.private_config import get_private_config_key_value

echo_extension = ".txt"


class redirectOutput(object):
    def __init__(self, process_name):
        self._original_err = sys.stderr
        self._original_out = sys.stdout

        file_name = get_echo_file_name(process_name)
        if file_name is missing_data:
            print(
                "Not redirecting output as variable 'echo_directory' not set in private_config.yaml"
            )
            self.file_obj = missing_data
            self._stderr = self._original_err
            self._stdout = self._original_out
        else:
            print("Redirecting output to %s" % file_name)
            self.file_obj = open(file_name, "w")
            self._stdout = self.file_obj
            self._stderr = self.file_obj

    def __enter__(self):
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def __exit__(self, type, value, traceback):
        if self.file_obj is missing_data:
            pass
        else:
            self._stdout.flush()
            self._stderr.flush()
            self.file_obj.close()
            sys.stdout = self._original_out
            sys.stderr = self._original_err


def get_echo_file_name(process_name):
    file_name = "%s%s" % (process_name, echo_extension)
    echo_dir = get_echo_file_directory()
    if echo_dir is missing_data:
        return missing_data
    full_file_name = os.path.join(echo_dir, file_name)

    return full_file_name


def get_echo_file_directory():
    ans = get_private_config_key_value("echo_directory")
    if ans is missing_data:
        return missing_data

    return ans
