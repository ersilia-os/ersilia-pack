from src.ersilia_pack.templates.default import resolve_model_version


def test_resolve_model_version_prefers_release():
  metadata = {"Identifier": "eos3b5e", "Release": "v1.0.0"}

  assert resolve_model_version(metadata, fallback="1.0") == "v1.0.0"


def test_resolve_model_version_handles_lowercase_release():
  metadata = {"Identifier": "eos3b5e", "release": "v2.0.0"}

  assert resolve_model_version(metadata, fallback="1.0") == "v2.0.0"


def test_resolve_model_version_falls_back_when_missing():
  metadata = {"Identifier": "eos3b5e"}

  assert resolve_model_version(metadata, fallback="1.0") == "1.0"
