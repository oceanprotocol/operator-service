import configparser
import os

import pytest

from operator_service.config import Config


@pytest.mark.unit
def test_config_filename_given_file_doesnt_exist(monkeypatch):
    """Test creating a Config object.
    Setup: filename given, file doesn't exist
    Expect: complain
    """
    config_file_name = "i_dont_exist.ini"
    monkeypatch.setenv("CONFIG_FILE", config_file_name)
    assert not os.path.exists(config_file_name)

    with pytest.raises(AssertionError) as err:
        Config()
    assert err.value.args[0].startswith("config file does not exist in")


@pytest.mark.unit
def test_config_filename_given_file_exists_malformed_content(monkeypatch, tmp_path):
    """Test creating a Config object.
    Setup: filename given, file exists, malformed content
    Expect: complain
    """
    config_file_name = _create_malformed_conffile(tmp_path)

    monkeypatch.setenv("CONFIG_FILE", config_file_name)
    with pytest.raises(configparser.MissingSectionHeaderError) as err:
        Config()

    assert err.value.args[2] == "Malformed content inside config file"


def _create_malformed_conffile(tmp_path):
    """Helper function to some tests above. In: pytest tmp_pth. Out: str"""
    d = tmp_path / "subdir"
    d.mkdir()
    config_file = d / "test_config_bad.ini"
    config_file.write_text("Malformed content inside config file")
    config_file_name = str(config_file)
    return config_file_name
