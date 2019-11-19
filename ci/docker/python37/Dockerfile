# escape=`
ARG PYTHON_VERSION=3.7
FROM python:${PYTHON_VERSION}
RUN certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst
ENV PIP_DOWNLOAD_CACHE=c:\pip_cache `
    PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release" `
    PIP_TRUSTED_HOST="devpi.library.illinois.edu"

ADD requirements.txt requirements-dev.txt c:\temp\
RUN python -m pip install pip --upgrade ; `
        pip install --extra-index-url https://devpi.library.illinois.edu/production/release `
        --trusted-host devpi.library.illinois.edu `
        -r c:\temp\requirements.txt `
        -r c:\temp\requirements-dev.txt `
        pipenv `
        pylint

ENV PIPENV_CACHE_DIR=c:\pipenv_cache `
    WORKON_HOME=c:\venvs `
    PIPENV_NOSPIN=True

ADD Pipfile Pipfile.lock c:\temp\
RUN cd c:\temp\ ; pipenv install --dev --extra-index-url https://devpi.library.illinois.edu/production/release --verbose
