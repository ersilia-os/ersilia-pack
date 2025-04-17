<p align="center">
  <img src="assets/logo.png" alt="Ersilia-Pack Logo" width="200"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-GNU%20GPLv3-blueviolet?style=for-the-badge" alt="GNU License">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Code%20Style-black-FFD43B?style=for-the-badge&logo=python" alt="Code Style: Black">
</p>

</p>

# Ersilia-Pack

Ersilia-Pack is a FastAPI-based package designed to seamlessly serve your Ersilia model repository. It provides a comprehensive suite of APIs to monitor, execute, and manage model jobs, alongside detailed metadata support.

---

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
  - [Core Endpoints Overview](#core-endpoints-overview)
  - [Additional APIs Overview](#additional-apis-overview)
- [Output Orientation](#output-orientation)
- [For Developers](#for-developers)
- [License](#license)

---

## Installation

Install the package directly from GitHub:

```bash
pip install git+https://github.com/ersilia-os/ersilia-pack.git
```

---

## Usage

Validate your model repository structure by running:

```bash
ersilia_model_lint --repo_path $REPO_PATH
```

Pack your model repository—supporting pip, conda, or both—using:

```bash
ersilia_model_pack --repo_path $REPO_PATH --bundles_repo_path $BUNDLE_PATH
```

For models with conda dependencies, specify a particular conda environment:

```bash
ersilia_model_pack --repo_path $REPO_PATH --bundles_repo_path $BUNDLE_PATH --conda_env_name $CONDA_ENV
```

After packaging, serve the application with:

```bash
ersilia_model_serve --bundle_path $BUNDLE_PATH --port $PORT
```

---

| Category               | Endpoint                      | Path                         | Description                                                                                               |
|------------------------|-------------------------------|------------------------------|-----------------------------------------------------------------------------------------------------------|
| **Core**               | Swagger UI                    | `/docs`                      | Interactive API interface with custom styling and title.                                                  |
|                        | ReDoc                         | `/redoc`                     | Alternative documentation view with a comprehensive layout.                                               |
|                        | Health Check                  | `/healthz`                   | Returns system status (CPU, memory, circuit breaker stats).                                               |
|                        | Base URL                      | `/`                          | Displays basic info (model identifier and slug).                                                          |
| **Job Management**     | Submit Job                    | `/submit`                    | Accepts input data, queues an async job, returns a unique job ID.                                         |
|                        | Job Status                    | `/status/{job_id}`           | Check the current status of a job (pending, completed, failed).                                           |
|                        | Job Result                    | `/result/{job_id}`           | Retrieve output of a completed job; if unfinished, returns current status only.                           |
|                        | Reset Jobs                    | `/jobs/reset`                | Clears all job records (should be secured in production).                                                 |
| **Metadata**           | Complete Metadata             | `/card`                      | Retrieves all model metadata (name, title, description).                                                  |
|                        | Specific Metadata Field       | `/card/{field}`              | Fetches a specific metadata field; errors if field not found.                                             |
| **Run**                | Example Input                 | `/run/example/input`         | Provides sample input data for testing.                                                                   |
|                        | Example Output                | `/run/example/output`        | Returns sample output data to demonstrate expected responses.                                             |
|                        | Input Columns                 | `/run/columns/input`         | Lists the input data headers.                                                                             |
|                        | Output Columns                | `/run/columns/output`        | Lists the output data headers.                                                                            |
|                        | Execute Job (sync)            | `/run`                       | Processes input data synchronously and returns computed results.                                          |
| **Model Information**  | Model Status                  | `/models/status`             | Provides details on model version, runtime environment, and worker statuses.                              |
---

## Output Orientation

API responses are always provided in JSON format, following the Pandas DataFrame `orient` syntax. Supported output orientations include:
- **records:** Each row is output as a dictionary.
- **split:** Returns separate lists for index, columns, and data.
- **columns:** Outputs a dictionary with column names as keys and lists of values as entries.
- **index:** Outputs a dictionary with indices mapping to corresponding row data.
- **values:** Outputs a list of lists, with each sublist representing a row.

For more details, please refer to the [Pandas to_json documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html).

---

| Feature                          | Description                                                                                                                                                 |
|----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Interactive API Documentation**| Offers both Swagger UI and ReDoc interfaces with custom styling and titles, ensuring a user-friendly API exploration experience.                            |
| **Asynchronous Job Processing**  | Supports submission and execution of jobs asynchronously. Users receive a unique job ID and can track job status and results, with robust error handling.  |
| **Real-time Health Monitoring**  | Monitors system performance—including CPU and memory usage and circuit breaker metrics—to ensure reliable service operations.                               |
| **Flexible Metadata Access**     | Provides endpoints to retrieve complete metadata or specific metadata fields, offering a clear view of model details such as name, title, and description. |
| **Comprehensive Run Endpoints**  | Facilitates example data retrieval for both input and output, along with dynamic job execution, enabling easy testing and validation of model predictions. |
| **Multiple Output Formats**      | Supports various output orientations (records, split, columns, index, and values) based on Pandas DataFrame `to_json` syntax, allowing flexible JSON responses. |
---

## For Developers

- **Input Handling:**  
  Currently, only `"Compound"` and `"Single"` input types are supported. To accommodate additional types, update the schemas within the `templates/input_schemas` directory.

- **Best Practices:**  
  Follow standard FastAPI conventions. Ensure that any new features are well-documented and thoroughly tested.

- **Extensibility:**  
  The modular design of Ersilia-Pack allows you to easily integrate new endpoints and custom logic to extend functionality as needed.

---

## License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html).  
