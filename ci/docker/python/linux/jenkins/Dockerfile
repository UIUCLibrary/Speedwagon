ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION} as base_image
FROM base_image as wheel_builder

ARG PIP_EXTRA_INDEX_URL
ARG PIP_TRUSTED_HOST
ARG PIP_INDEX_URL

COPY requirements.txt requirements-dev.txt requirements-gui.txt ci/docker/python/shared/requirements-ci.txt ci/docker/python/shared/requirements-extra.txt /tmp/
COPY requirements/ /tmp/requirements
RUN python -m pip install  --no-cache-dir --upgrade pip &&  \
    pip install --no-cache-dir wheel && \
    pip install --no-cache-dir setuptools && \
    pip install --no-cache-dir conan cmake && \
    pip wheel --wheel-dir=/wheels --no-cache-dir \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
        -r /tmp/requirements-gui.txt \
        -r /tmp/requirements-ci.txt && \
    pip wheel  --no-cache-dir --wheel-dir=/wheels -r /tmp/requirements-extra.txt && \
    rm -rf  /root/.cache

#==============================================================================
FROM base_image as SONAR_BUILDER
RUN apt-get update && \
    apt-get install -y --no-install-recommends unzip=6.0-26+deb11u1
ENV SONAR_SCANNER_VERSION=4.6.2.2472
ARG SONAR_SCANNER_HOME=/opt/sonar/${SONAR_SCANNER_VERSION}-linux
ENV SONAR_USER_HOME=/opt/sonar/.sonar
RUN curl --create-dirs -sSLo /tmp/sonar-scanner.zip \
        https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-$SONAR_SCANNER_VERSION-linux.zip && \
    unzip -o /tmp/sonar-scanner.zip -d /opt/sonar/ && \
    rm /tmp/sonar-scanner.zip && \
    mkdir -p $SONAR_USER_HOME/cache && \
    chmod -R 777 "${SONAR_USER_HOME}" &&\
    ln -s /opt/sonar/sonar-scanner-$SONAR_SCANNER_VERSION-linux/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    which sonar-scanner


#==============================================================================
FROM base_image

RUN apt-get update &&  \
    apt-get install -y --no-install-recommends tzdata=2021a-1+deb11u8 && \
    ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    apt-get install -y --no-install-recommends \
      libxkbcommon-x11-0=1.0.3-2 \
      libgl1-mesa-glx=20.3.5-1 \
      locales=2.31-13+deb11u5 \
      locales-all=2.31-13+deb11u5 \
      latexmk=1:4.70b-0.2 \
      tex-gyre=20180621-3.1 \
      libegl-dev=1.3.2-1 \
      libdbus-1-3=1.12.24-0+deb11u1 \
      texlive-formats-extra=2020.20210202-3 \
      xvfb=2:1.20.11-1+deb11u5 && \
    rm -rf  /root/.cache
RUN mkdir -p /.cache/pip && \
    chmod -R 777 /.cache

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV QT_QPA_PLATFORM="offscreen"
COPY --from=wheel_builder /wheels /wheels/
COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt requirements-gui.txt ci/docker/python/shared/requirements-extra.txt /tmp/
COPY requirements/ /tmp/requirements

RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links=/wheels \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
        -r /tmp/requirements-gui.txt \
        -r /tmp/requirements-ci.txt

ENV PIP_FIND_LINKS=/wheels
RUN python -m pip install --no-cache-dir types-PyYAML types-requests

COPY --from=SONAR_BUILDER /opt/sonar /opt/sonar/
ENV SONAR_SCANNER_VERSION=4.6.2.2472
ARG SONAR_SCANNER_HOME=/opt/sonar/${SONAR_SCANNER_VERSION}-linux
ENV SONAR_USER_HOME=/opt/sonar/.sonar
RUN ln -s /opt/sonar/sonar-scanner-${SONAR_SCANNER_VERSION}-linux/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    which sonar-scanner
RUN mkdir -p /home/user/.sonar/ && chmod -R 777 /home/user/
