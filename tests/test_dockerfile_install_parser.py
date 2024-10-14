
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../parser')))

from dockerfile_install_parser import DockerfileInstallParser
import unittest

class TestDockerfileInstallParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = DockerfileInstallParser(r"C:\Users\HP\Desktop\OutreachyDec2024\Task4\ersilia-pack\dockerfiles")

    def test_get_python_version(self):
        version = self.parser._get_python_version()
        self.assertEqual(version, '3.10-slim')

    def test_process_pip_command(self):
        command = "pip install package_name==1.0.0"
        result = self.parser._process_pip_command(command)
        self.assertEqual(result, ["pip", "package_name", "1.0.0"])

    def test_process_conda_command(self):
        command = "conda install package_name==1.0.0"
        result = self.parser._process_conda_command(command)
        self.assertEqual(result, ["conda", "package_name", "1.0.0", "default"])

if __name__ == '__main__':
    unittest.main()
