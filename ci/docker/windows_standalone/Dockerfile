# escape=`
ARG FROM_IMAGE=mcr.microsoft.com/dotnet/framework/sdk:4.8-windowsservercore-ltsc2019
FROM ${FROM_IMAGE}
SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop';"]
# First install Visual Studio Build Tools
RUN Invoke-WebRequest https://aka.ms/vs/17/release/vs_buildtools.exe -OutFile vs_buildtools.exe ;`
    $VS_INSTALL_PATH =  \"${Env:ProgramFiles(x86)}\" + '\Microsoft Visual Studio\2022\BuildTools' ; `
    Write-Host \"Installing Visual Studio Build Tools to ${VS_INSTALL_PATH}\" ; `
    $ARGS_LIST = @(`
        '--quiet', `
        '--wait', `
        '--norestart', `
        '--nocache', `
        \"--installPath ${VS_INSTALL_PATH}\",`
        '--add Microsoft.VisualStudio.Component.Windows10SDK.18362', `
        '--remove Microsoft.VisualStudio.Component.Windows10SDK.10240',`
        '--remove Microsoft.VisualStudio.Component.Windows10SDK.10586', `
        '--remove Microsoft.VisualStudio.Component.Windows10SDK.14393', `
        '--remove Microsoft.VisualStudio.Component.Windows81SDK'`
        ) ;`
    $process = Start-Process -NoNewWindow -PassThru -FilePath vs_buildtools.exe  `
    -ArgumentList $ARGS_LIST -Wait  ; `
    if ( $process.ExitCode -eq 0) `
    { `
        Write-Host 'Installing Visual Studio Build Tools - Done' ; `
    } `
    else `
    { `
        Get-ChildItem c:\\ ; `
        Get-ChildItem ${Env:ProgramFiles(x86)} ; `
        Get-ChildItem ${VS_INSTALL_PATH} ; `
        Get-ChildItem ${VS_INSTALL_PATH}\\Common7\\Tools ; `
        $message = \"Installing Visual Studio Build Tools exited with code $($process.ExitCode) \"; `
        Write-Host $message ;  `
        throw 'unable to continue' ; `
    } ; `
    Write-Host 'Testing for VsDevCmd.bat' ; `
    if (! (Test-Path 'c:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat')) `
    { `
        Write-Host 'Testing for VsDevCmd.bat - Failed' ; `
        Start-Process -NoNewWindow -FilePath $Env:TEMP\\collect.exe -ArgumentList '-nologo -zip:${Env:TEMP}\\vslogs.zip' -Wait; `
        if (! (Test-Path '${Env:TEMP}\\vslogs.zip')) `
        { `
            throw 'VsDevCmd.bat not found and ${Env:TEMP}\\vslogs.zip never generated' ; `
        } ; `
        Expand-Archive -Path vslogs.zip -DestinationPath $Env:TEMP\\logs\\ ; `
        Get-Content -LiteralPath '$Env:TEMP\\logs\\[Content_Types].xml' ; `
        throw 'VsDevCmd.bat not found' ; `
    } ; `
    Write-Host "Testing for VsDevCmd.bat - Found" ; `
    Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Command Processor' -Name 'AutoRun' -Value "c:\startup\startup.bat"
ADD ci/docker/windows_standalone/startup.bat c:/startup/startup.bat
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
    Remove-Item -Force -Recurse ${Env:TEMP}\*

ADD ci/docker/windows_standalone/chocolatey/python.xml choco/python.config
RUN C:\ProgramData\chocolatey\bin\choco.exe install -y --stoponfirstfailure --no-progress --verbose choco/python.config ;`
    Remove-Item C:\Users\ContainerAdministrator\AppData\Local\Temp\chocolatey -Recurse ; `
    refreshenv ; `
    Remove-Item -Force -Recurse ${Env:TEMP}\* ; `
    py --list ;`
    py -3.11 --version ; `
    Write-Host "Installing Python with Chocolatey - Done"

# Install packages that can be installed by chocolatey
ADD ci/docker/windows_standalone/chocolatey/packages.config choco/packages.config

RUN C:\ProgramData\chocolatey\bin\choco.exe sources ; `
    Write-Host "Installing packages with Chocolatey" ; `
    $process = start-process -NoNewWindow -PassThru -FilePath C:\ProgramData\chocolatey\bin\choco.exe -ArgumentList 'install -y --stoponfirstfailure --no-progress choco/packages.config' -Wait ;`
    if ( $process.ExitCode -eq 0) `
    { `
        Write-Host "Installing packages with Chocolatey - Done" ; `
    } else { `
        throw 'Installing packages with Chocolatey - Failed with none zero exit code' ;  `
    };`
    Remove-Item C:\Users\ContainerAdministrator\AppData\Local\Temp\chocolatey -Recurse ; `
    Remove-Item -Force -Recurse ${Env:TEMP}\* ; `
    if (!(Test-Path 'C:\Program Files\Git\cmd\git.exe')) `
    { `
        throw 'git.exe not found' ; `
    }; `
    Write-Host "Finished install packages with Chocolatey"

    # Install WiX toolset for making .msi installers and put the tools on the path
ARG NUGET_PACKAGE_PATH=c:/nuget_packages/
COPY ci/docker/windows_standalone/nuget/packages.config c:\temp\packages.config
COPY ci/docker/windows_standalone/nuget/verify_installed_correctly.ps1 c:\temp\verify_installed_correctly.ps1
RUN Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.208 -Force ;`
    Register-PackageSource -Name MyNuGet -Location https://www.nuget.org/api/v2 -ProviderName NuGet ;`
    nuget.exe install c:\temp\packages.config -OutputDirectory ${Env:NUGET_PACKAGE_PATH}; `
    $WIX_PATH ="$((Get-Childitem -Path ${Env:NUGET_PACKAGE_PATH} -Include wix.dll -File -Recurse)[0].DirectoryName)" ; `
    $env:Path += $WIX_PATH ; `
    [Environment]::SetEnvironmentVariable('Path', $env:Path, [EnvironmentVariableTarget]::Machine ) ;`
    Write-Host "Updated path to = $env:Path";`
    c:\temp\verify_installed_correctly.ps1
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ADD requirements.txt requirements-dev.txt c:\temp\
RUN python -m pip install --no-cache-dir --upgrade pip ; `
    pip install --no-cache-dir wheel ; `
    pip install --no-cache-dir --upgrade setuptools ;`
    pip install --no-cache-dir -r c:\temp\requirements-dev.txt

ENV PIP_FIND_LINKS=c:\wheels\
COPY ci/docker/windows_standalone/build_standalone.ps1 c:/scripts/build_standalone.ps1
CMD c:\scripts\build_standalone.ps1
