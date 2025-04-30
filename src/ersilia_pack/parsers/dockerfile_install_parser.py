import os
import re

from .install_parser import InstallParser

FILE_TYPE = "Dockerfile"


class DockerfileInstallParser(InstallParser):
  def __init__(self, file_dir, conda_env_name=None):
    file_name = os.path.join(file_dir, FILE_TYPE)
    super().__init__(file_name, conda_env_name)

  def _get_python_version(self):
    with open(self.file_name) as f:
      for line in f:
        if line.startswith("FROM"):
          match = re.search(r"py(\d+\.\d+|\d{2,3})", line)
          if match:
            v = match.group(1)
            if "." not in v:
              v = f"{v[0]}.{v[1:]}"
            return v
    raise ValueError("Python version not found")

  @staticmethod
  def _tokenize(command):
    return command.split()

  @staticmethod
  def _process_pip_command(command):
    parts = DockerfileInstallParser._tokenize(command)
    if len(parts) < 3 or parts[0] != "pip" or parts[1] != "install":
      raise ValueError("Invalid pip install command")
    pkg_spec = parts[2]
    if pkg_spec.startswith("git+"):
      return ["pip", pkg_spec]
    if "==" in pkg_spec:
      pkg, ver = pkg_spec.split("==", 1)
    else:
      raise ValueError("pip install must specify version or git URL")
    flags = parts[3:]
    return ["pip", pkg, ver] + flags

  @staticmethod
  def _process_conda_command(command):
    parts = command.split()
    if len(parts) < 3 or parts[0] != "conda" or parts[1] != "install":
      raise ValueError("Invalid conda install command")
    return parts

  def _get_commands(self):
    cmds = []
    with open(self.file_name) as f:
      for line in f:
        if line.strip().startswith("RUN"):
          cmd = line.strip()[3:].strip()
          if cmd.startswith("pip"):
            cmds.append(self._process_pip_command(cmd))
          elif cmd.startswith("conda"):
            cmds.append(self._process_conda_command(cmd))
          else:
            cmds.append(cmd)
    return cmds
