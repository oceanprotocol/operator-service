FROM python:3.6-alpine
LABEL maintainer="Ocean Protocol <devops@oceanprotocol.com>"

ARG VERSION

RUN apk add --no-cache --update\
    build-base \
    gcc \
    gettext\
    gmp \
    gmp-dev \
    libffi-dev \
    openssl-dev \
    py-pip \
    python3 \
    python3-dev \
    postgresql-dev \
  && pip install virtualenv

COPY . /operator-service
WORKDIR /operator-service

RUN pip install .

# config.ini configuration file variables
ENV OPERATOR_URL='http://0.0.0.0:8050'

# docker-entrypoint.sh configuration file variables
ENV OPERATOR_WORKERS='1'
ENV OPERATOR_TIMEOUT='9000'
ENV ALGO_POD_TIMEOUT='3600'
ENV ALLOWED_PROVIDERS=""
ENV SIGNATURE_REQUIRED=0
ENV OPERATOR_ADDRESS='0x6D39A833d1a6789AECa50dB85CB830bc08319F45'

ENTRYPOINT ["/operator-service/docker-entrypoint.sh"]

EXPOSE 8050
