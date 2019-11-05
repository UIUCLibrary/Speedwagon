FROM mcr.microsoft.com/windows/servercore:ltsc2019
WORKDIR c:/scripts

RUN mkdir c:\\temp

ADD ./dist/ c:/dist/
ADD ci/docker/test_installation/run_install.ps1 c:/scripts/
RUN powershell -noexit "& ""c:\scripts\run_install.ps1"""
