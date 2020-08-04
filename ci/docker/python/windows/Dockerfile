# escape=`
ARG PYTHON_VERSION=3.7
FROM python:${PYTHON_VERSION} as certsgen
RUN certutil -generateSSTFromWU roots.sst

FROM python:${PYTHON_VERSION} as wheel_maker
ARG PIP_EXTRA_INDEX_URL
ARG PIP_TRUSTED_HOST
ARG PIP_INDEX_URL
RUN python -m pip install pip --upgrade ;`
    pip install setuptools --upgrade ; `
    pip install wheel

COPY requirements.txt requirements-dev.txt ci/docker/python/shared/requirements-ci.txt ci/docker/python/shared/requirements-extra.txt c:/temp/

RUN pip wheel --wheel-dir c:\wheels `
        -r c:\temp\requirements.txt `
        -r c:\temp\requirements-dev.txt ; `
    pip wheel --wheel-dir c:\wheels `
        -r c:\temp\requirements-ci.txt ; `
    pip wheel --wheel-dir c:\wheels `
        -r c:\temp\requirements-extra.txt

FROM python:${PYTHON_VERSION}
COPY --from=certsgen c:/roots.sst roots.sst
RUN certutil -addstore -f root roots.sst ; `
    del roots.sst

RUN python -m pip install pip --upgrade ; `
    pip install setuptools --upgrade

COPY --from=wheel_maker c:\wheels\ c:\wheels\

COPY requirements.txt requirements-dev.txt ci/docker/python/shared/requirements-ci.txt c:/temp/

RUN pip install --no-index --find-links c:\wheels `
    -r c:\temp\requirements.txt `
    -r c:\temp\requirements-dev.txt `
    -r c:\temp\requirements-ci.txt
ENV PIP_FIND_LINKS=c:\wheels
