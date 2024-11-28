import pytest
import yaml
import json
import os
from pathlib import Path
import sys

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))
from src.ersilia_pack.parsers import MetadataYml2JsonConverter

# Get the absolute path to the Models directory
MODELS_DIR = Path(__file__).parent / "Models"

def test_valid_metadata_conversion():
    valid_yml_path = MODELS_DIR / "valid_metadata.yml"
    converter = MetadataYml2JsonConverter(str(valid_yml_path))
    result = converter.convert()
    
    # Verify type conversions and content
    assert isinstance(result["Identifier"], str)
    assert isinstance(result["Task"], list)
    assert isinstance(result["Output"], list)
    assert isinstance(result["Output Type"], list)
    assert isinstance(result["Tag"], list)
    assert isinstance(result["Docker Architecture"], list)
    
    # Verify specific content
    assert result["Identifier"] == "bioimage.io/test-model"
    assert result["Slug"] == "unet-2d-nuclei"
    assert len(result["Task"]) == 2
    assert len(result["Output"]) == 2
    assert len(result["Tag"]) == 4
    assert result["License"] == "MIT"

def test_invalid_metadata_conversion():
    invalid_yml_path = MODELS_DIR / "incorrect_metadata.yml"
    converter = MetadataYml2JsonConverter(str(invalid_yml_path))
    
    # Should raise exception due to invalid Identifier format
    with pytest.raises(Exception) as exc_info:
        converter.convert()
    assert "Value is a list with more than one element" in str(exc_info.value)

def test_json_file_output(tmp_path):
    valid_yml_path = MODELS_DIR / "valid_metadata.yml"
    json_path = tmp_path / "metadata.json"
    converter = MetadataYml2JsonConverter(str(valid_yml_path), str(json_path))
    converter.convert()
    
    # Verify JSON file creation and content
    assert json_path.exists()
    with open(json_path) as f:
        data = json.load(f)
    
    assert isinstance(data["Task"], list)
    assert isinstance(data["Output"], list)
    assert data["Identifier"] == "bioimage.io/test-model"
    assert data["Slug"] == "unet-2d-nuclei"

def test_complete_conversion_workflow():
    # Create output paths
    output_dir = MODELS_DIR / "json_output"
    output_dir.mkdir(exist_ok=True)
    
    # Convert valid metadata
    valid_json_path = output_dir / "valid_metadata.json"
    valid_converter = MetadataYml2JsonConverter(
        str(MODELS_DIR / "valid_metadata.yml"), 
        str(valid_json_path)
    )
    valid_converter.convert()
    
    # Verify valid metadata conversion
    assert valid_json_path.exists()
    with open(valid_json_path) as f:
        valid_data = json.load(f)
    assert valid_data["Identifier"] == "bioimage.io/test-model"
    
    # Try to convert invalid metadata (should fail but not crash)
    invalid_json_path = output_dir / "invalid_metadata.json"
    invalid_converter = MetadataYml2JsonConverter(
        str(MODELS_DIR / "incorrect_metadata.yml"), 
        str(invalid_json_path)
    )
    with pytest.raises(Exception):
        invalid_converter.convert()
    
    # Clean up test files
    if valid_json_path.exists():
        valid_json_path.unlink()
    if invalid_json_path.exists():
        invalid_json_path.unlink()
    if output_dir.exists():
        output_dir.rmdir()

def test_missing_file():
    with pytest.raises(FileNotFoundError):
        converter = MetadataYml2JsonConverter("nonexistent.yml")
        converter.convert()

if __name__ == "__main__":
    # This will create the JSON files when running the script directly
    output_dir = MODELS_DIR / "json_output"
    output_dir.mkdir(exist_ok=True)
    
    # Convert valid metadata
    valid_yml_path = MODELS_DIR / "valid_metadata.yml"
    valid_json_path = output_dir / "valid_metadata.json"
    converter = MetadataYml2JsonConverter(str(valid_yml_path), str(valid_json_path))
    converter.convert()
    
    print(f"Created JSON file: {valid_json_path}")