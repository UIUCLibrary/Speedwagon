
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
                set(${PYTHON_PATCH} ${py_patch} PARENT_SCOPE)
            endif()

    endif()
endfunction(get_python_version)

macro(create_virtual_env)
    execute_process(COMMAND ${PYTHON_EXECUTABLE} -m venv ${SPEEDWAGON_VENV_PATH})
    find_program(VENV_PYTHON
        NAMES python
        PATHS
            ${SPEEDWAGON_VENV_PATH}/Scripts/
            ${SPEEDWAGON_VENV_PATH}/bin/
        NO_DEFAULT_PATH
    )
    mark_as_advanced(VENV_PYTHON)
    if(VENV_PYTHON)
        execute_process(COMMAND ${VENV_PYTHON} -m pip install --upgrade pip)
        execute_process(COMMAND ${VENV_PYTHON} -m pip install --upgrade setuptools wheel)
        set(VENV_PYTHON ${VENV_PYTHON} CACHE BOOL "Python Virtual environment for building.")
    endif(VENV_PYTHON)

    # set()
endmacro()

function(install_venv_deps)
    cmake_parse_arguments(VENV "" "PYTHON_EXE" "REQUIREMENTS_FILES" ${ARGN})
    message(STATUS "Installing Python dependencies to environment")

    foreach(requirements_file ${VENV_REQUIREMENTS_FILES})
        list(APPEND requirement_file_args "-r")
        list(APPEND requirement_file_args "${requirements_file}")
    endforeach()
    execute_process(COMMAND ${VENV_PYTHON_EXE} -m pip install ${requirement_file_args} --upgrade-strategy only-if-needed -f ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE})
    message(STATUS "Installing Python dependencies to environment done")
endfunction(install_venv_deps)

function(create_pth_configure_file)
    cmake_parse_arguments(CONFIG "" "SOURCE_PTH_FILE;OUTPUT" "PYTHON_PATHS" ${ARGN})
#    message(STATUS "CONFIG_OUTPUT: ${CONFIG_OUTPUT}")
#    message(STATUS "PYTHON_PATHS: ${CONFIG_PYTHON_PATHS}")
#    message(STATUS "CONFIG_SOURCE_PTH_FILE: ${CONFIG_SOURCE_PTH_FILE}")

    file(READ ${CONFIG_SOURCE_PTH_FILE} PYTHON_PTH_DATA)

    foreach(python_path ${CONFIG_PYTHON_PATHS})
        string(APPEND PYTHON_PTH_DATA "\n${python_path}")
    endforeach()

    string(APPEND PYTHON_PTH_DATA "\n")

    file(WRITE ${CONFIG_OUTPUT} ${PYTHON_PTH_DATA})

endfunction(create_pth_configure_file)


function(create_dep_wheels)
    cmake_parse_arguments(VENV "" "PYTHON_EXE" "REQUIREMENTS_FILES" ${ARGN})

    foreach(requirements_file ${VENV_REQUIREMENTS_FILES})
        # Create a hash of the requirements file and update cache if
        # the requirements file has changed
        file(SHA1 ${requirements_file} file_hash)
        if("${file_hash}" STREQUAL "${${requirements_file}_hash}")
            message(STATUS "No changed detected from ${requirements_file}")
            continue()
        else()
            set(${requirements_file}_hash ${file_hash} CACHE INTERNAL "SHA1 hash for ${requirements_file}")
        endif()
        list(APPEND requirement_file_args "-r")
        list(APPEND requirement_file_args "${requirements_file}")
    endforeach()

    if(requirement_file_args)
        message(STATUS "Syncing Python dependency .whl cache")
        execute_process(
            COMMAND ${VENV_PYTHON_EXE} -m pip wheel ${requirement_file_args} --wheel-dir ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE} -f ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
            )
        else()
            message(STATUS "Python dependency .whl cache already up to date")
    endif()
endfunction(create_dep_wheels)

function(get_embedded_python_url)
    if(NOT WIN32)
        message(FATAL_ERROR "Embedded Python distributions are currently only available for Windows")
    endif()

    cmake_parse_arguments(EMBEDDED_PYTHON "" "VERSION;URL_VAR" "" ${ARGN})
    string(TOLOWER ${CMAKE_SYSTEM_PROCESSOR} PROCESSOR_TYPE)

    set(${EMBEDDED_PYTHON_URL_VAR} "https://www.python.org/ftp/python/${EMBEDDED_PYTHON_VERSION}/python-${EMBEDDED_PYTHON_VERSION}-embed-${PROCESSOR_TYPE}.zip" PARENT_SCOPE)
endfunction(get_embedded_python_url)
