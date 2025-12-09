import os
import re
import warnings
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
    pattern = re.compile(r"^(git\+https://|git\+ssh://|https://).*")
    return bool(pattern.match(url))

  def _convert_pip_entry_to_bash(self, command):
    if len(command) == 2:
      pkg = command[1]
      if pkg.startswith("git+"):
        if not self._is_valid_url(pkg):
          raise ValueError("Invalid Git URL provided")
        return f"pip install {pkg}"
      else:
        raise ValueError("pip install entry must include version")
    pkg, ver = command[1], command[2]
    spec = pkg if ver == "" else f"{pkg}=={ver}"
    flags = command[3:]
    return f"pip install {spec}" + (" " + " ".join(flags) if flags else "")

  def _convert_conda_entry_to_bash(self, command):
    if len(command) >= 4 and command[1] != "install":
      _, pkg, ver, *rest = command
      if not re.match(r"^[\w\-.]+(?:={1,2})[\w\-.]+$", f"{pkg}={ver}"):
        raise ValueError("Invalid conda version pin")
      channels = [x for x in rest if x not in ("-y",)]
      flags = [x for x in rest if x == "-y"]
      if not channels:
        warnings.warn(f"No channel specified for conda package '{pkg}'")
        channels = ["default"]
      channel_flags = []
      for ch in channels:
        channel_flags.extend(["-c", ch])
      cmd = ["conda", "install"] + flags + channel_flags + [f"{pkg}={ver}"]
      if "-y" not in flags:
        cmd.append("-y")
      return " ".join(cmd)

    parts = command[1:]
    cmd = ["conda", "install"]
    channels = []
    flags = []
    pkg_spec = None
    i = 0

    while i < len(parts):
      p = parts[i]
      if p in ("-c", "--channel") and i + 1 < len(parts):
        channels += [parts[i], parts[i + 1]]
        i += 2
      elif p == "-y":
        flags.append("-y")
        i += 1
      else:
        pkg_spec = p
        i += 1

    if not pkg_spec:
      raise ValueError("No conda package specified")
    cmd += flags + channels + [pkg_spec]
    if "-y" not in flags:
      cmd.append("-y")
    return " ".join(cmd)

  def _prefix_unknown(self, raw):
    if not raw.strip():
      return ""

    head = raw.split()[0]

    native = {
      "apt",
      "apt-get",
      "apt-cache",
      "apt-key",
      "curl",
      "wget",
      "ls",
      "cd",
      "cat",
      "echo",
      "touch",
      "mkdir",
      "rm",
      "cp",
      "mv",
      "bash",
      "sh",
      "sudo",
      "python",
      "python3",
      "pip",
      "conda",
      "from",
      "workdir",
      "copy",
      "maintainer",
    }

    if head.lower() in native:
      return raw

    conda_prefix = eval_conda_prefix()
    env = self.conda_env_name or "base"
    env_bin = f"{conda_prefix}/envs/{env}/bin" if conda_prefix else ""
    return f"{env_bin}/{raw}" if env_bin else raw

  def _convert_commands_to_bash_script(self):
    commands = self._get_commands()
    has_conda = self._has_conda(commands)
    conda_prefix = eval_conda_prefix() or ""
    python_exe = self.get_python_exe()
    lines = []

    if has_conda:
      env = self.conda_env_name or "base"
      if conda_prefix:
        lines.append(f"source {conda_prefix}/etc/profile.d/conda.sh")
      lines.append(f"conda activate {env}")

    for cmd in commands:
      if isinstance(cmd, list):
        head = cmd[0].lower()

        if head == "pip":
          bash = f"{python_exe} -m {self._convert_pip_entry_to_bash(cmd)}"
        elif head == "conda":
          bash = self._convert_conda_entry_to_bash(cmd)
        else:
          raw = " ".join(cmd)
          bash = self._prefix_unknown(raw)

      else:
        s = str(cmd).lstrip()
        bash = self._prefix_unknown(s)

      lines.append(bash)

    return os.linesep.join(lines)

  def write_bash_script(self, file_name=None):
    if file_name is None:
      file_name = os.path.splitext(self.file_name)[0] + ".sh"
    with open(file_name, "w") as f:
      f.write(self._convert_commands_to_bash_script())

  def check_file_exists(self):
    return os.path.exists(self.file_name)
