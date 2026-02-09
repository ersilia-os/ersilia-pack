import os
import re
import shlex
import warnings

from ..utils import get_conda_source, get_native, conda_python_executable


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
    return conda_python_executable(self.conda_env_name)

  @staticmethod
  def _has_conda(commands):
    for cmd in commands:
      if isinstance(cmd, list):
        if cmd and str(cmd[0]).strip().lower() == "conda":
          return True
        s = " ".join(map(str, cmd)).lstrip().lower()
        if s.startswith("conda "):
          return True
      else:
        s = str(cmd).lstrip().lower()
        if s.startswith("conda "):
          return True
    return False

  def _is_valid_url(self, url):
    pattern = re.compile(r"^(git\+https://|git\+ssh://|https://).*")
    return bool(pattern.match(url))

  def _convert_pip_entry_to_bash(self, command):
    if isinstance(command, str):
      s = command.strip()
      parts = shlex.split(s)
      if len(parts) >= 2 and parts[0] in ("pip", "pip3") and parts[1] == "install":
        return s if parts[0] == "pip" else "pip " + " ".join(parts[1:])
      return s

    if len(command) == 2:
      pkg = command[1]
      if pkg.startswith("git+"):
        if not self._is_valid_url(pkg):
          raise ValueError("Invalid Git URL provided")
        return f"pip install {pkg}"
      raise ValueError("pip install entry must include version")

    pkg, ver = command[1], command[2]
    spec = pkg if (ver == "" or "git+" in pkg) else f"{pkg}=={ver}"
    flags = command[2:] if "git+" in pkg else command[3:]
    return f"pip install {spec}" + (" " + " ".join(flags) if flags else "")

  def _convert_conda_entry_to_bash(self, command):
    if isinstance(command, str):
      return command.strip()

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
    s = str(raw).strip()
    if not s:
      return ""
    head = s.split()[0]
    native = get_native()
    if head.lower() in native:
      return s
    return s

  @staticmethod
  def _head_of_string(cmd_str):
    try:
      parts = shlex.split(cmd_str.strip())
    except ValueError:
      parts = cmd_str.strip().split()
    return parts[0].lower() if parts else ""

  def _convert_commands_to_bash_script(self):
    commands = self._get_commands()
    has_conda = self._has_conda(commands)
    env = self.conda_env_name or "base"
    python_exe = self.get_python_exe()
    lines = get_conda_source(env) if has_conda else []

    def add_pip(x):
      lines.append(f"{python_exe} -m {self._convert_pip_entry_to_bash(x)}")

    for cmd in commands:
      if isinstance(cmd, list):
        if not cmd:
          continue
        head = str(cmd[0]).lower()
        if head == "pip":
          add_pip(cmd)
        elif head == "conda":
          lines.append(self._convert_conda_entry_to_bash(cmd))
        else:
          lines.append(self._prefix_unknown(" ".join(map(str, cmd))))
        continue

      s = str(cmd).strip()
      if not s:
        continue
      head = self._head_of_string(s)
      if head in ("pip", "pip3"):
        add_pip(s)
      elif head == "conda":
        lines.append(self._convert_conda_entry_to_bash(s))
      else:
        lines.append(self._prefix_unknown(s))

    return os.linesep.join(lines)

  def write_bash_script(self, file_name=None):
    if file_name is None:
      file_name = os.path.splitext(self.file_name)[0] + ".sh"
    data = self._convert_commands_to_bash_script()
    print(data)
    with open(file_name, "w") as f:
      f.write(data)

  def check_file_exists(self):
    return os.path.exists(self.file_name)
