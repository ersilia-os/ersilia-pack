FROM bentoml/model-server:0.11.0-py37
MAINTAINER ersilia

RUN pip install rdkit==2023.3.2
RUN pip install git+https://github.com/bp-kelley/descriptastorus.git@d552f934757378a61dd1799cdb589a864032cd1b
RUN pip install tqdm==4.66.2
RUN pip install typed-argument-parser==1.6.1
RUN pip install scikit-learn==1.0.2
RUN pip install torch==1.13.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install pandas==1.3.5
RUN pip install numpy==1.21.6
RUN pip install scipy==1.7.3
RUN pip install xarray==0.20.2

WORKDIR /repo
COPY . /repo
