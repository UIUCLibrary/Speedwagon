# escape=`
ARG PYTHON_DOCKER_IMAGE_BASE=python:3.7
FROM ${PYTHON_DOCKER_IMAGE_BASE}
RUN certutil -generateSSTFromWU roots.sst ; `
    certutil -addstore -f root roots.sst ; `
    del roots.sst
RUN python -m pip install --upgrade pip ; pip install devpi-client "tox<3.7"

ENV TMP=c:\temp `
    TMPDIR=c:\temp `
    TEMP=c:\temp
