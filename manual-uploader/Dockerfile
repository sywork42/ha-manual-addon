ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Install Python and deps
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir --break-system-packages flask==3.0.3 flask-cors==4.0.1

# Copy application files
WORKDIR /app
COPY server.py /app/server.py
COPY static /app/static
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
