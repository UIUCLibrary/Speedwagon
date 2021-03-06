# escape=`
ARG FROM_IMAGE=mcr.microsoft.com/dotnet/framework/sdk:4.8
FROM ${FROM_IMAGE}
SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop';"]
# First install Visual Studio Build Tools
ADD ci/docker/windows_standalone/startup.bat c:\startup\startup.bat
RUN Invoke-WebRequest https://aka.ms/vs/16/release/vs_buildtools.exe -OutFile ${Env:TEMP}\\vs_buildtools.exe ; `
    Invoke-WebRequest https://aka.ms/vs/16/release/channel -OutFile ${Env:TEMP}\\VisualStudio.chman ; `
    Invoke-WebRequest https://aka.ms/vscollect.exe  -OutFile ${Env:TEMP}\\collect.exe ; `
    Write-Host 'Installing Visual Studio Build Tools' ; `
    $process = Start-Process -NoNewWindow -PassThru -FilePath $Env:TEMP\\vs_buildtools.exe -ArgumentList '--quiet  --installPath "C:\\BuildTools"  --wait --norestart --nocache --add Microsoft.VisualStudio.Component.Windows10SDK.18362' -Wait  ; `
    if ( $process.ExitCode -eq 0) `
    { `
        Write-Host 'Installing Visual Studio Build Tools - Done' ; `
    } `
    else `
    { `
        throw \"Installing Visual Studio Build Tools exited with code $($process.ExitCode)\" ;  `
    };`
    Write-Host "Testing for VsDevCmd.bat" ; `
    if (! (Test-Path 'C:\BuildTools\Common7\Tools\VsDevCmd.bat')) `
    { `
        Start-Process -NoNewWindow -FilePath $Env:TEMP\\collect.exe -ArgumentList '-nologo -zip:${Env:TEMP}\\vslogs.zip' -Wait; `
        Expand-Archive -Path vslogs.zip -DestinationPath $Env:TEMP\\logs\\ ; `
        Get-Content -LiteralPath '$Env:TEMP\\logs\\[Content_Types].xml' ; `
        throw 'VsDevCmd.bat not found' ; `
    } ; `
    Write-Host "Testing for VsDevCmd.bat - Found" ; `
    Write-Host "Adding VsDevCmd.bat to cmd.exe startup" ; `
    Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Command Processor' -Name 'AutoRun' -Value "c:\startup\startup.bat" ; `
    Write-Host "Adding VsDevCmd.bat to cmd.exe startup - Done" ; `
    Write-Host "Cleaning up $Env:TEMP" ; `
    Remove-Item -Force -Recurse $Env:TEMP\* ; `
    Write-Host "Cleaning up $Env:TEMP - Done" ; `
    Write-Host 'Visual Studio Build Tools installed!'

ARG CHOCOLATEY_SOURCE=https://chocolatey.org/api/v2
ARG ChocolateyEnvironmentDebug=false
ADD ci/docker/windows_standalone/install_choco.ps1 choco/install_choco.ps1
RUN Set-ExecutionPolicy Bypass -Scope Process -Force; `
    ./choco/install_choco.ps1 -packageRepo $env:CHOCOLATEY_SOURCE ; `
    choco feature enable --name="useEnhancedExitCodes" ; `
    choco feature disable --name="showDownloadProgress" ; `
    if( -not ([string]::IsNullOrEmpty($Env:CHOCOLATEY_SOURCE ))) `
    { `
        Write-Host "Adding $env:CHOCOLATEY_SOURCE to chocolatey sources" ; `
        choco source add -n=CHOCOLATEY_SOURCE --priority=1 -s=\"$env:CHOCOLATEY_SOURCE\"; `
        choco source disable -n=chocolatey ;`
    }; `
    choco feature disable -n=showDownloadProgress ; `
    Remove-Item C:\ProgramData\chocolatey\bin\cpack.exe ; `
    Remove-Item -Force -Recurse ${Env:TEMP}\*


# Install packages that can be installed by chocolatey
ADD ci/docker/windows_standalone/chocolatey/packages.config choco/packages.config

RUN C:\ProgramData\chocolatey\bin\choco.exe sources ; `
    Write-Host "Installing packages with Chocolatey" ; `
    $process = start-process -NoNewWindow -PassThru -FilePath C:\ProgramData\chocolatey\bin\choco.exe -ArgumentList 'install -y --stoponfirstfailure --no-progress choco/packages.config' -Wait ;`
    if ( $process.ExitCode -eq 0) `
    { `
        Write-Host "Installing packages with Chocolatey - Done" ; `
    } else { `
        throw "Installing packages with Chocolatey - Failed with exit code ($process.ExitCode)" ;  `
    };`
    Remove-Item C:\Users\ContainerAdministrator\AppData\Local\Temp\chocolatey -Recurse ; `
    Remove-Item -Force -Recurse ${Env:TEMP}\* ; `
    if (!(Test-Path 'C:\Program Files\Git\cmd\git.exe')) `
    { `
        throw 'git.exe not found' ; `
    }; `
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

ENV PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release"
ENV PIP_TRUSTED_HOST="devpi.library.illinois.edu"

RUN python -m pip install --upgrade pip ; `
    pip install wheel ; `
    pip install --upgrade setuptools


ADD requirements.txt requirements-dev.txt c:\temp\
RUN python -m pip wheel -r c:\temp\requirements.txt -r c:\temp\requirements-dev.txt --wheel-dir c:\wheels

RUN pip install --no-index --find-links=c:\wheels\ `
        --trusted-host devpi.library.illinois.edu `
        -r c:\temp\requirements.txt `
        -r c:\temp\requirements-dev.txt

ENV PIP_FIND_LINKS=c:\wheels\
COPY ci/docker/windows_standalone/build_standalone.ps1 c:\scripts\build_standalone.ps1
CMD c:\scripts\build_standalone.ps1
#SHELL ["cmd", "/S", "/C"]
