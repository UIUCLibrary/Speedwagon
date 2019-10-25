# escape=`
ARG PYTHON_VERSION=3.7
FROM python:${PYTHON_VERSION}
RUN certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst
ADD requirements.txt requirements-dev.txt c:\temp\
RUN python -m pip install pip --upgrade ; `
        pip install --extra-index-url https://devpi.library.illinois.edu/production/release `
        --trusted-host devpi.library.illinois.edu `
        --no-cache-dir `
        -r c:\temp\requirements.txt `
        -r c:\temp\requirements-dev.txt `
        pipenv

ENV WORKON_HOME=c:\venvs
ENV PIPENV_CACHE_DIR=c:\pipenv_cache
ENV PIPENV_NOSPIN=True
ADD Pipfile Pipfile.lock c:\temp\
RUN cd c:\temp\ ; pipenv install --dev --extra-index-url https://devpi.library.illinois.edu/production/release --verbose