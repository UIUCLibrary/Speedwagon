FROM mcr.microsoft.com/windows/servercore:1709
WORKDIR c:/scripts
RUN mkdir c:\\temp
ADD *.msi c:/scripts/
ADD run_install.ps1 c:/scripts/
CMD ["powershell.exe", "-executionpolicy", "bypass", "-file", "c:/scripts/run_install.ps1"]
