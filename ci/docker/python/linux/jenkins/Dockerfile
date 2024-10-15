ARG PYTHON_VERSION=3.11
ARG PIP_FIND_LINKS=/wheels/
ARG PIPX_HOME=/pipx
ARG SONAR_SCANNER_VERSION=5.0.1.3006
FROM python:${PYTHON_VERSION} AS base_image
FROM base_image AS wheel_builder

ARG PIP_EXTRA_INDEX_URL
ARG PIP_TRUSTED_HOST
ARG PIP_INDEX_URL

COPY requirements-dev.txt requirements-gui.txt /requirements/

ARG PIP_FIND_LINKS
RUN mkdir -p ${PIP_FIND_LINKS} &&  \
    python -m pip install pip --upgrade && \
    python -m pip wheel --wheel-dir=${PIP_FIND_LINKS} --no-cache-dir -r /requirements/requirements-dev.txt -r /requirements/requirements-gui.txt

#==============================================================================
FROM base_image AS SONAR_BUILDER
RUN apt-get update && \
    apt-get install --no-install-recommends -y unzip

ARG SONAR_SCANNER_VERSION
ARG SONAR_SCANNER_HOME=/opt/sonar/${SONAR_SCANNER_VERSION}-linux
ENV SONAR_USER_HOME=/opt/sonar/.sonar
RUN curl --create-dirs -sSLo /tmp/sonar-scanner.zip \
        https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux.zip && \
    unzip -o /tmp/sonar-scanner.zip -d /opt/sonar/ && \
    rm /tmp/sonar-scanner.zip && \
    mkdir -p ${SONAR_USER_HOME}/cache && \
    chmod -R 777 "${SONAR_USER_HOME}" &&\
    ln -s /opt/sonar/sonar-scanner-${SONAR_SCANNER_VERSION}-linux/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    which sonar-scanner



#==============================================================================
FROM base_image

RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update &&  \
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install --no-install-recommends tzdata && \
    apt-get install -y --no-install-recommends \
      libxkbcommon-x11-0 \
      libgl1-mesa-glx \
      locales \
      locales-all \
      latexmk \
      tex-gyre \
      libegl-dev \
      libdbus-1-3 \
      texlive-formats-extra \
      xvfb

RUN mkdir -p /.cache/pip && \
    chmod -R 777 /.cache

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV QT_QPA_PLATFORM="offscreen"
ARG PIP_FIND_LINKS
ARG PIP_EXTRA_INDEX_URL
ARG PIP_TRUSTED_HOST
COPY --from=wheel_builder ${PIP_FIND_LINKS}/* ${PIP_FIND_LINKS}/
COPY --from=wheel_builder requirements/ /requirements
RUN pip install --no-index --no-cache-dir --find-links=${PIP_FIND_LINKS} \
    -r /requirements/requirements-dev.txt -r /requirements/requirements-gui.txt

ARG PIPX_HOME
ENV PIPX_HOME=${PIPX_HOME}
ENV PIPX_BIN_DIR=${PIPX_HOME}/bin
RUN pip install --no-cache-dir pipx && \
    pipx ensurepath && \
    mkdir -p $PIPX_HOME  && chmod -R 777 $PIPX_HOME
RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install pip-audit

COPY --from=SONAR_BUILDER /opt/sonar /opt/sonar/
ARG SONAR_SCANNER_VERSION
ENV SONAR_SCANNER_VERSION=${SONAR_SCANNER_VERSION}
ARG SONAR_SCANNER_HOME=/opt/sonar/${SONAR_SCANNER_VERSION}-linux
ENV SONAR_USER_HOME=/opt/sonar/.sonar
RUN ln -s /opt/sonar/sonar-scanner-${SONAR_SCANNER_VERSION}-linux/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    which sonar-scanner
RUN mkdir -p /home/user/.sonar/ && chmod -R 777 /home/user/