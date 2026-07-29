ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

ARG BUILD_VERSION
ARG BUILD_ARCH

RUN apk add --no-cache python3 py3-yaml py3-websocket-client

COPY rootfs /

RUN chmod a+x \
    /etc/services.d/ai-supervisor-connector/run \
    /etc/services.d/ai-supervisor-connector/finish

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.title="Home Assistant App: AI Supervisor V5 Connector" \
    org.opencontainers.image.description="Safe connector between Home Assistant and the external AI Supervisor V5 Engine" \
    org.opencontainers.image.source="https://github.com/vaitkus82-cpu/ha-ai-supervisor-v5" \
    org.opencontainers.image.licenses="MIT"
