# escape=`
ARG PYTHON_VERSION=3.7
FROM python:${PYTHON_VERSION} as certsgen
RUN certutil -generateSSTFromWU roots.sst

#FROM python:${PYTHON_VERSION} as deplocker
#COPY --from=certsgen c:/roots.sst roots.sst
#RUN certutil -addstore -f root roots.sst ; `
#    del roots.sst
#
#RUN python -m pip install pip --upgrade ; `
#    pip install pipenv
#
#ENV PIPENV_NOSPIN=True
#ADD Pipfile Pipfile.lock c:\temp\
#RUN cd c:\temp\ ; pipenv lock --requirements > requirements.txt ; pipenv lock --dev --requirements > requirements-dev.txt

FROM python:${PYTHON_VERSION} as wheel_maker
COPY requirements.txt requirements-dev.txt c:/temp/
RUN python -m pip install pip --upgrade ;`
    pip install setuptools --upgrade ; `
    pip install wheel
RUN python -m pip wheel --wheel-dir c:\wheels `
    --extra-index-url https://devpi.library.illinois.edu/production/release `
    -r c:\temp\requirements.txt `
    -r c:\temp\requirements-dev.txt

FROM python:${PYTHON_VERSION}
COPY --from=certsgen c:/roots.sst roots.sst
RUN certutil -addstore -f root roots.sst ; `
    del roots.sst

RUN python -m pip install pip --upgrade ; `
    pip install setuptools --upgrade

ENV PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release"
ENV PIP_TRUSTED_HOST="devpi.library.illinois.edu"

COPY --from=wheel_maker c:\wheels\ c:\wheels\

COPY requirements.txt requirements-dev.txt c:/temp/

RUN pip install --no-index --find-links c:\wheels `
    -r c:\temp\requirements.txt `
    -r c:\temp\requirements-dev.txt

#ENV PIPENV_CACHE_DIR=c:\pipenv_cache `
#    WORKON_HOME=c:\venvs
ENV PIP_EXTRA_INDEX_URL https://devpi.library.illinois.edu/production/release
#    --trusted-host devpi.library.illinois.edu `