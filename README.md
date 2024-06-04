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

## API

The FastAPI APIs are divided in two blocks, namely **Metadata** and **App**. Generally, Metadata includes `GET` requests and `App` includes `POST` requests.

### Metadata

### App

#### Output orientation

Outputs are always provided in `JSON` format. We use the `orient` syntax [from Pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html), including:
- `records`: 
- `split`:
- `columns`: 
- `index`:
- `values`:

## For developers

- At the moment, only `"Compound"` `"Single"` inputs are accepted. If more casuistics are necessary, they should be included inside `templates/input_schemas`.