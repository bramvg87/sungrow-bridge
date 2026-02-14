ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM ${BUILD_FROM}

WORKDIR /usr/src/app

# Python + venv + pip
RUN apk add --no-cache python3 py3-pip py3-virtualenv

# Create venv and install requirements into it
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8088
CMD ["/run.sh"]
