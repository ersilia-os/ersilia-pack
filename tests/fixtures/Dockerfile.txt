FROM bentoml/model-server:0.11.0-py311
MAINTAINER ersilia

RUN pip install scikit-learn==1.2.0
RUN pip install MolVS==0.1.1
RUN pip install mordred==1.2.0
RUN pip install rdkit==2023.9.2
RUN pip install shap==0.41.0
RUN pip install pandas==1.5.2
RUN pip install numpy==1.23.5
RUN pip install dimorphite-dl==1.3.2
RUN pip install loguru==0.7.2


WORKDIR /repo
COPY . /repo
