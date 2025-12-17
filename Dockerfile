FROM python:3.11.8

RUN mkdir /app

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

RUN pip install --no-cache-dir \
    numpy \
    pandas \
    scikit-learn \
    matplotlib \
    seaborn \
    scipy
RUN python -m ipykernel install --name=autograder-env --display-name "Autograder Environment"

COPY . .