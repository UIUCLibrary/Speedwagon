ARG PIP_DOWNLOAD_CACHE=/.cache/pip
ARG UV_CACHE_DIR=/.cache/uv
ARG UV_EXTRA_INDEX_URL

ARG PIPX_HOME=/pipx

FROM ubuntu:22.04 AS wheel_builder_base
COPY ci/docker/python/linux/tox/apt-packages.txt /tmp/
RUN apt-get update && \
    apt-get install -y software-properties-common gpg-agent --no-install-recommends && \
    add-apt-repository ppa:deadsnakes/ppa && \
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata && \
    apt-get update && \
     < /tmp/apt-packages.txt xargs apt-get install -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV QT_QPA_PLATFORM="offscreen"

ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY requirements-dev.txt /tmp/python_requirements/requirements-dev.txt
ARG UV_EXTRA_INDEX_URL
ENV UV_INDEX_STRATEGY=unsafe-best-match
RUN --mount=type=cache,target=/.cache/python \
    python3 -m pip install --cache-dir=/.cache/python/pip --upgrade pip && \
    python3 -m pip install --cache-dir=/.cache/python/pip --upgrade uv && \
    uv pip install --cache-dir=/.cache/python/uv --system -r /tmp/python_requirements/requirements-dev.txt tox-uv

ARG PIP_DOWNLOAD_CACHE
ARG UV_CACHE_DIR
RUN mkdir -p ${PIP_DOWNLOAD_CACHE} && \
    chmod -R 777 ${PIP_DOWNLOAD_CACHE} && \
    mkdir -p ${UV_CACHE_DIR} && \
    chmod -R 777 ${UV_CACHE_DIR}

ARG PIPX_HOME
ENV PIPX_HOME=${PIPX_HOME}
ENV PIPX_BIN_DIR=${PIPX_HOME}/bin
RUN --mount=type=cache,target=/.cache/python \
    python3 -m uv pip install --cache-dir=/.cache/python/uv --system --no-cache-dir pipx && \
    pipx ensurepath && \
    mkdir -p $PIPX_HOME  && chmod -R 777 $PIPX_HOME

ARG UV_CACHE_DIR
ARG PIP_DOWNLOAD_CACHE
ENV UV_CACHE_DIR=${UV_CACHE_DIR}
ENV PIP_DOWNLOAD_CACHE=${PIP_DOWNLOAD_CACHE}

WORKDIR /src
CMD ["tox", "--workdir", "/tmp/tox", "--recreate", "-p=auto"]
