import pytest
import os
from ersilia_pack.linter import SimpleModelLinter

MODEL_PATH = "Models/eos30d7"

class TestSimpleModelLinter:
    @pytest.fixture
    def linter(self):
        return SimpleModelLinter(repo_path=MODEL_PATH)
    
    def test_model_id_validation(self, linter):
        """Test if model ID starts with 'eos' and is 7 characters long"""
        linter._check_model_id()
        assert linter.model_id.startswith("eos")
        assert len(linter.model_id) == 7

    def test_metadata_existence(self, linter):
        """Test if either metadata.yml or metadata.json exists"""
        linter._check_metadata()
        metadata_exists = (
            os.path.exists(os.path.join(MODEL_PATH, "metadata.yml")) or
            os.path.exists(os.path.join(MODEL_PATH, "metadata.json"))
        )
        assert metadata_exists

    def test_install_file_existence(self, linter):
        """Test if either install.yml or Dockerfile exists"""
        linter._check_installs()
        install_exists = (
            os.path.exists(os.path.join(MODEL_PATH, "install.yml")) or
            os.path.exists(os.path.join(MODEL_PATH, "Dockerfile"))
        )
        assert install_exists

    def test_license_existence(self, linter):
        """Test if LICENSE file exists"""
        linter._check_license()
        assert os.path.exists(os.path.join(MODEL_PATH, "LICENSE"))

    def test_readme_existence(self, linter):
        """Test if README.md exists"""
        linter._check_readme()
        assert os.path.exists(os.path.join(MODEL_PATH, "README.md"))

    def test_model_folder_existence(self, linter):
        """Test if model/framework directory exists"""
        linter._check_model_folder()
        assert os.path.exists(os.path.join(MODEL_PATH, "model", "framework"))

    def test_api_existence(self, linter):
        """Test if there are any .sh files (APIs)"""
        linter._check_apis()
        api_names = linter.get_api_names()
        assert len(api_names) > 0

    def test_examples_existence(self, linter):
        """Test if example input/output files exist for each API"""
        api_names = linter.get_api_names()
        examples_path = os.path.join(MODEL_PATH, "model", "framework", "examples")
        
        for api_name in api_names:
            input_file = os.path.join(examples_path, f"{api_name}_input.csv")
            output_file = os.path.join(examples_path, f"{api_name}_output.csv")
            assert os.path.exists(input_file), f"Missing input example for {api_name}"
            assert os.path.exists(output_file), f"Missing output example for {api_name}"

    def test_complete_validation(self, linter):
        """Test complete validation process"""
        try:
            linter.check()
        except Exception as e:
            pytest.fail(f"Validation failed: {str(e)}")

    @pytest.mark.parametrize("file_path", [
        os.path.join(MODEL_PATH, "metadata.yml"),
        os.path.join(MODEL_PATH, "metadata.json"),
        os.path.join(MODEL_PATH, "install.yml"),
        os.path.join(MODEL_PATH, "Dockerfile"),
        os.path.join(MODEL_PATH, "LICENSE"),
        os.path.join(MODEL_PATH, "README.md"),
        os.path.join(MODEL_PATH, "model", "framework")
    ])
    def test_file_permissions(self, file_path):
        """Test if files are readable"""
        if os.path.exists(file_path):
            assert os.access(file_path, os.R_OK), f"File {file_path} is not readable"

    def test_get_api_names(self, linter):
        """Test if get_api_names returns a list of API names"""
        api_names = linter.get_api_names()
        assert isinstance(api_names, list)
        for api_name in api_names:
            assert isinstance(api_name, str)
            assert api_name.strip() != ""
            # Check if corresponding .sh file exists
            assert os.path.exists(os.path.join(MODEL_PATH, "model", "framework", f"{api_name}.sh"))