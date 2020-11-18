FROM ubuntu:20.04 as wheel_builder_base
COPY ci/docker/python/linux/tox/apt-packages.txt /tmp/
RUN apt update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt update && \
    cat /tmp/apt-packages.txt | xargs apt-get -y install
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -g $GROUP_ID user && \
    useradd -u $USER_ID -s /bin/sh -m -d /home/user -g user user

FROM wheel_builder_base as WHEEL_BUILDER_PY36
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt /tmp/
ENV PYTHON=python3.6
RUN $PYTHON -m pip install pip --upgrade pip && \
    $PYTHON -m pip install wheel && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-dev.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-vendor.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-ci.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-extra.txt

# ==============================================================================
FROM wheel_builder_base as WHEEL_BUILDER_PY37
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt /tmp/
ENV PYTHON=python3.7
RUN $PYTHON -m pip install pip --upgrade pip && \
    $PYTHON -m pip install wheel && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-dev.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-vendor.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-ci.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-extra.txt

# ==============================================================================
FROM wheel_builder_base as WHEEL_BUILDER_PY38
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt /tmp/
ENV PYTHON=python3.8
RUN $PYTHON -m pip install pip --upgrade pip && \
    $PYTHON -m pip install wheel && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-dev.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-vendor.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-ci.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-extra.txt

# ==============================================================================
FROM wheel_builder_base as WHEEL_BUILDER_PY39
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt /tmp/
ENV PYTHON=python3.9
RUN $PYTHON -m pip install pip --upgrade pip && \
    $PYTHON -m pip install wheel && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-dev.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-vendor.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-ci.txt && \
    $PYTHON -m pip wheel -w /wheels --no-cache-dir -v -r /tmp/requirements-extra.txt

# ==============================================================================
FROM wheel_builder_base
RUN pip3 install tox

ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
COPY --from=WHEEL_BUILDER_PY36 /wheels/* /wheels/
COPY --from=WHEEL_BUILDER_PY37 /wheels/* /wheels/
COPY --from=WHEEL_BUILDER_PY38 /wheels/* /wheels/
COPY --from=WHEEL_BUILDER_PY39 /wheels/* /wheels/
ENV PIP_FIND_LINKS=/wheels
WORKDIR /src
CMD tox --workdir /tmp/tox --recreate -p=auto