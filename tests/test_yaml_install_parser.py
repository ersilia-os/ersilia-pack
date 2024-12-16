import pytest
from unittest.mock import patch, mock_open
import yaml
from src.ersilia_pack.parsers import YAMLInstallParser


# Case 1: Test method for the python version
@patch("builtins.open", new_callable=mock_open, read_data='python: "3.9"')
@patch("yaml.safe_load", return_value={"python": "3.9", "commands": ["cmd1", "cmd2"]})
def test_get_python_version(mock_yaml_safe_load, mock_file):
    parser = YAMLInstallParser(file_dir="/workspaces/ersilia-pack/src/ersilia_pack/parsers.py")
    assert parser._get_python_version() == "3.9"


# Case 2: Test method for the python version raising an error
@patch("builtins.open", new_callable=mock_open, read_data='python: "3.9"')
@patch("yaml.safe_load", return_value={"python": 3.9, "commands": ["cmd1", "cmd2"]})
def test_get_python_version_raises_error(mock_yaml_safe_load, mock_file):
    with pytest.raises (ValueError, match="Python version must be a string"):
        YAMLInstallParser(file_dir="/workspaces/ersilia-pack/src/ersilia_pack/parsers.py")       

    
# Case 3: Test method for the commands    
@patch("builtins.open", new_callable=mock_open, read_data='python: "3.9"')
@patch("yaml.safe_load", return_value={"python": "3.9", "commands": ["cmd1", "cmd2"]})
def test_get_commands(mock_yaml_safe_load, mock_file):
    parser = YAMLInstallParser(file_dir="/workspaces/ersilia-pack/src/ersilia_pack/parsers.py")
    assert parser._get_commands() == ["cmd1", "cmd2"]
    

# Case 4:  Tests valid pip commands.
@patch("builtins.open", new_callable=mock_open, read_data=""" 
python: "3.9" 
commands:
  - ['pip', 'SomeProject', '1.3']
  - ['pip', 'git', 'https://github.com/bp-kelley/descriptastorus.git', 'd552f934757378a61dd1799cdb589a864032cd1b']
  - ['pip', 'torchvision', '0.17.1', '--index-url', 'https://download.pytorch.org/whl/cpu']
""")
@patch("yaml.safe_load", return_value={
    "python": "3.9",
    "commands": [
        ['pip', 'SomeProject', '1.3'],
        ['pip', 'git', 'https://github.com/bp-kelley/descriptastorus.git', 'd552f934757378a61dd1799cdb589a864032cd1b'],
        ['pip', 'torchvision', '0.17.1', '--index-url', 'https://download.pytorch.org/whl/cpu']
    ]
})
def test_get_commands_with_pip_dependencies(mock_yaml_safe_load, mock_file):
    parser = YAMLInstallParser(file_dir="/workspaces/ersilia-pack/src/ersilia_pack/parsers.py")
    commands = parser._get_commands()
    assert commands == [
        ['pip', 'SomeProject', '1.3'],
        ['pip', 'git', 'https://github.com/bp-kelley/descriptastorus.git', 'd552f934757378a61dd1799cdb589a864032cd1b'],
        ['pip', 'torchvision', '0.17.1', '--index-url', 'https://download.pytorch.org/whl/cpu']
    ]

# Case 5: Test Invalid pip commands
@patch("builtins.open", new_callable=mock_open, read_data="""
python: "3.9"
commands:
  - ['pip', 'SomeProject']  
  - ['pip', 'git', 'https://github.com/bp-kelley/descriptastorus.git']
  - ['pip', 'torchvision']  
""")
@patch("yaml.safe_load", return_value={
    "python": "3.9",
    "commands": [
        ['pip', 'SomeProject'], 
        ['pip', 'git', 'https://github.com/bp-kelley/descriptastorus.git'], 
        ['pip', 'torchvision']  
    ]
})
def test_get_commands_with_invalid_pip_dependencies(mock_yaml_safe_load, mock_file):
    parser = YAMLInstallParser(file_dir="/workspaces/ersilia-pack/src/ersilia_pack/parsers.py")
    with pytest.raises(ValueError, match="Invalid pip command format"):
        parser._get_commands()

