import os
import re
import textwrap
from ..utils import eval_conda_prefix


class InstallParser:
  def __init__(self, file_name, conda_env_name=None):
    self.conda_env_name = conda_env_name
    self.file_name = file_name
    self.python_version = self._get_python_version()

  def _get_python_version(self):
    raise NotImplementedError("Implement this in subclass")

  def _get_commands(self):
    raise NotImplementedError("Implement this in subclass")

  def get_python_exe(self):
    conda_prefix = eval_conda_prefix()
    if not conda_prefix:
      return "python"
    if self.conda_env_name is None:
      return f"{conda_prefix}/bin/python"
    return f"{conda_prefix}/envs/{self.conda_env_name}/bin/python"

  @staticmethod
  def _has_conda(commands):
    return any(isinstance(cmd, list) and cmd[0] == "conda" for cmd in commands)

  def _is_valid_url(self, url):
    pattern = re.compile(r"^(?:git\+https://|git\+ssh://|https://).*")
    return bool(pattern.match(url))

  def _convert_pip_entry_to_bash(self, command):
    cmd = ["pip", "install"]
    pkg = command[1]
    if len(command) >= 3 and re.match(r"^[~=!><]=?\d+", command[2]):
      spec = pkg + command[2]
      cmd.append(spec)
      extras = command[3:]
    elif len(command) >= 3 and re.match(r"\d+(?:\.\d+)*", command[2]):
      spec = pkg + "==" + command[2]
      cmd.append(spec)
      extras = command[3:]
    else:
      cmd.append(pkg)
      extras = command[2:]
    cmd.extend(extras)
    return " ".join(cmd)

  def _convert_conda_entry_to_bash(self, command):
    base = ["conda", "install", "-y"]
    channels = [c for c in command[3:] if c]
    for chan in channels:
      base.extend(["-c", chan])
    pkg = command[1]
    if len(command) >= 3 and command[2] != "default":
      base.append(f"{pkg}={command[2]}")
    else:
      base.append(pkg)
    return " ".join(base)

  def _convert_commands_to_bash_script(self):
    lines = []
    commands = self._get_commands()
    has_conda = self._has_conda(commands)
    conda_prefix = eval_conda_prefix() or "$CONDA_PREFIX"
    python_exe = self.get_python_exe()
    for command in commands:
      if isinstance(command, list):
        if command[0] == "pip":
          lines.append(f"{python_exe} -m {self._convert_pip_entry_to_bash(command)}")
        elif command[0] == "conda":
          lines.append(self._convert_conda_entry_to_bash(command))
        else:
          raise ValueError(f"Unknown command type: {command[0]}")
      else:
        lines.append(command)

    header = []
    if has_conda:
      env = self.conda_env_name or "base"
      header = [
        f"source {conda_prefix}/etc/profile.d/conda.sh",
        f"conda activate {env}",
      ]
    script = header + lines
    return textwrap.dedent("\n".join(script))

  def write_bash_script(self, file_name=None):
    file_name = file_name or os.path.splitext(self.file_name)[0] + ".sh"
    with open(file_name, "w") as f:
      f.write(self._convert_commands_to_bash_script())

  def check_file_exists(self):
    return os.path.exists(self.file_name)
