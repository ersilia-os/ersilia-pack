# Ersilia Packaging Based on FastAPI

Given an Ersilia model repository, this package allows you to serve it using FastAPI.

## Installation

```bash
pip install git+https://github.com/ersilia-os/ersilia-pack.git
```

## Usage

You can check that the model repository contains all the expected files as follows:

```bash
ersilia_model_lint --repo_path $REPO_PATH
```

You can pack the model as follows:

```bash
ersilia_model_pack --repo_path $REPO_PATH --bundle_path $BUNDLE_PATH
```

This will create a folder with the packed model and the app available. The app can be served as follows:

```bash
ersilia_model_serve --bundle_path $BUNDLE_PATH --port $PORT
```

## API

The FastAPI APIs are divided into two blocks: **Metadata** and **App**. Generally, Metadata includes `GET` requests, and App includes `POST` requests.

### Metadata

- **GET /card**: Retrieves metadata about the model, such as its name, title, and description.
- **GET /card/model_id**: Gets the model identifier.

### App

- **POST /run**: Takes input data and returns predictions from the model.

#### Output Orientation

Outputs are always provided in `JSON` format. We use the `orient` syntax from [Pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html), including:
- `records`: Each row is a dictionary.
- `split`: Dictionary containing separate lists for `index`, `columns`, and `data`.
- `columns`: Dictionary where each key is a column name, and the value is a list of column values.
- `index`: Dictionary where each key is an index value, and the value is a dictionary of row data.
- `values`: List of lists with row data.

## For Developers

- Currently, only `"Compound"` and `"Single"` inputs are accepted. If more input types are needed, they should be included inside `templates/input_schemas`.
- Ensure to follow best practices for FastAPI development and maintain proper documentation and tests for any new features added to the package.
