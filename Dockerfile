FROM python:3.11.8

RUN mkdir /app
WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential docker.io curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir numpy pandas scikit-learn matplotlib seaborn scipy jupyterhub jupyterlab \
    && python -m ipykernel install --name=autograder-env --display-name "Autograder Environment"

RUN useradd -m -u 1000 -s /bin/bash jovyan \
    && mkdir -p /home/jovyan/work \
    && chown -R jovyan:jovyan /home/jovyan

COPY . .

USER 1000
