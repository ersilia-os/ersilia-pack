import os
import re

from .install_parser import InstallParser

FILE_TYPE = 'Dockerfile'

class DockerfileInstallParser(InstallParser):
    def __init__(self, file_dir, conda_env_name=None):
        file_name = os.path.join(file_dir, FILE_TYPE)
        super().__init__(file_name, conda_env_name)

    def _get_python_version(self):
        with open(self.file_name) as f:
            for line in f:
                if line.startswith('FROM'):
                    m = re.search(r'py(\d+)(?:\.(\d+))?', line)
                    if m:
                        major = m.group(1)
                        minor = m.group(2) or major[1:]
                        return f"{major}.{minor}"
        raise ValueError('Python version not found')

    @staticmethod
    def _process_pip_command(command):
        parts = command.split()
        if parts[:2] != ['pip', 'install']:
            raise ValueError('Expected pip install')
        pkg_spec = parts[2]
        match = re.match(r'([^=\[]+)(\[[^\]]+\])?([=><!~]+.*)?', pkg_spec)
        if not match:
            raise ValueError(f'Invalid package spec: {pkg_spec}')
        pkg, extras, ver = match.group(1), match.group(2) or '', match.group(3) or ''
        cmd = ['pip', pkg + extras]
        if ver:
            if re.match(r'^\d', ver):
                ver = '==' + ver
            cmd.append(ver)
        cmd.extend(parts[3:])
        return cmd

    @staticmethod
    def _process_conda_command(command):
        parts = command.split()
        if parts[:2] != ['conda', 'install']:
            raise ValueError('Expected conda install')
        channels = []
        pkg_spec = None
        for token in parts[2:]:
            if token == '-c':
                continue
            if token.startswith('-c'):
                c = token[2:]
                channels.append(c)
            elif pkg_spec is None:
                pkg_spec = token
            else:
                channels.append(token)
        if not pkg_spec:
            raise ValueError('No package specified')
        pkg, ver = re.split(r'=+|>=|<=|>|<', pkg_spec, maxsplit=1)[:2] if '=' in pkg_spec else (pkg_spec, '')
        cmd = ['conda', pkg]
        if ver:
            cmd.append(ver)
        if not channels:
            channels = ['default']
        cmd.extend(channels)
        return cmd

    def _get_commands(self):
        commands = []
        with open(self.file_name) as f:
            for line in f:
                if line.strip().startswith('RUN'):
                    cmd = line.strip()[len('RUN'):].strip()
                    if cmd.startswith('pip'):
                        try:
                            commands.append(self._process_pip_command(cmd))
                        except ValueError as e:
                            print(f"Skipping pip: {e}")
                    elif cmd.startswith('conda'):
                        try:
                            commands.append(self._process_conda_command(cmd))
                        except ValueError as e:
                            print(f"Skipping conda: {e}")
                    else:
                        commands.append(cmd)
        return commands
