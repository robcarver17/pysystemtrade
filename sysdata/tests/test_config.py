from sysdata.config.configdata import default_config
from sysdata.config.control_config import get_control_config
from sysdata.config.private_directory import PRIVATE_CONFIG_DIR_ENV_VAR
import os


class TestConfig:

    def test_default(self):
        config = default_config()
        assert config.get_element_or_missing_data("ib_idoffset") == 100

    def test_custom_dir(self, monkeypatch):
        envs = {
            PRIVATE_CONFIG_DIR_ENV_VAR: 'sysdata.tests.custom_private_config'
        }
        monkeypatch.setattr(os, 'environ', envs)

        config = default_config()
        assert config.get_element_or_missing_data("ib_idoffset") == 1000

    def test_bad_custom_dir(self, monkeypatch):
        envs = {
            PRIVATE_CONFIG_DIR_ENV_VAR: 'sysdata.tests'
        }
        monkeypatch.setattr(os, 'environ', envs)

        config = default_config()
        assert config.get_element_or_missing_data("ib_idoffset") == 100

    def test_default_control(self):
        config = get_control_config()
        assert config.as_dict()["process_configuration_start_time"]["run_stack_handler"] == '00:01'

    def test_control_custom_dir(self, monkeypatch):
        envs = {
            PRIVATE_CONFIG_DIR_ENV_VAR: 'sysdata.tests.custom_private_config'
        }
        monkeypatch.setattr(os, 'environ', envs)

        config = get_control_config()
        assert config.as_dict()["process_configuration_start_time"]["run_stack_handler"] == '01:00'

    def test_control_bad_custom_dir(self, monkeypatch):
        envs = {
            PRIVATE_CONFIG_DIR_ENV_VAR: 'sysdata.tests'
        }
        monkeypatch.setattr(os, 'environ', envs)

        config = get_control_config()
        assert config.as_dict()["process_configuration_start_time"]["run_stack_handler"] == '00:01'
