ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python 3 + Flask + Flask-CORS using Alpine packages (reliable across base image versions).
# Fall back to pip if apk packages aren't available.
RUN apk add --no-cache python3 py3-pip py3-flask py3-flask-cors \
    || (apk add --no-cache python3 py3-pip && \
        pip3 install --no-cache-dir --break-system-packages flask flask-cors)

WORKDIR /app
COPY server.py /app/server.py
COPY static /app/static
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
