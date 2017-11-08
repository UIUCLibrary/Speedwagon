setlocal

REM Run with the x64 environment
set "VSCMD_START_DIR=%CD%"
call "%vs140comntools%..\..\VC\vcvarsall.bat" x86_amd64

REM Call clean on MSBuild targets
MSBuild /nologo windows_build\release.pyproj /t:Clean /p:ProjectRoot=%CD%

REM Delete any nugetpackages used to build a standalone release
if exist "build\nugetpackages" (
        echo Deleting local nuget packages
        rmdir /s /q build\nugetpackages
    )

endlocal