# syntax=docker/dockerfile:1.7

FROM python:3.12.8-alpine3.21

ARG VERSION=0.1.0
ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown
ARG IMAGE_REF=local

LABEL org.opencontainers.image.title="binarybitops-demo" \
      org.opencontainers.image.description="Phase 3 WBS 3.10 HDE delivery-path demonstrator (not Nexus)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.source="https://github.com/Boitshoko88/BinaryBitOps" \
      org.opencontainers.image.licenses="Proprietary"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PORT=8080 \
    DEMO_ENV=nonprod \
    DEMO_RELEASE=wbs-3.10 \
    VAULT_INJECTED_FILE=/vault/secrets/demo.json \
    REQUIRE_VAULT_INJECTION=false \
    APP_VERSION="${VERSION}" \
    GIT_SHA="${GIT_SHA}" \
    BUILD_DATE="${BUILD_DATE}" \
    IMAGE_REF="${IMAGE_REF}"

WORKDIR /app

# Fixed, non-root runtime identity shared by the image, manifests and tests.
RUN addgroup -g 10001 -S app \
    && adduser -u 10001 -S -D -H -G app -s /sbin/nologin app

COPY --chown=10001:10001 binarybitops.py /app/binarybitops.py
COPY --chown=10001:10001 binarybitops/ /app/binarybitops/

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).status == 200 else 1)"]

ENTRYPOINT ["python", "-m", "binarybitops.server"]
