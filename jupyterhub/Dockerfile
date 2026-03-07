FROM jupyterhub/jupyterhub:5.2

RUN pip install --no-cache-dir \
    dockerspawner==13.0.0

COPY jupyterhub/jupyterhub_config.py /etc/jupyterhub/jupyterhub_config.py

WORKDIR /srv/jupyterhub

EXPOSE 8000

CMD ["jupyterhub", "-f", "/etc/jupyterhub/jupyterhub_config.py"]
