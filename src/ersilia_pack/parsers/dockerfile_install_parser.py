import os
import re
import shlex

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
  def _is_flag(tok):
    return tok.startswith("-")

  @staticmethod
  def _is_git_spec(tok):
    return tok.startswith("git+")

  @staticmethod
  def _validate_pip_pkg_spec(tok):
    if DockerfileInstallParser._is_git_spec(tok):
      return
    if "==" not in tok:
      raise ValueError(
        "pip install must pin versions (use '=='): got '{0}'".format(tok)
      )
    pkg, ver = tok.split("==", 1)
    if not pkg or not ver:
      raise ValueError("Invalid pip pin: '{0}'".format(tok))

  @staticmethod
  def _validate_conda_pkg_spec(tok):
    if "=" not in tok:
      raise ValueError(
        "conda install must pin versions (use '='): got '{0}'".format(tok)
      )
    pkg, ver = tok.split("=", 1)
    if pkg.endswith("="):
      pkg = pkg[:-1]
      if ver.startswith("="):
        ver = ver[1:]
    if not pkg or not ver:
      raise ValueError("Invalid conda pin: '{0}'".format(tok))
    if not re.match(r"^[A-Za-z0-9._-]+$", pkg):
      raise ValueError("Invalid conda package name: '{0}'".format(pkg))

  @staticmethod
  def _validate_pip_install(parts):
    if len(parts) < 3:
      raise ValueError("pip install must include at least one package spec")
    i = 2
    while i < len(parts):
      tok = parts[i]
      if DockerfileInstallParser._is_flag(tok):
        if tok in (
          "-i",
          "--index-url",
          "--extra-index-url",
          "-f",
          "--find-links",
        ) and i + 1 < len(parts):
          i += 2
        else:
          i += 1
        continue
      DockerfileInstallParser._validate_pip_pkg_spec(tok)
      i += 1

  @staticmethod
  def _validate_conda_install(parts):
    if len(parts) < 3:
      raise ValueError("conda install must include at least one package spec")
    i = 2
    saw_pkg = False
    while i < len(parts):
      tok = parts[i]
      if tok in ("-c", "--channel"):
        if i + 1 >= len(parts):
          raise ValueError("conda install: -c/--channel must have a value")
        i += 2
        continue
      if tok in ("-y", "--yes", "--quiet", "-q", "--freeze-installed"):
        i += 1
        continue
      if DockerfileInstallParser._is_flag(tok):
        i += 1
        continue
      saw_pkg = True
      DockerfileInstallParser._validate_conda_pkg_spec(tok)
      i += 1
    if not saw_pkg:
      raise ValueError("conda install must include at least one pinned package spec")

  @staticmethod
  def _maybe_validate_install_command(cmd):
    parts = shlex.split(cmd)
    if len(parts) >= 2 and parts[0] == "pip" and parts[1] == "install":
      DockerfileInstallParser._validate_pip_install(parts)
      return
    if len(parts) >= 2 and parts[0] == "conda" and parts[1] == "install":
      DockerfileInstallParser._validate_conda_install(parts)
      return

  def _get_commands(self):
    cmds = []
    with open(self.file_name) as f:
      for line in f:
        s = line.strip()
        if not s or s.startswith("#"):
          continue
        if s.startswith("RUN "):
          cmd = s[4:].strip()
          self._maybe_validate_install_command(cmd)
          cmds.append(cmd)
    return cmds
