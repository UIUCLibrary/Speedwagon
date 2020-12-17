ARG PYTHON_VERSION=3.8

FROM python:${PYTHON_VERSION} as wheel_builder

ARG PIP_EXTRA_INDEX_URL
ARG PIP_TRUSTED_HOST
ARG PIP_INDEX_URL

RUN python -m pip install --upgrade pip &&  \
    pip install setuptools && \
    pip install wheel && \
    pip install conan cmake

ADD requirements.txt requirements-dev.txt ci/docker/python/shared/requirements-ci.txt ci/docker/python/shared/requirements-extra.txt /tmp/
RUN pip wheel --wheel-dir=/wheels --no-cache-dir \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
        -r /tmp/requirements-ci.txt && \
    pip wheel --wheel-dir=/wheels -r /tmp/requirements-extra.txt && \
    rm -rf  /root/.cache

FROM python:${PYTHON_VERSION}
ARG USER_ID=1000
ARG GROUP_ID=1000

RUN if id $USER_ID ; then \
        echo 'Existing user id found: Creating an alias' ;\
        groupadd --non-unique --gid $GROUP_ID user ; \
        useradd  --non-unique --uid $USER_ID -s /bin/sh -m -d /home/user -g user user  ; \
    else \
        groupadd -g $GROUP_ID user ; \
        useradd  -u $USER_ID -s /bin/sh -m -d /home/user -g user user ;\
    fi && \
    mkdir -p /.cache/pip && chown -R user /.cache/pip


RUN apt-get update && apt-get install -y tzdata \
    && ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime \
    && dpkg-reconfigure --frontend noninteractive tzdata

RUN apt-get install -y libgl1-mesa-glx \
                       locales \
                       locales-all \
                       latexmk \
                       texlive-formats-extra \
                       xvfb \
                       libxkbcommon-x11-0

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
COPY --from=wheel_builder /wheels /wheels/
COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt /tmp/

RUN  python -m pip install --upgrade pip && \
    pip install --no-index --find-links=/wheels \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
        -r /tmp/requirements-ci.txt

ENV PIP_FIND_LINKS=/wheels
USER user
WORKDIR /home/user

ENV SONAR_SCANNER_VERSION=4.4.0.2170
ENV SONAR_SCANNER_HOME=/home/user/.sonar/sonar-scanner-$SONAR_SCANNER_VERSION-linux
RUN curl --create-dirs -sSLo $HOME/.sonar/sonar-scanner.zip \
        https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-$SONAR_SCANNER_VERSION-linux.zip && \
    unzip -o $HOME/.sonar/sonar-scanner.zip -d $HOME/.sonar/ && \
    rm $HOME/.sonar/sonar-scanner.zip && \
    mkdir -p /home/user/.sonar/cache && \
    chown user:user /home/user/.sonar/cache
ENV PATH=$SONAR_SCANNER_HOME/bin:$PATH
ENV SONAR_SCANNER_OPTS="-server"
USER root
RUN pip install pytest-qt