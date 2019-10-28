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

RUN @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" `
    && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

RUN choco install -y git nsis wixtoolset ninja`
    && choco install -y cmake --installargs 'ADD_CMAKE_TO_PATH=System' `
    && del /S /F /Q %ChocolateyInstall%

RUN powershell.exe -Command  `
    $ErrorActionPreference = 'Stop'; `
    Invoke-WebRequest https://www.python.org/ftp/python/3.7.5/python-3.7.5-amd64.exe -OutFile c:\python-3.7.5-amd64.exe ; `
    Start-Process python-3.7.5-amd64.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; `
    Remove-Item c:\python-3.7.5-amd64.exe -Force

RUN python -m pip install --upgrade pip `
    && pip install --upgrade setuptools
