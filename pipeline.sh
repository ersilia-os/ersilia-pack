HOME_DIR=$(eval echo ~$USER)
MODEL_ID="$1"

ersilia_model_lint --repo_path "$MODEL_ID"
ersilia_model_pack --repo_path "$MODEL_ID" --bundles_repo_path "$HOME_DIR"/eos/repository
ersilia_model_serve --bundle_path "$HOME_DIR"/eos/repository/"$MODEL_ID"
