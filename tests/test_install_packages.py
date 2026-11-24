import pytest

from src.ersilia_pack.packer import FastApiAppPacker


def _packer(sh_file):
  packer = FastApiAppPacker.__new__(FastApiAppPacker)
  packer.sh_file = str(sh_file)
  return packer


def test_a_failed_install_command_stops_the_install(tmp_path):
  # Like a pip-only install.sh: no 'set -e', and the failing command is not the
  # last one, so plain 'bash install.sh' returned 0
  marker = tmp_path / "after_failure"
  sh = tmp_path / "install.sh"
  sh.write_text(f"echo first\nfalse\ntouch {marker}\n")
  with pytest.raises(RuntimeError, match="return code 1"):
    _packer(sh)._install_packages()
  assert not marker.exists()


def test_a_successful_install_passes(tmp_path):
  marker = tmp_path / "done"
  sh = tmp_path / "install.sh"
  sh.write_text(f"echo first\ntouch {marker}\n")
  _packer(sh)._install_packages()
  assert marker.exists()
