FROM python:3.9.5-alpine

RUN echo 'python3 /ddns/run.py' > /ddns.su
RUN chmod 755 /ddns.su

RUN echo "*/5 * * * *   /ddns.su" > /etc/crontabs/root
CMD [ "crond", "-f" ]
