# escape=`
FROM mcr.microsoft.com/windows/servercore:ltsc2019

RUN @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" `
    && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
ADD ci/docker/chocolatey/speedwagon/ C:/ProgramData/chocolatey/templates/speedwagon/
#ADD distrubution c:/distrubution/
#
#RUN cd distrubution/chocolatey/speedwagon && choco pack && choco chocolateyInstall.ps1 speedwagon -y -dv -s .
#RUN mkdir package `
#    && cd package `
#    && choco new speedwagon -t speedwagon packageversion=0.1.4 maintainername='"Henry Borchers"' packageSourceUrl='https://github.com/UIUCLibrary/Speedwagon' InstallerType='msi' InstallerFile='Speedwagon-0.1.4-win64.msi'
#
#ADD dist/*.msi c:/package/speedwagon/tools/
#RUN cd package\speedwagon && dir &&  choco pack
#RUN cd package\speedwagon\tools && dir
#RUN cd c:\package\speedwagon && dir && type speedwagon.nuspec
#RUN choco install speedwagon -y -dv -s c:\package
#RUN speedwagon --version
#RUN choco uninstall speedwagon -y
#RUN speedwagon --version && (exit 1) || (echo This should say is not recognized as an internal or external command && exit 0)
