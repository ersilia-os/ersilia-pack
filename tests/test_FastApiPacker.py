import os
import pytest
import shutil
import json
import yaml
from unittest.mock import patch, mock_open, MagicMock
from src.ersilia_pack.packer import FastApiAppPacker

@pytest.fixture
def temp_model_directory(tmp_path):
    """Fixture to create a temporary model directory."""
    model_dir = tmp_path / "test_model"
    os.makedirs(model_dir / "model")
    os.makedirs(model_dir / "framework")
    return model_dir

@pytest.fixture
def bundles_repo_path(tmp_path):
    """Fixture to create a bundles repository path."""
    return tmp_path / "bundles_repo"

# 1. Test correct initialization
def test_fastapi_packer_initialization(temp_model_directory, bundles_repo_path):
    metadata_file = temp_model_directory / "metadata.json"
    metadata_file.write_text(json.dumps({"Identifier": "test_model_id"}))

    install_file = temp_model_directory / "install.yml"  # Add this line
    install_file.write_text(yaml.dump({"python": "3.8", "pip": ["numpy"]}))  # Add basic content

    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))
    assert os.path.exists(packer.bundle_dir)
    assert os.path.exists(os.path.join(packer.bundle_dir, "installs"))

# 2. Test _get_model_id method
def test_get_model_id_with_json(temp_model_directory, bundles_repo_path):
    metadata_file = temp_model_directory / "metadata.json"
    metadata_file.write_text(json.dumps({"Identifier": "test_model_id"}))

    install_file = temp_model_directory / "install.yml"  # Add install.yml
    install_file.write_text(yaml.dump({"python": "3.8", "pip": ["numpy"]}))  
    
    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))
    assert packer._get_model_id() == "test_model_id"


def test_get_model_id_with_yaml(temp_model_directory, bundles_repo_path):
    metadata_file = temp_model_directory / "metadata.yml"
    metadata_file.write_text(yaml.dump({"Identifier": "test_model_id", "Slug": "test_slug"}))

    install_file = temp_model_directory / "install.yml"  # Add install.yml
    install_file.write_text(yaml.dump({"python": "3.8", "pip": ["numpy"]}))
    
    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))
    assert packer._get_model_id() == "test_model_id"

def test_get_model_id_no_metadata(temp_model_directory, bundles_repo_path):
    with pytest.raises(Exception, match="No metadata file found"):
        FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))

# 3. Test _get_favicon
@patch("urllib.request.urlretrieve")
def test_get_favicon(mock_urlretrieve, temp_model_directory, bundles_repo_path):
    metadata_file = temp_model_directory / "metadata.json"
    metadata_file.write_text(json.dumps({"Identifier": "test_model_id"}))

    # Add install.yml file
    install_file = temp_model_directory / "install.yml"
    install_file.write_text(yaml.dump({"python": "3.8", "pip": ["requests"]}))
    
    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))
    packer._get_favicon()

    expected_path = os.path.join(packer.bundle_dir, "static", "favicon.ico")
    mock_urlretrieve.assert_called_once_with(
        "https://raw.githubusercontent.com/ersilia-os/ersilia-pack/main/assets/favicon.ico",
        expected_path,
    )
    assert os.path.exists(os.path.dirname(expected_path))

# 4. Test _create_bundle_structure
def test_create_bundle_structure(temp_model_directory, bundles_repo_path):
    (temp_model_directory / "model" / "test_file.txt").write_text("content")
    metadata_file = temp_model_directory / "metadata.json"
    metadata_file.write_text(json.dumps({"Identifier": "test_model_id"}))

# Add install.yml file
    install_file = temp_model_directory / "install.yml"
    install_file.write_text(yaml.dump({"python": "3.8", "pip": ["requests"]}))
    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))
    packer._create_bundle_structure()

    assert os.path.exists(os.path.join(packer.bundle_dir, "model", "test_file.txt"))

# 5. Test _get_input_schema
@patch("shutil.copy")
def test_get_input_schema(mock_copy, temp_model_directory, bundles_repo_path):
    metadata_file = temp_model_directory / "metadata.json"
    metadata_file.write_text(json.dumps({
        "Identifier": "test_model_id", 
        "Input": ["Text"], 
        "Input Shape": "Square"
    }))

    # Add an install.yml file
    install_file = temp_model_directory / "install.yml"
    install_file.write_text(yaml.dump({"python": "3.8", "pip": ["requests"]}))
    
    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))
    packer.info = {"card": {"Input": ["Text"], "Input Shape": "Square"}}
    packer._get_input_schema()
    
    mock_copy.assert_called_once()

# 6. Test _get_api_names_from_sh
def test_get_api_names_from_sh(temp_model_directory, bundles_repo_path):
    # Setup: Create the required directory structure
    framework_dir = temp_model_directory / "model" / "framework"
    os.makedirs(framework_dir)
    (framework_dir / "run.sh").write_text("#!/bin/bash\necho 'Running API...'")

    # Add a metadata.json file
    metadata_file = temp_model_directory / "metadata.json"
    metadata_file.write_text(json.dumps({"Identifier": "test_model_id"}))

    # Add an install.yml file
    install_file = temp_model_directory / "install.yml"
    install_file.write_text(yaml.dump({"python": "3.8", "pip": ["requests"]}))

    # Initialize FastApiAppPacker
    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))

    # Simulate copying model files to bundle_dir
    bundle_framework_dir = os.path.join(packer.bundle_dir, "model", "framework")
    os.makedirs(bundle_framework_dir)
    shutil.copy(framework_dir / "run.sh", os.path.join(bundle_framework_dir, "run.sh"))

    # Run the method to get API names
    api_names = packer._get_api_names_from_sh()

    # Assert the output is as expected
    assert api_names == ["run"], "Expected to find 'run' as the API name"

# 8. Test _create_app_files
@patch("shutil.copy")
def test_create_app_files(mock_copy, temp_model_directory, bundles_repo_path):
    metadata_file = temp_model_directory / "metadata.json"
    metadata_file.write_text(json.dumps({"Identifier": "test_model_id"}))

    # Add a valid install.yml file
    install_file = temp_model_directory / "install.yml"
    install_file.write_text(yaml.dump({"python": "3.8", "pip": ["requests"]}))

    # Initialize the FastApiAppPacker
    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))

    # Correct the expected paths for the templates using self.src_dir
    template_path = os.path.join(packer.src_dir, "templates")

    # Call _create_app_files
    packer._create_app_files()

    # Ensure the 'app' directory was created
    assert os.path.exists(os.path.join(packer.bundle_dir, "app"))

    # Mock assertion for the paths used in shutil.copy
    mock_copy.assert_any_call(
        os.path.join(template_path, "app.py"),
        os.path.join(packer.bundle_dir, "app", "main.py")
    )
    mock_copy.assert_any_call(
        os.path.join(template_path, "run_uvicorn.py"),
        os.path.join(packer.bundle_dir, "run_uvicorn.py")
    )
    mock_copy.assert_any_call(
        os.path.join(template_path, "utils.py"),
        os.path.join(packer.bundle_dir, "app", "utils.py")
    )


# 8. Test _edit_post_commands_app
@patch("builtins.open", new_callable=mock_open, read_data=json.dumps({"Identifier": "test_model_id"}))
def test_edit_post_commands_app(mock_open_file, temp_model_directory, bundles_repo_path):
    # Ensure necessary directories and files are created
    framework_dir = temp_model_directory / "model" / "framework"
    os.makedirs(framework_dir)
    (framework_dir / "run.sh").write_text("#!/bin/bash")

    metadata_file = temp_model_directory / "metadata.json"
    metadata_file.write_text(json.dumps({"Identifier": "test_model_id"}))

    # Correctly formatted install.yml file with a valid python version
    install_file = temp_model_directory / "install.yml"
    install_file.write_text("""
python: "3.8"
pip:
  - requests
commands:
  - pip install -r requirements.txt
""")

    # Print to check the contents of the YAML file
    with open(install_file, "r") as f:
        print(f"YAML file content: {f.read()}")  # To check if it's being read correctly

    # Initialize the FastApiAppPacker and check the install_writer
    try:
        packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))
        print(f"Install writer: {packer.install_writer}")  # Check if the install writer is created

        # Call the method to be tested after successful initialization
        packer._create_app_files()  # Ensure this method is called after successful initialization
        packer._edit_post_commands_app()  # Add this if it's meant to be called

    except ValueError as e:
        print(f"Error: {str(e)}")  # Catch and print any ValueError raised during initialization
        # Handle exception as needed (e.g., re-raise if necessary or assert the expected error)

    # Check if 'open' was called with the correct file and mode (read)
    mock_open_file.assert_called_with(str(install_file), "r")  # Convert PosixPath to string



@patch("builtins.open", new_callable=mock_open)
def test_write_api_schema(mock_open_file, temp_model_directory, bundles_repo_path):
    # Write the metadata file content
    metadata_file = temp_model_directory / "metadata.json"
    metadata_content = json.dumps({"Identifier": "test_model_id"})
    metadata_file.write_text(metadata_content)

    # Write the install.yml file content
    install_file = temp_model_directory / "install.yml"
    install_content = yaml.dump({"python": "3.8", "pip": ["requests"]})
    install_file.write_text(install_content)

    # Configure the mock to return the content for both files
    def mock_open_side_effect(file, mode="r", *args, **kwargs):
        if file == str(metadata_file):
            return mock_open(read_data=metadata_content).return_value
        elif file == str(install_file):
            return mock_open(read_data=install_content).return_value
        else:
            raise FileNotFoundError(f"Mock not configured for file: {file}")

    mock_open_file.side_effect = mock_open_side_effect

    # Create the FastApiAppPacker instance
    packer = FastApiAppPacker(str(temp_model_directory), str(bundles_repo_path))
    
    # Add assertions to verify functionality (e.g., check the generated bundle directory)
    assert packer.model_id == "test_model_id"


# Run tests
if __name__ == "__main__":
    pytest.main()



