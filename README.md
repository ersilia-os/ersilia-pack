# New Ersilia packaging based on FastAPI

## The model repository

The model template should be very simple:
1. A `model` folder, with `framework` and `checkpoints` subfolders.
1. Inside the `model` folder, an arbitrary number of `.sh` files can exist. For example, `run.sh`. The base name of these files will determine the API names for FastAPI.
1. A `metadata.json` file.
1. An `install.sh` file. Optionally, We can have multiple install files depending on the platform and/or GPU usage. One option would be that these files are called `install_arm.sh`, `install_gpu.sh` etc. This is to be discussed.

We might also consider the following:
- Making `example_input.csv` and `example_output.csv` mandatory.
- Allowing for running models from `.sh` or `.py` (e.g. `run.py`). When `run.py` are specified, the idea is that the model is only loaded once, which would be very beneficial for the heavier models. We can discuss about this.

## The Ersilia Pack package

We should have an `ersilia-pack` package that allows us to write a FastAPI app based on the previous model repository. Some considerations:
- Ersilia Pack should be lightweight and independent of Ersilia.
- In principle, this package could work with or without conda. Getting rid of conda would lighten the images substantially.

I envisage the following functionality:
```bash
ersilia_pack --model_dir $MODEL_DIR [--conda/--system]
```
- If `--conda` is specified, then we will create a conda environment as usual (named with the `model_id`)
- If `--system` is specified, then we can simply run the installs in the system. When building a model inside a container, there is in principle no reason to use conda.

Ersilia Pack will take care of **writing** a FastAPI app based on the information of the model folder. Everything will be stored in `$EOS/repository/$MODEL_ID`. In this sense, the Ersilia Pack will create a folder that is already similar to the BentoML folder that we already have.

In addition, we should have the following functionality:
```bash
ersilia_serve --repository_dir $MODEL_DIR [--port $PORT] [--host $HOST]
```

This will simply serve the FastAPI app using `uvicorn`.

## Modifications in the Ersilia CLI fetch command

These modifications will not affect dramatically the fetching from DockerHub (with some exceptions, especially if the API endpoints are modified (for example, `info` now expects and empty input)).

However, this will have implications if fetch is done from GitHub or S3. In that case, to stay on the safe side, I would always run `ersilia_pack` with the `--conda` option.

We will have to ensure backward compatibility. This should not be a problem, though: in principle, it should be easy to identify whether a model requires the legacy `bentoml` packaging or the `ersilia_pack` packaging. Therefore, we do not have to install `bentoml` in `ersilia` by default. Rather, we can just install it on the fly when we need it.

## Advantages of the new approach

- We remove entirely the `bentoml` dependency.
- Conda becomes non-essential, at least within the docker images.
- Our base docker image can be much slimmer, containg only `ersilia_pack` (i.e. `fastapi` and `uvicorn`).
- Easy to extend to `fit` commands.
- Easier to add authentication or configuration parameters.