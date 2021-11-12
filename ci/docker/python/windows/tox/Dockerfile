# escape=`

ARG PYTHON_36_VERSION=3.6.8
ARG PYTHON_37_VERSION=3.7.9
ARG PYTHON_38_VERSION=3.8.10
ARG PYTHON_39_VERSION=3.9.7
ARG PYTHON_310_VERSION=3.10.0

ARG FROM_IMAGE=mcr.microsoft.com/dotnet/framework/sdk:4.8
FROM ${FROM_IMAGE} as certsgen
RUN certutil -generateSSTFromWU roots.sst

FROM ${FROM_IMAGE} as BASE_BUILDER

SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop';"]

ARG CHOCOLATEY_SOURCE=https://chocolatey.org/api/v2
ARG ChocolateyEnvironmentDebug=false
COPY ci/docker/shared/chocolatey/install_choco.ps1 choco/install_choco.ps1
RUN Set-ExecutionPolicy Bypass -Scope Process -Force; `
    ./choco/install_choco.ps1 ; `
    if( -not ([string]::IsNullOrEmpty($Env:CHOCOLATEY_SOURCE ))) `
    { `
        Write-Host "Adding $env:CHOCOLATEY_SOURCE to chocolatey sources" ; `
        choco source add -n=CHOCOLATEY_SOURCE --priority=1 -s=\"$env:CHOCOLATEY_SOURCE\"; `
        choco source remove -n=chocolatey ;`
    }; `
    Write-Host "Disabling Showing Download Progress" ; `
    choco feature disable -n=showDownloadProgress ; `
    Remove-Item C:\ProgramData\chocolatey\bin\cpack.exe ; `
    Remove-Item -Force -Recurse ${Env:TEMP}\*


ADD ci/docker/shared/chocolatey/packages.xml choco/packages.config
RUN C:\ProgramData\chocolatey\bin\choco.exe sources ; `
    C:\ProgramData\chocolatey\bin\choco.exe install -y --stoponfirstfailure --no-progress --verbose choco/packages.config ;`
    Remove-Item C:\Users\ContainerAdministrator\AppData\Local\Temp\chocolatey -Recurse ; `
    refreshenv ; `
    Remove-Item -Force -Recurse ${Env:TEMP}\* ; `
    if (!(Test-Path 'C:\Program Files\Git\cmd\git.exe')) `
    { `
        throw 'git.exe not found' ; `
    }; `
    Write-Host "Finished install packages with Chocolatey"

ARG PYTHON_36_VERSION
ARG PYTHON_37_VERSION
ARG PYTHON_38_VERSION
ARG PYTHON_39_VERSION
ARG PYTHON_310_VERSION

RUN $PYTHON_VERSIONS = @(${Env:PYTHON_36_VERSION}, ${Env:PYTHON_37_VERSION}, ${Env:PYTHON_38_VERSION}, ${Env:PYTHON_39_VERSION}, ${Env:PYTHON_310_VERSION}) ; `
    foreach( $PYTHON_VERSION in $PYTHON_VERSIONS ){ `
        Write-Host "Installing Python $PYTHON_VERSION with Chocolatey" ; `
        $process = start-process -NoNewWindow -PassThru -FilePath C:\ProgramData\chocolatey\bin\choco.exe -ArgumentList 'install -y --stoponfirstfailure --no-progress --verbose python3', "--version=$PYTHON_VERSION", "-my" -Wait ;`
        if ( $process.ExitCode -eq 0) `
        { `
            Write-Host "Installing Python $PYTHON_VERSION with Chocolatey - Done" ; `
        } else { `
            throw "Installing packages with Chocolatey - Failed with exit code ($process.ExitCode)" ;  `
        };`
    } ; `
    Remove-Item C:\Users\ContainerAdministrator\AppData\Local\Temp\chocolatey -Recurse ; `
    Remove-Item -Force -Recurse ${Env:TEMP}\* ; `
    py --list

# ==============================================================================
FROM BASE_BUILDER as WHEEL_BUILDER_PY36
SHELL ["cmd", "/S", "/C" ]
COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt c:/requirements/
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ENV PY_PYTHON=3.6
RUN py -m pip install --upgrade pip wheel && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements.txt -r c:/requirements/requirements-dev.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-vendor.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-extra.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-ci.txt
RUN py -m pip wheel -w c:\wheels\ --no-cache-dir -v devpi_client
RUN py -m pip list
# ==============================================================================
FROM BASE_BUILDER as WHEEL_BUILDER_PY37
SHELL ["cmd", "/S", "/C" ]
COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt c:/requirements/
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ENV PY_PYTHON=3.7
RUN py -m pip install --upgrade pip wheel && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements.txt -r c:/requirements/requirements-dev.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-vendor.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-extra.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-ci.txt
RUN py -m pip wheel -w c:\wheels\ --no-cache-dir -v devpi_client
RUN py -m pip list

# ==============================================================================
FROM BASE_BUILDER as WHEEL_BUILDER_PY38
SHELL ["cmd", "/S", "/C" ]
COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt c:/requirements/
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ENV PY_PYTHON=3.8
RUN py -m pip install --upgrade pip wheel && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements.txt -r c:/requirements/requirements-dev.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-vendor.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-extra.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-ci.txt
RUN py -m pip wheel -w c:\wheels\ --no-cache-dir -v devpi_client
RUN py -m pip list

# ==============================================================================

FROM BASE_BUILDER as WHEEL_BUILDER_PY39
SHELL ["cmd", "/S", "/C" ]
COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt c:/requirements/
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ENV PY_PYTHON=3.9
RUN py -m pip install --upgrade pip wheel && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements.txt -r c:/requirements/requirements-dev.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-vendor.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-extra.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-ci.txt
RUN py -m pip wheel -w c:\wheels\ --no-cache-dir -v devpi_client
RUN py -m pip list
# ==============================================================================# ==============================================================================

FROM BASE_BUILDER as WHEEL_BUILDER_PY310
SHELL ["cmd", "/S", "/C" ]
COPY ci/docker/python/shared/requirements-ci.txt requirements.txt requirements-dev.txt requirements-vendor.txt ci/docker/python/shared/requirements-extra.txt c:/requirements/
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ENV PY_PYTHON=3.10
RUN py -m pip install --upgrade pip wheel && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements.txt -r c:/requirements/requirements-dev.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-vendor.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-extra.txt && `
    py -m pip wheel -w c:\wheels\ --no-cache-dir -r c:/requirements/requirements-ci.txt
RUN py -m pip wheel -w c:\wheels\ --no-cache-dir -v devpi_client
RUN py -m pip list
# ==============================================================================

#FROM BASE_BUILDER as CONAN_BUILDER
#ARG PIP_EXTRA_INDEX_URL
#ARG PIP_INDEX_URL
#RUN python -m pip install --upgrade pip ; `
#    pip install wheel ; `
#    pip install conan cmake
#COPY conanfile.py c:/temp/conanfile.py
#COPY ci/docker/shared/conan/remotes.json  C:/Users/ContainerAdministrator/.conan/remotes.json
#COPY ci/docker/python/windows/msvc/shared/profile.ini  C:/Users/ContainerAdministrator/.conan/profiles/default
#SHELL ["cmd", "/S", "/C" ]
#RUN conan config home
#RUN conan install c:/temp/ --build missing --build openjpeg --no-import  && `
#    conan remove "*" -b --src -f && `
#    conan remove --lock
## ==============================================================================
#
FROM BASE_BUILDER
COPY --from=certsgen c:/roots.sst roots.sst
RUN certutil -addstore -f root roots.sst ; `
    del roots.sst
#
#RUN python -m pip install pip --upgrade ; `
#    pip install wheel ; `
#    pip install conan
#
#COPY --from=CONAN_BUILDER C:/Users/ContainerAdministrator/.conan/ C:/Users/ContainerAdministrator/.conan/
#ENV CONAN_USER_HOME=C:/Users/ContainerAdministrator
#COPY conanfile.py c:/temp/conanfile.py
#RUN conan config home
#RUN conan install c:/temp/ --build outdated --no-import  ; `
#    conan remove "*" -b --src -f ; `
#    conan remove --locks
SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop';"]
COPY --from=WHEEL_BUILDER_PY36 c:/wheels/ c:/wheels/
COPY --from=WHEEL_BUILDER_PY37 c:/wheels/ c:/wheels/
COPY --from=WHEEL_BUILDER_PY38 c:/wheels/ c:/wheels/
COPY --from=WHEEL_BUILDER_PY39 c:/wheels/ c:/wheels/
COPY --from=WHEEL_BUILDER_PY310 c:/wheels/ c:/wheels/

ENV PIP_FIND_LINKS=c:\wheels

RUN python -m pip install pip --upgrade ; `
    pip install wheel ; `
    pip wheel -w c:\wheels wheel ; `
    pip install --no-index --find-links=c:\wheels tox devpi_client
WORKDIR C:/src
CMD tox --workdir ${Env:TEMP}\tox\ -vv  --recreate -p=auto