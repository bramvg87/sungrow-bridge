#!/usr/bin/with-contenv bashio
set -e

PORT=$(bashio::config 'port')

export SUNGROW_APP_KEY=$(bashio::config 'sungrow_app_key')
export SUNGROW_SECRET_KEY=$(bashio::config 'sungrow_secret_key')
export SUNGROW_APP_ID=$(bashio::config 'sungrow_app_id')
export SUNGROW_REDIRECT_URI=$(bashio::config 'sungrow_redirect_uri')
export SUNGROW_SERVER=$(bashio::config 'sungrow_server')
export SG_PLANT_NAME=$(bashio::config 'sg_plant_name')
export SH_PLANT_NAME=$(bashio::config 'sh_plant_name')
export CACHE_TTL_SECONDS=$(bashio::config 'cache_ttl_seconds')

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}