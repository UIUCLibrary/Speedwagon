# escape=`
FROM mcr.microsoft.com/dotnet/framework/sdk:4.8-windowsservercore-ltsc2019
#FROM mcr.microsoft.com/windows/servercore:ltsc2019 as choco_builder
SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop';"]

ADD ci/docker/shared/chocolatey/install_choco.ps1 choco/install_choco.ps1
ARG CHOCOLATEY_SOURCE=https://chocolatey.org/api/v2
ARG ChocolateyEnvironmentDebug=false
RUN Set-ExecutionPolicy Bypass -Scope Process -Force; `
    ./choco/install_choco.ps1 ; `
    if( -not ([string]::IsNullOrEmpty($Env:CHOCOLATEY_SOURCE ))) `
    { `
        Write-Host "Adding $env:CHOCOLATEY_SOURCE to chocolatey sources" ; `
        choco source add -n=CHOCOLATEY_SOURCE --priority=1 -s=\"$env:CHOCOLATEY_SOURCE\" ; `
    }

COPY ci/docker/chocolatey_package/choco_package_template/pythonscript/ C:/ProgramData/chocolatey/templates/pythonscript/
#===============================
