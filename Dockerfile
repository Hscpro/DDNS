FROM alpine:latest
RUN echo 'echo "Hello, Shell"' > /test.su
RUN chmod 755 /test.su
RUN echo "*/5 * * * *   /test.su" > /etc/crontabs/root
CMD [ "crond", "-f" ]
