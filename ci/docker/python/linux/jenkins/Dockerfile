FROM python:latest
RUN --mount=type=bind,source=./ci/docker/python/linux/jenkins/apt-packages.txt,target=/tmp/apt-packages.txt\
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
      < /tmp/apt-packages.txt xargs apt-get install -yqq --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
