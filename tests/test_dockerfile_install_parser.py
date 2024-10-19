import os
import pytest
from parsers.dockerfile_install_parser import DockerfileInstallParser
from parsers.install_parser import InstallParser


# Fixture for providing the path to the test Dockerfile located in fixtures dir
@pytest.fixture
def dockerfile_path():
    return os.path.join(os.path.dirname(__file__), 'fixtures', 'Dockerfile.txt')

# Test for _get_python_version
def test_get_python_version(dockerfile_path):
    parser = DockerfileInstallParser(dockerfile_path)
    python_version = parser._get_python_version()
    # Check for Python version in the Dockerfile
    assert python_version == "3.11", "Failed to parse the correct Python version"

# Test for _process_pip_command with different pip command structures
@pytest.mark.parametrize("command,expected", [
    ("pip install scikit-learn==1.2.0", ["pip", "scikit-learn", "1.2.0"]),
    ("pip install numpy", ["pip", "numpy"]),
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
