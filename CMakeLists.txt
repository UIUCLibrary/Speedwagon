cmake_minimum_required(VERSION 3.11)
PROJECT(speedwagon LANGUAGES NONE)
find_package(PythonInterp REQUIRED)
message(STATUS "Using Python ${PYTHON_VERSION_STRING} located at \"${PYTHON_EXECUTABLE}\".")

macro(create_virtual_env)
    execute_process(COMMAND ${PYTHON_EXECUTABLE} -m venv ${PROJECT_BINARY_DIR}/venv)
    find_program(VENV_PYTHON 
        NAMES python
        PATHS 
            ${PROJECT_BINARY_DIR}/venv/Scripts/
            ${PROJECT_BINARY_DIR}/venv/bin/
        NO_DEFAULT_PATH 
    )
    if(VENV_PYTHON)
        execute_process(COMMAND ${VENV_PYTHON} -m pip install --upgrade setuptools)
        set(VENV_PYTHON ${VENV_PYTHON} CACHE BOOL "Python Virtual environment for building.")
    endif(VENV_PYTHON)
    
    # set()
endmacro()

function(install_venv_deps python_exe requirements_files)
    # TODO: make requirements_files a list so that multiple files can installed at the same time
    execute_process(COMMAND ${python_exe} -m pip install -r ${requirements_files})
endfunction(install_venv_deps)

create_virtual_env()
install_venv_deps(${VENV_PYTHON} ${PROJECT_SOURCE_DIR}/requirements.txt)
install_venv_deps(${VENV_PYTHON} ${PROJECT_SOURCE_DIR}/requirements-dev.txt)

message(STATUS "VENV_PYTHON = ${VENV_PYTHON}")
add_custom_target(wheel 
    COMMAND ${VENV_PYTHON} setup.py build_py --no-compile
    COMMAND ${VENV_PYTHON} setup.py bdist_wheel --bdist-dir ${PROJECT_BINARY_DIR}/python_build --dist-dir ${PROJECT_BINARY_DIR}
    WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
    )



# add_custom_target(venv )