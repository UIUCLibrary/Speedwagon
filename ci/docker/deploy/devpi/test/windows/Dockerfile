# escape=`
ARG CERTS_GENERATOR_IMAGE=mcr.microsoft.com/dotnet/framework/sdk:4.8
ARG PYTHON_DOCKER_IMAGE_BASE=python:3.7

FROM ${CERTS_GENERATOR_IMAGE} as certsgen
RUN certutil -generateSSTFromWU roots.sst

FROM ${PYTHON_DOCKER_IMAGE_BASE}
COPY --from=certsgen c:/roots.sst roots.sst
RUN certutil -addstore -f root roots.sst ; `
    del roots.sst

RUN python -m pip install --upgrade pip ; pip install devpi-client "tox<3.7"

ENV TMP=c:\temp `
    TMPDIR=c:\temp `
    TEMP=c:\temp
