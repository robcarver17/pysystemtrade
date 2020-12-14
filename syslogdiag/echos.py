
from syscore.objects import missing_data
from sysdata.private_config import get_private_config_key_value

echo_extension = ".txt"

def get_echo_file_directory():
    ans = get_private_config_key_value("echo_directory")
    if ans is missing_data:
        return missing_data

    return ans
