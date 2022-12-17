FROM python:3.9.5-alpine

RUN pip install click
RUN pip install PrettyTable
RUN pip install wcwidth
RUN pip install six

RUN echo 'python3 /ddns/run.py -c /ddns/config.json -a /ddns/ddns.cache' > /ddns.su
RUN chmod 755 /ddns.su

#         .---------------- 分钟 (0 - 59)
#         |  .------------- 小时 (0 - 23)
#         |  |  .---------- 天   (1 - 31)
#         |  |  |  .------- 月   (1 - 12) OR jan,feb,mar,apr ...
#         |  |  |  |  .---- 星期 (0 - 6) (Sunday=0 or 7) OR sun,mon,tue,wed,thu,fri,sat
#         |  |  |  |  |
#         *  *  *  *  * command to be executed
RUN echo "*/5 * * * * /ddns.su" > /etc/crontabs/root
CMD [ "crond", "-f" ]
