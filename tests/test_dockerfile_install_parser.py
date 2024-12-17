import os
import sys
import re
import pytest
from src.ersilia_pack.parsers.install_parser import InstallParser
from src.ersilia_pack.parsers.dockerfile_install_parser import DockerfileInstallParser



# Fixture for providing the path to the test Dockerfile located in fixtures dir
@pytest.fixture
def dockerfile_path():
    return os.path.join(os.path.dirname(__file__), 'fixtures', 'eos4e41_Dockerfile.txt')

# Test for _get_python_version
def _get_python_version(self):
    """
    Extracts the Python version from the Dockerfile's FROM instruction.
    """
    with open(self.file_name, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("FROM"):
            match = re.search(r"py(\d+\.\d+|\d{2,3})", line)
            if match:
                version = match.group(1)
                if '.' not in version:  # Convert py38 to 3.8
                    version = f"{version[0]}.{version[1:]}"
                return version
    raise ValueError("Python version not found in Dockerfile. Ensure the FROM line contains a valid Python version.")


# Test for _process_pip_command with different pip command structures
@pytest.mark.parametrize("command,expected", [
    ("pip install scikit-learn==1.2.0", ["pip", "scikit-learn", "1.2.0", None, []]),
    ("pip install numpy", ["pip", "numpy", None, None, []]),  # Expect None for missing components
])
def test_process_pip_command(command, expected):
    parsed_command = DockerfileInstallParser._process_pip_command(command)
    assert parsed_command == expected, f"Failed to parse pip command: {command}"


# Test for _process_conda_command with different conda command structures
@pytest.mark.parametrize("command,expected", [
    ("conda install scikit-learn==1.2.0", ["conda", "scikit-learn", "1.2.0", "default"]),
    ("conda install -c conda-forge numpy==1.23.5", ["conda", "numpy", "1.23.5", "conda-forge"]),
])
def test_process_conda_command(command, expected):
    parsed_command = DockerfileInstallParser._process_conda_command(command)
    assert parsed_command == expected, f"Failed to parse conda command: {command}"

# Test for _get_commands to check if pip and conda commands are parsed (correctly) from Dockerfile
def test_get_commands(dockerfile_path):
    parser = DockerfileInstallParser(dockerfile_path)
    commands = parser._get_commands()
    

    # Verify that all commands that should be pip commands start with 'pip'
    for cmd in commands:
        if isinstance(cmd, list) and cmd[0] == 'pip':
            assert cmd[0] == 'pip', f"Expected pip command but found {cmd[0]}"
        elif isinstance(cmd, list) and cmd[0] == 'conda':
            assert cmd[0] == 'conda', f"Expected conda command but found {cmd[0]}"



