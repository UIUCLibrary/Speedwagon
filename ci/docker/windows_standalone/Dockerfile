# escape=`
ARG FROM_IMAGE=mcr.microsoft.com/dotnet/framework/sdk:3.5
FROM ${FROM_IMAGE}

# Reset the shell.
SHELL ["cmd", "/S", "/C"]
RUN mkdir c:\\TEMP
#COPY Install.cmd C:/TEMP/
ADD https://aka.ms/vscollect.exe C:/TEMP/collect.exe

# Download channel for fixed install.
ARG CHANNEL_URL=https://aka.ms/vs/16/release/channel
ADD ${CHANNEL_URL} C:/TEMP/VisualStudio.chman

# Download and install Build Tools for Visual Studio 2017 for native desktop workload.

ADD https://aka.ms/vs/16/release/vs_buildtools.exe C:/TEMP/vs_buildtools.exe

RUN (C:\\TEMP\\vs_buildtools.exe `
    --quiet --wait --norestart --nocache `
    --channelUri C:\\TEMP\\VisualStudio.chman `
    --installChannelUri C:\\TEMP\\VisualStudio.chman `
    --add Microsoft.VisualStudio.Component.Windows10SDK.18362 `
    --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64	 `
    --includeRecommended `
    --installPath C:\BuildTools `
  || IF "%ERRORLEVEL%"=="3010" EXIT 0 )`
  && @echo Cleaning up temp files`
  && del /S /F /Q %temp% `
  && del /S /F /Q %Windir%\Temp `
  && @echo Done cleaning up files in temp directories

SHELL ["powershell", "-command"]
RUN Set-ExecutionPolicy Bypass -Scope Process -Force; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

ARG CHOCOLATEY_SOURCE=chocolatey
ADD ci/docker/windows_standalone/packages.config packages.config
RUN choco install -y --source=$env:CHOCOLATEY_SOURCE packages.config ; `
    Remove-Item C:\ProgramData\chocolatey\bin\cpack.exe ; `
    Remove-Item C:\Users\ContainerAdministrator\AppData\Local\Temp\chocolatey -Recurse

ARG PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.7.5/python-3.7.5-amd64.exe

RUN $ErrorActionPreference = 'Stop'; `
    Invoke-WebRequest $Env:PYTHON_INSTALLER_URL -OutFile c:\python-installer.exe ; `
    Start-Process python-installer.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; `
    Remove-Item c:\python-installer.exe -Force

RUN certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst

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
RUN REG ADD "HKLM\Software\Microsoft\Command Processor" /v AutoRun /t REG_SZ /d c:\startup\startup.bat
#ENTRYPOINT C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat -no_logo -arch=amd64 -host_arch=amd64 &&
#CMD ["powershell.exe", "-NoLogo", "-ExecutionPolicy", "Bypass"]
