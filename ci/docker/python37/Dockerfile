# escape=`
ARG PYTHON_VERSION=3.7
FROM python:${PYTHON_VERSION} as certsgen
RUN certutil -generateSSTFromWU roots.sst

FROM python:${PYTHON_VERSION} as deplocker
COPY --from=certsgen c:/roots.sst roots.sst
RUN certutil -addstore -f root roots.sst ; `
    del roots.sst

RUN python -m pip install pip --upgrade ; `
    pip install pipenv

ENV PIPENV_NOSPIN=True
ADD Pipfile Pipfile.lock c:\temp\
RUN cd c:\temp\ ; pipenv lock --requirements > requirements.txt ; pipenv lock --dev --requirements > requirements-dev.txt

FROM python:${PYTHON_VERSION}
COPY --from=certsgen c:/roots.sst roots.sst
RUN certutil -addstore -f root roots.sst ; `
    del roots.sst

RUN python -m pip install pip --upgrade ; `
    pip install pipenv

ENV PIP_DOWNLOAD_CACHE=c:\pip_cache `
    PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release" `
    PIP_TRUSTED_HOST="devpi.library.illinois.edu"

COPY --from=deplocker c:\temp\requirements.txt c:\temp\requirements-dev.txt c:\temp\

RUN pip install --extra-index-url https://devpi.library.illinois.edu/production/release `
    --trusted-host devpi.library.illinois.edu `
    -r c:\temp\requirements.txt `
    -r c:\temp\requirements-dev.txt

ENV PIPENV_CACHE_DIR=c:\pipenv_cache `
    WORKON_HOME=c:\venvs
