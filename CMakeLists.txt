cmake_minimum_required(VERSION 3.11)
project(speedwagon LANGUAGES NONE
    VERSION 0.0.0)

find_package(PythonInterp REQUIRED)
message(STATUS "Using Python ${PYTHON_VERSION_STRING} located at \"${PYTHON_EXECUTABLE}\".")

set(speedwagon_PythonDepsCache ${PROJECT_BINARY_DIR}/deps CACHE PATH "location to put Python deps")
set(speedwagon_venv_path ${PROJECT_BINARY_DIR}/venv CACHE PATH "Location for Python virtual environment needed for building")

function(get_python_version SETUP_PY)
    cmake_parse_arguments(PYTHON "" "VERSION;MAJOR;MINOR;PATCH" "" ${ARGN})

    execute_process(
        COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} --version
        OUTPUT_VARIABLE PYTHON_PACKAGE_VERSION
        WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
        )
        string(STRIP ${PYTHON_PACKAGE_VERSION} PYTHON_PACKAGE_VERSION)
    if(NOT PYTHON_PACKAGE_VERSION MATCHES "^[0-9]\\.[0-9]\\.[0-9](a|b|r)?$")
            message(WARNING "Unable to extract version information from the Python project")
        else()
            set(${PYTHON_VERSION} ${PYTHON_PACKAGE_VERSION} PARENT_SCOPE)
            string(REGEX MATCHALL "([0-9])" PYTHON_PACKAGE_VERSION ${PYTHON_PACKAGE_VERSION})
            list(LENGTH PYTHON_PACKAGE_VERSION PYTHON_PACKAGE_VERSION_parse_size)

            if(NOT ${PYTHON_PACKAGE_VERSION_parse_size} EQUAL 3)
                message(FATAL_ERROR "Unable to parse python version string ${PYTHON_PACKAGE_VERSION}")
            else()
                list(GET PYTHON_PACKAGE_VERSION 0 py_major)
                list(GET PYTHON_PACKAGE_VERSION 1 py_minor)
                list(GET PYTHON_PACKAGE_VERSION 2 py_patch)
                set(${PYTHON_MAJOR} ${py_major} PARENT_SCOPE)
                set(${PYTHON_MINOR} ${py_minor} PARENT_SCOPE)
                set(${PYTHON_PATH} ${py_patch} PARENT_SCOPE)
            endif()

    endif()
endfunction(get_python_version)

macro(create_virtual_env)
    execute_process(COMMAND ${PYTHON_EXECUTABLE} -m venv ${speedwagon_venv_path})
    find_program(VENV_PYTHON 
        NAMES python
        PATHS 
            ${speedwagon_venv_path}/Scripts/
            ${speedwagon_venv_path}/bin/
        NO_DEFAULT_PATH 
    )
    mark_as_advanced(VENV_PYTHON)
    if(VENV_PYTHON)
        execute_process(COMMAND ${VENV_PYTHON} -m pip install --upgrade setuptools)
        set(VENV_PYTHON ${VENV_PYTHON} CACHE BOOL "Python Virtual environment for building.")
    endif(VENV_PYTHON)
    
    # set()
endmacro()

function(install_venv_deps)
    cmake_parse_arguments(VENV "" "PYTHON_EXE" "REQUIREMENTS_FILES" ${ARGN})

    foreach(requirements_file ${VENV_REQUIREMENTS_FILES})
        list(APPEND requirement_file_args "-r")
        list(APPEND requirement_file_args "${requirements_file}")
    endforeach()
    message(STATUS "running: ${VENV_PYTHON_EXE} -m pip install ${requirement_file_args} --upgrade-strategy only-if-needed")
    execute_process(COMMAND ${VENV_PYTHON_EXE} -m pip install ${requirement_file_args} --upgrade-strategy only-if-needed)
    message(STATUS "FINISHED installing venv deps")
endfunction(install_venv_deps)

function(create_dep_wheels)
    cmake_parse_arguments(VENV "" "PYTHON_EXE" "REQUIREMENTS_FILES" ${ARGN})

    foreach(requirements_file ${VENV_REQUIREMENTS_FILES})
        list(APPEND requirement_file_args "-r")
        list(APPEND requirement_file_args "${requirements_file}")
    endforeach()

    execute_process(COMMAND ${VENV_PYTHON_EXE} -m pip wheel ${requirement_file_args} --wheel-dir ${speedwagon_PythonDepsCache})
endfunction(create_dep_wheels)

# Set project Version number based on the metadata

get_python_version(
    ${PROJECT_SOURCE_DIR}/setup.py
    MAJOR PROJECT_VERSION_MAJOR
    MINOR PROJECT_VERSION_MINOR
    PATCH PROJECT_VERSION_PATCH
    VERSION PROJECT_VERSION
    )
get_python_version(
    ${PROJECT_SOURCE_DIR}/setup.py
    MAJOR ${PROJECT_NAME}_VERSION_MAJOR
    MINOR ${PROJECT_NAME}_VERSION_MINOR
    PATCH {PROJECT_NAME}_VERSION_PATCH
    VERSION {PROJECT_NAME}_VERSION
    )

create_virtual_env()
execute_process(COMMAND ${VENV_PYTHON} -m pip install wheel)
create_dep_wheels(
    PYTHON_EXE ${VENV_PYTHON}
    REQUIREMENTS_FILES
        ${PROJECT_SOURCE_DIR}/requirements.txt
        ${PROJECT_SOURCE_DIR}/requirements-dev.txt
    )

install_venv_deps(
    PYTHON_EXE ${VENV_PYTHON}
    REQUIREMENTS_FILES
        ${PROJECT_SOURCE_DIR}/requirements-dev.txt
        ${PROJECT_SOURCE_DIR}/requirements.txt
)

add_custom_target(wheel
   DEPENDS ${PROJECT_BINARY_DIR}/speedwagon-${PROJECT_VERSION}-py3-none-any.whl
    )

add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/speedwagon-${PROJECT_VERSION}-py3-none-any.whl
    COMMAND ${VENV_PYTHON} setup.py build_py --no-compile
    COMMAND ${VENV_PYTHON} setup.py bdist_wheel --bdist-dir ${PROJECT_BINARY_DIR}/python_build --dist-dir ${PROJECT_BINARY_DIR}
    WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
    MAIN_DEPENDENCY setup.py
)


# add_custom_target(venv )