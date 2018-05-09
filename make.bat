@echo off

for /f "tokens=1,* delims= " %%a in ("%*") do set EXTRA_ARGS=%%b

if [%1] == []                call:main                  && goto:eof
if "%~1" == "build"          call:build                 && goto:eof
if "%~1" == "gui"            call:gui                   && goto:eof
if "%~1" == "sdist"          call:sdist                 && goto:eof
if "%~1" == "wheel"          call:wheel                 && goto:eof
if "%~1" == "standalone"     call:standalone            && goto:eof
if "%~1" == "docs"           call:docs %EXTRA_ARGS%     && goto:eof
if "%~1" == "clean"          call:clean                 && goto:eof
if "%~1" == "test"           call:test                  && goto:eof
if "%~1" == "test-mypy"      call:mypy %EXTRA_ARGS%     && goto:eof
if "%~1" == "venv"           call:venv                  && goto:eof
if "%~1" == "venvclean"      call:venvclean             && goto:eof
if "%~1" == "help"           call:help                  && goto:eof
if not %ERRORLEVEL% == 0 exit /b %ERRORLEVEL%
goto :error %*

EXIT /B 0

::=============================================================================
:: Display help information about available options
::=============================================================================
:help
    echo Available options:
    echo    make build              Creates a build in the build directory
    echo    make sdist              Build a Python source distribution
    echo    make wheel              Build a Python built distribution wheel
    echo    make standalone         Build a standalone distribution
    echo    make docs               Generates html documentation into the docs/build/html directory
    echo    make clean              Removes generated files
    echo    make test               Runs tests
    echo    make test-mypy          Runs MyPy tests
    echo    make venv               Creates a virtualenv with development requirements
    echo    make venvclean          Removes the generated virtualenv
goto:eof


::=============================================================================
:: Default target if no options are selected
::=============================================================================
:main
    call:_venv
    call:_install-required-deps
    call:_install-dev
    call:_update_gui
    call:_build
    call:_sdist
    call:_wheel
    call:_docs --build-dir dist/docs
goto:eof


::=============================================================================
:: Install runtime requirements
::=============================================================================
:_install-required-deps
    setlocal
    echo Syncing runtime dependencies
    call venv\Scripts\activate.bat && pip install -r requirements.txt
    endlocal
goto:eof

::=============================================================================
:: Install development requirements
::=============================================================================

:install-dev
    call:_venv
    call:_install-required-deps
    call:_install-dev
goto:eof


:_install-dev
    setlocal
    echo Syncing development dependencies
    call venv\Scripts\activate.bat && pip install -r requirements-dev.txt
    endlocal
goto:eof


::=============================================================================
:: Build a virtualenv sandbox for development
::=============================================================================
:venv
    if not exist "venv" call:_venv
    call :_install-required-deps
    call:_install-dev
goto:eof

:_venv
    if exist "venv" echo Found Python virtualenv && goto:eof

    echo Creating a local virtualenv in %CD%\venv
    setlocal
    REM Create a new virtualenv in the venv path
    py -m venv venv
    endlocal
goto:eof

::=============================================================================
:: Remove virtualenv sandbox
::=============================================================================
:venvclean
    if exist "venv" echo removing venv & RD /S /Q venv
goto:eof


::=============================================================================
:: Build the target
::=============================================================================
:build
    call:_venv
    call:_install-required-deps
    call:_install-dev
    call:_update_gui
    call:_build
goto:eof

:_build
    setlocal
    call venv\Scripts\activate.bat && python setup.py --quiet build
    endlocal
goto:eof

::=============================================================================
:: Generate Python GUI files from Qt .ui file located in the ui directory
::=============================================================================
:gui
    call:_install-dev
    call:_update_gui
goto:eof

:_update_gui
    setlocal
    call venv\Scripts\activate.bat && python setup.py --quiet build_ui
    endlocal
goto:eof


::=============================================================================
:: Create a wheel distribution
::=============================================================================
:wheel
    call:_venv
    call:_install-required-deps
    call:_install-dev
    call:_wheel

goto:eof

:_wheel
    echo Creating a Wheel distribution
    setlocal
    call venv\Scripts\activate.bat && python setup.py --quiet bdist_wheel
    endlocal
goto:eof

::=============================================================================
:: Create a source distribution
::=============================================================================
:sdist
    call:_venv
    call:_install-required-deps
    call:_install-dev
    call:_update_gui
    call:_sdist

goto:eof

:_sdist
    echo Creating a source distribution
    setlocal
    call venv\Scripts\activate.bat && python setup.py --quiet sdist
    endlocal
goto:eof

::=============================================================================
:: Create a standalone distribution
::=============================================================================
:standalone
    call:_venv
    call:_install-required-deps
    call:_install-dev
    REM call:_update_gui
    REM call:_build
    echo Creating a standalone distribution
    setlocal
    call venv\Scripts\activate.bat
    call windows_build\build_release.bat
    endlocal
goto:eof

::=============================================================================
:: Run unit tests
::=============================================================================
:test
    call:_venv
    call:_install-required-deps
    call:_install-dev
    call:_update_gui
    setlocal
    call venv\Scripts\activate.bat && python setup.py test && python -m behave
    endlocal
goto:eof


::=============================================================================
:: Test code with mypy
::=============================================================================
:mypy
    call:_venv
    call:_install-required-deps
    call:_install-dev
    call:_update_gui
    setlocal
    call venv\Scripts\activate.bat && mypy -p speedwagon %*
    endlocal
goto:eof


::=============================================================================
:: Build html documentation
::=============================================================================
:docs
    call:_venv
    call:_install-dev
    call:_build
    call:_docs %*
goto:eof

:_docs
    echo Creating docs
    setlocal
    call venv\Scripts\activate.bat && python setup.py build_sphinx %*
    endlocal
goto:eof

::=============================================================================
:: Clean up any generated files
::=============================================================================
:clean
    setlocal
	call venv\Scripts\activate.bat

	echo Calling setup.py clean
	python setup.py clean --all

    call windows_build/clean_release.bat

	echo Cleaning docs
	call docs\make.bat clean



	if exist .cache rd /q /s .cache                     && echo Removed .cache
	if exist .pytest_cache rd /q /s .pytest_cache       && echo Removed .pytest_cache
	if exist .reports rd /q /s .reports                 && echo Removed .reports
	if exist reports rd /q /s reports                   && echo Removed  reports
	if exist .mypy_cache rd /q /s .mypy_cache           && echo Removed .mypy_cache
	if exist .eggs rd /q /s .eggs                       && echo Removed .eggs
	if exist .tox rd /q /s .tox                         && echo Removed .tox
	if exist speedwagon.egg-info rd /q /s speedwagon.egg-info && echo Removed speedwagon.egg-info
	endlocal
goto:eof


::=============================================================================
:: If user request an invalid target
::=============================================================================
:error
    echo Unknown option: %*
    call :help
goto:eof
