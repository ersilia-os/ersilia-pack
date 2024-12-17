import pytest
import os
from unittest.mock import patch
from src.ersilia_pack.parsers import YAMLInstallParser


class TestYamlInstallParser:

    @patch("src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE", "simple_install.yml")
    def test_simple_install_yaml(self):
        parser = YAMLInstallParser(file_dir="tests/data")
        assert parser._get_python_version() == "3.10"

        commands = parser._get_commands()
        assert commands == [
            ["pip", "pandas", "2.1.4"],
            ["pip", "joblib", "1.3.2"],
        ]
        assert parser._has_conda(commands) == False
        install_script = parser._convert_commands_to_bash_script()
        with open(f"tests/data/simple_install.sh", "r") as file:
            expected_script = file.read()
        assert install_script == expected_script

    @patch("src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE", "complex_install.yml")
    def test_complex_install_yaml(self):
        parser = YAMLInstallParser(file_dir="tests/data")
        assert parser._get_python_version() == "3.10"

        commands = parser._get_commands()
        assert commands == [
            ["pip", "pandas", "2.1.4"],
            ["pip", "torch", "2.4.1", "--index-url", "https://download.pytorch.org/whl/cpu"],
            ["pip", "git+https://github.com/example.git"]
        ]
        assert parser._has_conda(commands) == False
        install_script = parser._convert_commands_to_bash_script()
        with open("tests/data/complex_install.sh", "r") as file:
            expected_script = file.read()
        assert install_script == expected_script


    @patch("src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE", "invalid_install.yml")
    def test_invalid_install_yaml(self):
        with pytest.raises(ValueError):
            parser = YAMLInstallParser(file_dir="tests/data")
            parser._convert_commands_to_bash_script()