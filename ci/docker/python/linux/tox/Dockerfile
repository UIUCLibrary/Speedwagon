FROM ubuntu:20.04 as wheel_builder_base
COPY ci/docker/python/linux/tox/apt-packages.txt /tmp/
RUN apt-get update && \
    apt-get install -y software-properties-common --no-install-recommends && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    < /tmp/apt-packages.txt xargs apt-get install -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

FROM wheel_builder_base
RUN mkdir -p /.cache/pip && \
    chmod -R 777 /.cache
ENV QT_QPA_PLATFORM="offscreen"
COPY requirements/ /tmp/requirements
RUN pip3 install --no-cache-dir pip --upgrade && \
    pip3 install --no-cache-dir -r /tmp/requirements/requirements_tox.txt
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
RUN pip3 wheel -w /wheels --no-cache-dir wheel

RUN pip3 install --no-cache-dir -r /tmp/requirements/requirements-devpi.txt
WORKDIR /src
CMD ["tox", "--workdir", "/tmp/tox", "--recreate", "-p=auto"]
