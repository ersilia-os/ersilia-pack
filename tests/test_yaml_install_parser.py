import unittest
from unittest.mock import patch, mock_open
import yaml
from src.ersilia_pack.parsers import YAMLInstallParser  # Correct import

class TestYAMLInstallParser(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    def test_get_python_version(self, mock_yaml_safe_load, mock_file):
        mock_yaml_safe_load.return_value = {"python": "3.9", "commands": ["cmd1", "cmd2"]}
        parser = YAMLInstallParser(file_dir="/some/directory")
        python_version = parser._get_python_version()
        self.assertEqual(python_version, "3.9")

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    def test_get_python_version_raises_error(self, mock_yaml_safe_load, mock_file):
        # Mock YAML data with an invalid non-string Python version
        mock_yaml_safe_load.return_value = {"python": 3.9, "commands": ["cmd1", "cmd2"]}
        parser = YAMLInstallParser(file_dir="/some/directory")
        with self.assertRaises(ValueError) as context:
            parser._get_python_version()
        self.assertEqual(str(context.exception), "Python version must be a string")

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    def test_get_commands(self, mock_yaml_safe_load, mock_file):
        mock_yaml_safe_load.return_value = {"python": "3.9", "commands": ["cmd1", "cmd2"]}
        parser = YAMLInstallParser(file_dir="/some/directory")
        commands = parser._get_commands()
        self.assertEqual(commands, ["cmd1", "cmd2"])

if __name__ == "__main__":
    unittest.main()
