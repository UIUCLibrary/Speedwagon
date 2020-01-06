# escape=`
ARG PYTHON_VERSION=3.7
FROM python:${PYTHON_VERSION} AS builder
ADD requirements.txt requirements-dev.txt c:\temp\
RUN python -m pip install pip --upgrade ; `
        pip install --extra-index-url https://devpi.library.illinois.edu/production/release `
        --trusted-host devpi.library.illinois.edu `
        -r c:\temp\requirements.txt `
        -r c:\temp\requirements-dev.txt `
        pipenv `
        pylint

ADD Pipfile Pipfile.lock c:/temp/
RUN cd c:\temp\ ; pipenv install --dev ;  pipenv run pip freeze > requirements.txt; pipenv --rm

FROM python:${PYTHON_VERSION}
RUN certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst
COPY --from=builder c:/temp/requirements.txt requirements.txt
RUN pip install -r requirements.txt --extra-index-url https://devpi.library.illinois.edu/production/release