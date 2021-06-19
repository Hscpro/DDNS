FROM python:3.9.5-alpine
WORKDIR /root

RUN apk add --no-cache dcron libcap
RUN echo "*/5 * * * *   /ddns -c /config.json" > /etc/crontabs/root

CMD [ "crond", "-f" ]
