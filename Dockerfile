FROM python:3.9.5
WORKDIR /root

RUN apt-get update -y && \
    apt-get install -y cron && \
    touch /var/log/cron.log
RUN echo "*/5 * * * *   python3 /ddns/run.py -c /ddns/config.json" > /etc/crontab
ADD /etc/crontab /etc/cron.d/crontab

# tail 可以防止容器自动退出运行
CMD cron && tail -f /var/log/cron.log
