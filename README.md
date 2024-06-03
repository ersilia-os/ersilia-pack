# Ersilia packaging based on FastAPI

Given an Ersilia model repository, it packs it to be served with FastAPI.

## Installation

```bash
pip install git+https://github.com/ersilia-os/ersilia-pack.git
```

## Usage

You can check that the model repository contains all expected files as follows:
```bash
ersilia_model_lint --repo_path $REPO_PATH
```

You can pack the mdoel as follows:
```bash
ersilia_model_pack --repo_path $REPO_PATH --bundle_path $BUNDLE_PATH
```

This will create a folder with the packed model, and the app available. The app can be served as follows:
```bash
ersilia_model_serve --bundle_path $BUNDLE_PATH --port $PORT
```