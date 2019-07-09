FROM mcr.microsoft.com/windows/servercore:1709
WORKDIR c:/scripts
RUN mkdir c:\\temp
ADD ci/docker/windowsserver/run_install.ps1 c:/scripts/
CMD powershell.exe -Command "while (1) { Start-Sleep 30 }"
#CMD ["powershell.exe", "-executionpolicy", "bypass", "-file", "c:/scripts/run_install.ps1"]
