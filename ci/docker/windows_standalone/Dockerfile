# escape=`
ARG FROM_IMAGE=mcr.microsoft.com/dotnet/framework/sdk:4.8
FROM ${FROM_IMAGE}
SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop';"]

ARG CHOCOLATEY_REPO=https://chocolatey.org/api/v2

ARG ChocolateyEnvironmentDebug=false
ADD ci/docker/windows_standalone/install_choco.ps1 choco/install_choco.ps1
RUN Set-ExecutionPolicy Bypass -Scope Process -Force; ./choco/install_choco.ps1 -packageRepo $env:CHOCOLATEY_REPO ; `
    choco source remove -n chocolatey ; choco source add -n=chocolatey_repo -s=\"$env:CHOCOLATEY_REPO\" ; `
    Remove-Item C:\ProgramData\chocolatey\bin\cpack.exe

# Install packages that can be installed by chocolatey
ADD ci/docker/windows_standalone/chocolatey/packages.config choco/packages.config
RUN choco install -y choco/packages.config --no-progress --stoponfirstfailure;`
    Remove-Item C:\Users\ContainerAdministrator\AppData\Local\Temp\chocolatey -Recurse ; `
    Write-Host "Finished install packages with Chocolatey"

# Install WiX toolset for making .msi installers and put the tools on the path
ADD ci/docker/windows_standalone/nuget/packages.config nuget/packages.config
RUN Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force ; `
    nuget update -self ;`
    nuget install nuget/packages.config -OutputDirectory c:\BuildTools\ ; `
    [Environment]::SetEnvironmentVariable('PATH', \"$($env:Path);$((Get-Childitem -Path C:\BuildTools -Include wix.dll -File -Recurse)[0].DirectoryName)\", [EnvironmentVariableTarget]::Machine)

# Install python version from URL
ARG PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.7.5/python-3.7.5-amd64.exe

RUN $ErrorActionPreference = 'Stop'; `
    Invoke-WebRequest $Env:PYTHON_INSTALLER_URL -OutFile c:\python-installer.exe ; `
    Start-Process python-installer.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; `
    Remove-Item c:\python-installer.exe -Force

# install certs so additional pip packages can download without any trouble
#RUN certutil -config - -ping; certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst

ENV PIPENV_CACHE_DIR=c:\pipenv_cache `
    WORKON_HOME=c:\venvs `
    PIPENV_NOSPIN=True `
    PIP_DOWNLOAD_CACHE=c:\pip_cache `
    PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release" `
    PIP_TRUSTED_HOST="devpi.library.illinois.edu"

RUN python -m pip install --upgrade pip ; `
    pip install --upgrade setuptools

ADD requirements.txt requirements-dev.txt c:\temp\

RUN python -m pip install pip --upgrade ; `
        pip install --extra-index-url https://devpi.library.illinois.edu/production/release `
        --trusted-host devpi.library.illinois.edu `
        -r c:\temp\requirements.txt `
        -r c:\temp\requirements-dev.txt `
        pipenv `
        wheel

RUN python -m pip wheel -r c:\temp\requirements.txt -r c:\temp\requirements-dev.txt --wheel-dir c:\wheel_cache
ADD ci/docker/windows_standalone/startup.bat c:\startup\startup.bat

SHELL ["cmd", "/S", "/C"]

# Add script that runs on starting cmd that launches developer cli.
# This is important because Jenkins won't be able to run bat() with the needed
# tools on the path.
RUN REG ADD "HKLM\Software\Microsoft\Command Processor" /v AutoRun /t REG_SZ /d c:\startup\startup.bat
