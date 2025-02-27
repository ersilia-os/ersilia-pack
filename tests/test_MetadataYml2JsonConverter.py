import json

import pytest

from src.ersilia_pack.parsers.metadata_yml2json_converter import (
  MetadataYml2JsonConverter,
)


class TestMetadataYml2JsonConverter:
  def test_correct_metadata_conversion(self):
    yml_file = "tests/fixtures/correct_metadata.yml"
    converter = MetadataYml2JsonConverter(yml_file)
    result = converter.convert()

    assert result["Identifier"] == "model-001"
    assert result["Slug"] == "my-model"
    assert result["Task"] == ["classification"]
    assert result["Output"] == ["output.csv"]
    assert result["Docker Architecture"] == ["amd64", "arm64"]

  def test_incorrect_metadata_conversion(self):
    yml_file = "tests/fixtures/incorrect_metadata.yml"
    converter = MetadataYml2JsonConverter(yml_file)

    with pytest.raises(Exception, match="Value is a list with more than one element"):
      converter.convert()

  def test_save_to_json_file(self, tmp_path):
    yml_file = "tests/fixtures/correct_metadata.yml"
    json_file = tmp_path / "output.json"
    converter = MetadataYml2JsonConverter(yml_file, json_file)
    converter.convert()

    with open(json_file, "r") as f:
      data = json.load(f)
      assert data["Identifier"] == "model-001"
      assert data["Slug"] == "my-model"
