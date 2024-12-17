import pytest
from unittest.mock import patch
from src.ersilia_pack.parsers.dockerfile_install_parser import DockerfileInstallParser


class TestDockerfileInstallParser:

    @patch("src.ersilia_pack.parsers.dockerfile_install_parser.FILE_TYPE", "simple_dockerfile.txt")
    def test_simple_dockerfile(self):
        parser = DockerfileInstallParser(file_dir="tests/data")
        assert parser._get_python_version() == "3.11"

        commands = parser._get_commands()
        assert commands == [
            ["pip", "scikit-learn", "1.2.0"],
            ["pip", "rdkit", "2023.9.2"],
        ]
        assert parser._has_conda(commands) == False
        install_script = parser._convert_commands_to_bash_script()
        with open("tests/data/simple_dockerfile.sh", "r") as file:
            expected_script = file.read()
        assert install_script == expected_script

    @patch("src.ersilia_pack.parsers.dockerfile_install_parser.FILE_TYPE", "complex_dockerfile.txt")
    def test_complex_dockerfile(self):
        parser = DockerfileInstallParser(file_dir="tests/data")
        assert parser._get_python_version() == "3.9"

        commands = parser._get_commands()
        assert commands == [
            ["pip", "rdkit", "2024.3.5"],
            ["pip", "git+https://github.com/example.git"],
            ["pip", "torch", "2.4.1", "--index-url", "https://download.pytorch.org/whl/cpu"],
        ]
        assert parser._has_conda(commands) == False
        install_script = parser._convert_commands_to_bash_script()
        with open("tests/data/complex_dockerfile.sh", "r") as file:
            expected_script = file.read()
        assert install_script == expected_script

    @patch("src.ersilia_pack.parsers.dockerfile_install_parser.FILE_TYPE", "invalid_dockerfile.txt")
    def test_invalid_dockerfile(self):
        parser = DockerfileInstallParser(file_dir="tests/data")
        with pytest.raises(ValueError) as e:
            parser._convert_commands_to_bash_script()
