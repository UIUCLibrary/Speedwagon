setlocal

REM Run with the x64 environment
call venv\Scripts\activate.bat

set "VSCMD_START_DIR=%CD%"
call "%vs140comntools%..\..\VC\vcvarsall.bat" x86_amd64

REM install required Nuget packages
nuget install windows_build\packages.config -OutputDirectory build\nugetpackages

REM Run the MSBuild script for creating the msi
MSBuild windows_build\release.pyproj /nologo /t:msi /p:ProjectRoot=%CD%

endlocal