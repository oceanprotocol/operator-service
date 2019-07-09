#!/bin/sh

export CONFIG_FILE=/operator-service/config.ini
envsubst < /operator-service/config.ini.template > /operator-service/config.ini

gunicorn -b ${OPERATOR_URL#*://} -w ${OPERATOR_WORKERS} -t ${OPERATOR_TIMEOUT} operator_service.run:app
tail -f /dev/null
