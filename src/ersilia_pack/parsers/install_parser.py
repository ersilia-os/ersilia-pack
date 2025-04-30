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
    for command in commands:
      if isinstance(command, list) and command[0] == "conda":
        return True
    return False

  def _is_valid_url(self, url):
    """
    Validate if the provided URL is a valid Git or HTTP URL.

    Accepts:
    - git+https://github.com/...
    - git+ssh://git@github.com/...
    - https://github.com/...
    - git+https://my.gitlab.com/repo.git
    """
    pattern = re.compile(r"^(git\+https://|git\+ssh://|https://).*")
    return bool(pattern.match(url))

  def _convert_pip_entry_to_bash(self, command):
    num_parts = len(command)
    if num_parts == 2 and command[1].startswith("git+"):
      if not self._is_valid_url(command[1]):
        raise ValueError("Invalid Git URL provided")
      return f"pip install {command[1]}"
    elif num_parts < 3:
      raise ValueError("pip command must have at least 3 arguments")
    else:
      cmd = f"pip install {command[1]}=={command[2]}"
      if num_parts == 3:
        return cmd
      else:
        # This assumes flags are preceded by double hyphen.
        # For example, '--index-url' instead of 'index-url'
        for part in command[3:]:
          cmd += f" {part}"
      return cmd

  def _has_version(self, cmd):
    return any(re.fullmatch(r"\d+(\.\d+)*", item) for item in cmd)

  def _convert_conda_entry_to_bash(self, command):
    assert len(command) <= 4, "conda command must have 4 arguments"
    if "default" in command:
      if self._has_version(command):
        cmd = f"conda install {command[1]}={command[2]}"
      else:
        cmd = f"conda install {command[1]}"
    else:
      if self._has_version(command):
        cmd = f"conda install -c {command[-1]} {command[1]}={command[2]}"

      else:
        cmd = f"conda install -c {command[-1]} {command[1]}"
    return cmd

  def _convert_commands_to_bash_script(self):
    lines = []
    commands = self._get_commands()
    has_conda = self._has_conda(commands)
    conda_prefix = eval_conda_prefix()
    python_exe = self.get_python_exe()
    for command in commands:
      if isinstance(command, list):
        if command[0] == "pip":
          cmd = f"{python_exe} -m {self._convert_pip_entry_to_bash(command)}"
        elif command[0] == "conda":
          cmd = self._convert_conda_entry_to_bash(command)
          cmd += " -y"
        else:
          raise ValueError("Unknown command type specified as a list")
      else:
        cmd = command
      lines += [cmd]
    txt = ""
    if has_conda:
      if self.conda_env_name is None:
        conda_env_name = "base"
        self.python_exe = "python_exe=$conda_prefix/bin/python"
      else:
        conda_env_name = self.conda_env_name
        self.python_exe = f"python_exe=$conda_prefix/envs/{conda_env_name}/bin/python"
      conda_lines = [
        f"source {conda_prefix}/etc/profile.d/conda.sh",
        f"conda activate {conda_env_name}",
      ]
      lines = [self.python_exe] + conda_lines + lines

      txt = textwrap.dedent(txt) + os.linesep
    txt += os.linesep.join(lines)
    return txt

  def write_bash_script(self, file_name=None):
    if file_name is None:
      file_name = self.file_name.split(".")[0] + ".sh"
    with open(file_name, "w") as file:
      file.write(self._convert_commands_to_bash_script())

  def check_file_exists(self):
    return os.path.exists(self.file_name)
