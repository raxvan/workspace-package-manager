FROM python:3.8

RUN apt-get update && apt-get install -y \
	cmake \
	git \
	nano

RUN pip3 install --upgrade pip && pip3 install \
	pudb \
	gunicorn \
	flask \
	netifaces \
	shared-memory-dict


ENV VAULT_VERSION=0.0.1
ENV VAULT_HOST=0.0.0.0
ENV VAULT_PORT=5000
ENV VAULT_MAX_REQUEST_SIZE=1048576
ENV VAULT_CONFIG_DIR=/repo/build/vault_config
ENV VAULT_DATA_DIR=/repo/build/vault_data
ENV VAULT_SERVER_MODE=debug
ENV VAULT_PUBLIC_ACCESS=enable
ENV VAULT_STARTUP_TIME=2

ENV VAULT_INSTALL_DIR=/repo/build/pySecretsVault
ENV VAULT_URL=http://127.0.0.1:5000