from unittest.mock import patch
import re

import pytest

from src.ersilia_pack.parsers import YAMLInstallParser


def _normalize_python_in_script(script: str) -> str:
  """
  Make tests portable across environments by normalizing any absolute python
  interpreter path (e.g. /home/.../bin/python) to just 'python'.
  """
  return re.sub(
    r"^\S*python\s+-m\s+pip",
    "python -m pip",
    script,
    flags=re.MULTILINE,
  )


class TestYamlInstallParser:
  @patch(
    "src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE",
    "simple_install.yml",
  )
  def test_simple_install_yaml(self):
    parser = YAMLInstallParser(file_dir="tests/data")
    assert parser._get_python_version() == "3.10"

    commands = parser._get_commands()
    assert commands == [
      ["pip", "pandas", "2.1.4"],
      ["pip", "joblib", "1.3.2"],
    ]
    assert parser._has_conda(commands) is False

    install_script = _normalize_python_in_script(
      parser._convert_commands_to_bash_script()
    )

    with open("tests/data/simple_install.sh", "r") as file:
      expected_script = file.read()

    assert install_script == expected_script

  @patch(
    "src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE",
    "complex_install.yml",
  )
  def test_complex_install_yaml(self):
    parser = YAMLInstallParser(file_dir="tests/data")
    assert parser._get_python_version() == "3.10"

    commands = parser._get_commands()
    assert commands == [
      ["pip", "pandas", "2.1.4"],
      [
        "pip",
        "torch",
        "2.4.1",
        "--index-url",
        "https://download.pytorch.org/whl/cpu",
      ],
      ["pip", "git+https://github.com/example.git"],
      ["pip", "molfeat[transformer]", "0.10.0"],
    ]

    assert parser._has_conda(commands) is False

    install_script = _normalize_python_in_script(
      parser._convert_commands_to_bash_script()
    )

    with open("tests/data/complex_install.sh", "r") as file:
      expected_script = file.read()

    assert install_script == expected_script

  @patch(
    "src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE",
    "invalid_install.yml",
  )
  def test_invalid_install_yaml(self):
    parser = YAMLInstallParser(file_dir="tests/data")
    with pytest.raises(ValueError):
      parser._convert_commands_to_bash_script()

  @patch(
    "src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE",
    "gpu_install.yml",
  )
  def test_gpu_install_yaml(self):
    cpu = YAMLInstallParser(file_dir="tests/data")
    gpu = YAMLInstallParser(file_dir="tests/data", device="gpu")
    assert cpu.has_gpu() and gpu.has_gpu()
    assert cpu._get_python_version() == gpu._get_python_version() == "3.11"
    assert cpu._get_commands()[0][-1] == "https://download.pytorch.org/whl/cpu"
    assert gpu._get_commands()[0][-1] == "https://download.pytorch.org/whl/cu126"

    install_script = _normalize_python_in_script(
      gpu._convert_commands_to_bash_script()
    )
    assert install_script.splitlines() == [
      "python -m pip install torch==2.10.0 --index-url "
      "https://download.pytorch.org/whl/cu126",
      "python -m pip install pandas==2.1.4",
    ]

  @patch(
    "src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE",
    "simple_install.yml",
  )
  def test_gpu_missing_section(self):
    assert not YAMLInstallParser(file_dir="tests/data").has_gpu()
    with pytest.raises(ValueError, match="'gpu' section"):
      YAMLInstallParser(file_dir="tests/data", device="gpu")

  @patch(
    "src.ersilia_pack.parsers.yaml_install_parser.FILE_TYPE",
    "simple_install.yml",
  )
  def test_invalid_device(self):
    with pytest.raises(ValueError):
      YAMLInstallParser(file_dir="tests/data", device="tpu")
