#!/usr/bin/with-contenv bashio

export MAX_UPLOAD_MB=$(bashio::config 'max_upload_mb')
export SUBFOLDER=$(bashio::config 'subfolder')

bashio::log.info "Starting Manual Uploader..."
bashio::log.info "Max upload size: ${MAX_UPLOAD_MB} MB"
bashio::log.info "Subfolder: ${SUBFOLDER}"

cd /app
exec python3 server.py
