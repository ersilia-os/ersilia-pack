FROM python:3.10-slim
WORKDIR /root
COPY ./eos80ch /root/eos80ch
COPY ./ersilia-pack /root/ersilia-pack
RUN cd ersilia-pack && pip install .
RUN ersilia_model_pack --repo_path eos80ch --bundles_repo_path /root/eos/repository
ENTRYPOINT ["ersilia_model_serve", "--port",  "5000", "--bundle_path", "/root/eos/repository/eos80ch"]
