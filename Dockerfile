FROM python:3.8-slim-buster
LABEL maintainer="Ocean Protocol <devops@oceanprotocol.com>"

ARG VERSION

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        gettext \
        libgmp-dev \
        libffi-dev \
        libssl-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /operator-service
WORKDIR /operator-service

RUN pip install .

# config.ini configuration file variables
ENV OPERATOR_URL='http://0.0.0.0:8050'

# docker-entrypoint.sh configuration file variables
ENV OPERATOR_WORKERS='20'
ENV OPERATOR_TIMEOUT='9000'
ENV ALGO_POD_TIMEOUT='3600'
ENV ALLOWED_PROVIDERS=""
ENV ALLOWED_ADMINS='["myAdminPass"]'
ENV SIGNATURE_REQUIRED=0
ENV OPERATOR_ADDRESS='0x6D39A833d1a6789AECa50dB85CB830bc08319F45'

ENTRYPOINT ["/operator-service/docker-entrypoint.sh"]

EXPOSE 8050
