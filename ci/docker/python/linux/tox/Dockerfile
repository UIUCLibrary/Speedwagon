FROM ubuntu:20.04 as wheel_builder_base
COPY ci/docker/python/linux/tox/apt-packages.txt /tmp/
RUN apt update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt update && \
    cat /tmp/apt-packages.txt | xargs apt-get -y install
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

# ==============================================================================
FROM wheel_builder_base as WHEEL_BUILDER_PY38
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt /tmp/
ENV PYTHON=python3.8
RUN $PYTHON -m pip install pip --upgrade pip && \
    $PYTHON -m pip install wheel && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
        -r /tmp/requirements-vendor.txt \
        -r /tmp/requirements-ci.txt \
        -r /tmp/requirements-extra.txt
RUN $PYTHON -m pip wheel -w /wheels --no-cache-dir -v devpi_client

# ==============================================================================
FROM wheel_builder_base as WHEEL_BUILDER_PY39
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt /tmp/
ENV PYTHON=python3.9
RUN $PYTHON -m pip install pip --upgrade pip && \
    $PYTHON -m pip install wheel && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
        -r /tmp/requirements-vendor.txt \
        -r /tmp/requirements-ci.txt \
        -r /tmp/requirements-extra.txt
RUN $PYTHON -m pip wheel -w /wheels --no-cache-dir -v devpi_client

# ==============================================================================
FROM wheel_builder_base as WHEEL_BUILDER_PY310
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt /tmp/
ENV PYTHON=python3.10
RUN $PYTHON -m ensurepip --upgrade && \
    $PYTHON -m pip install pip --upgrade pip && \
    $PYTHON -m pip install wheel && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
        -r /tmp/requirements-vendor.txt \
        -r /tmp/requirements-ci.txt \
        -r /tmp/requirements-extra.txt
RUN $PYTHON -m pip wheel -w /wheels --no-cache-dir -v devpi_client

# ==============================================================================
FROM wheel_builder_base
RUN mkdir -p /.cache/pip && \
    chmod -R 777 /.cache
ENV QT_QPA_PLATFORM="offscreen"
RUN pip3 install pip --upgrade && \
    pip3 install tox
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
RUN pip3 wheel -w /wheels --no-cache-dir wheel
COPY --from=WHEEL_BUILDER_PY38 /wheels/* /wheels/
COPY --from=WHEEL_BUILDER_PY39 /wheels/* /wheels/
COPY --from=WHEEL_BUILDER_PY310 /wheels/* /wheels/
ENV PIP_FIND_LINKS=/wheels
RUN pip3 install --no-index --find-links=/wheels devpi_client
WORKDIR /src
CMD tox --workdir /tmp/tox --recreate -p=auto