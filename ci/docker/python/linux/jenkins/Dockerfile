FROM ghcr.io/astral-sh/uv:latest AS uv_builder
FROM python:latest
RUN --mount=type=bind,source=./ci/docker/python/linux/jenkins/apt-packages.txt,target=/tmp/apt-packages.txt\
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
      < /tmp/apt-packages.txt xargs apt-get install -yqq --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
COPY --from=uv_builder /uv /uvx /bin/

# To help mark the image as a CI image so it can be cleaned up more easily
LABEL purpose=ci
