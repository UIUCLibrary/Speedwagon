cmake_minimum_required(VERSION 3.11)
project(Speedwagon
LANGUAGES NONE
    VERSION 0.0.0)

include(FetchContent)
find_package(PythonInterp REQUIRED)

message(STATUS "Using Python ${PYTHON_VERSION_STRING} located at \"${PYTHON_EXECUTABLE}\".")
option(SPEEDWAGON_CACHE_PYTHON_WHEEL_DEPENDENCIES "Cache python whl dependencies to a folder for reuse" ON)
option(SPEEDWAGON_SYNC_PYTHON_BUILD_VENV "SYNC installed python packages in build virtual environment" ON)
set(SPEEDWAGON_PYTHON_DEPENDENCY_CACHE ${PROJECT_BINARY_DIR}/_deps/python_wheels CACHE PATH "location to put Python deps")
set(SPEEDWAGON_VENV_PATH ${PROJECT_BINARY_DIR}/venv CACHE PATH "Location for Python virtual environment needed for building")

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


get_embedded_python_url(
    VERSION ${PYTHON_VERSION_STRING} 
    URL_VAR EMBEDDED_PYTHON_URL
    )


FetchContent_Declare(embedded_python
    URL ${EMBEDDED_PYTHON_URL} 
    SOURCE_DIR ${EMBEDDED_PYTHON_DESTINATION}
)
FetchContent_GetProperties(embedded_python)

if (NOT embedded_python_POPULATED)
    message(STATUS "Fetching Embedded Distribution of Python version ${PYTHON_VERSION_STRING} for ${CMAKE_SYSTEM_PROCESSOR}.")
    FetchContent_Populate(embedded_python)

    # Get pointer size. Used for CPack and deciding if the version of Python
    # used is 32 bit or 64 bit
    execute_process(
        COMMAND python  -c "import struct;import sys;sys ;sys.exit(struct.calcsize('P'))"
        WORKING_DIRECTORY embedded_python_SOURCE_DIR
        RESULTS_VARIABLE  PYTHON_EMBEDDED_P_SIZE
    )
    set(CMAKE_SIZEOF_VOID_P ${PYTHON_EMBEDDED_P_SIZE})

    find_file(PYTHON_EMBEDDED_PTH_FILE
        NAMES python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth
        HINTS ${embedded_python_SOURCE_DIR}
        NO_DEFAULT_PATH
    )
    file(READ ${PYTHON_EMBEDDED_PTH_FILE} PYTHON_EMBEDDED_PTH_DATA)
    string(APPEND PYTHON_EMBEDDED_PTH_DATA "\n@EXTRA_PYTHON_LIBRARY_PATHS@\n")
    
    set(python_pth_template_file "${PROJECT_BINARY_DIR}/templates/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth.in")
    file(WRITE ${python_pth_template_file} ${PYTHON_EMBEDDED_PTH_DATA})

    set(EXTRA_PYTHON_LIBRARY_PATHS "../Lib/site-packages")
    set(PYTHON_INSTALL_CONFIG_PTH_FILE "${PROJECT_BINARY_DIR}/configs/install/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth")
    configure_file(${python_pth_template_file} ${PYTHON_INSTALL_CONFIG_PTH_FILE} @ONLY)

    set(EXTRA_PYTHON_LIBRARY_PATHS "./Lib/site-packages")
    string(APPEND EXTRA_PYTHON_LIBRARY_PATHS "\n./pytest")
    set(PYTHON_TEST_CONFIG_PTH_FILE "${PROJECT_BINARY_DIR}/configs/test/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth" )
    configure_file(${python_pth_template_file} ${PYTHON_TEST_CONFIG_PTH_FILE} @ONLY)

endif()

# Set project Version number based on the metadata
get_python_version(
    ${PROJECT_SOURCE_DIR}/setup.py
    MAJOR CMAKE_PROJECT_VERSION_MAJOR
    MINOR CMAKE_PROJECT_VERSION_MINOR
    PATCH CMAKE_PROJECT_VERSION_PATCH
    VERSION PROJECT_VERSION
    )
get_python_version(
    ${PROJECT_SOURCE_DIR}/setup.py
    MAJOR ${PROJECT_NAME}_VERSION_MAJOR
    MINOR ${PROJECT_NAME}_VERSION_MINOR
    PATCH ${PROJECT_NAME}_VERSION_PATCH
    VERSION ${PROJECT_NAME}_VERSION
    )
# if build_number is set. make that the PROJECT_VERSION tweek
if(DEFINED ENV{build_number})
    set(CMAKE_PROJECT_VERSION_TWEAK $ENV{build_number})
    set(${PROJECT_NAME}_VERSION_TWEAK $ENV{build_number})
endif()

create_virtual_env()
execute_process(COMMAND ${VENV_PYTHON} -m pip install wheel)
#set_property(DIRECTORY PROPERTY CMAKE_CONFIGURE_DEPENDS "requirements.txt;requirements-dev.txt")

#file(TIMESTAMP ${PROJECT_SOURCE_DIR}/requirements.txt requirements_TS)
#message(FATAL_ERROR "requirements_TS = ${requirements_TS}")

if(SPEEDWAGON_CACHE_PYTHON_WHEEL_DEPENDENCIES)
    create_dep_wheels(
        PYTHON_EXE ${VENV_PYTHON}
        REQUIREMENTS_FILES
            ${PROJECT_SOURCE_DIR}/requirements.txt
            ${PROJECT_SOURCE_DIR}/requirements-dev.txt
        )
endif()

if(SPEEDWAGON_SYNC_PYTHON_BUILD_VENV)
    install_venv_deps(
        PYTHON_EXE ${VENV_PYTHON}
        REQUIREMENTS_FILES
            ${PROJECT_SOURCE_DIR}/requirements-dev.txt
            ${PROJECT_SOURCE_DIR}/requirements.txt
    )
endif()

add_custom_target(wheel
   DEPENDS ${PROJECT_BINARY_DIR}/speedwagon-${PROJECT_VERSION}-py3-none-any.whl
    )

add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/speedwagon-${PROJECT_VERSION}-py3-none-any.whl
    COMMAND ${VENV_PYTHON} setup.py build_py --no-compile
    COMMAND ${VENV_PYTHON} setup.py bdist_wheel --bdist-dir ${PROJECT_BINARY_DIR}/python_build --dist-dir ${PROJECT_BINARY_DIR}
    WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
    MAIN_DEPENDENCY setup.py
)

add_custom_target(docs
    DEPENDS ${PROJECT_BINARY_DIR}/docs
    )
add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/docs
    COMMAND ${VENV_PYTHON} setup.py build_sphinx -b html --build-dir=${PROJECT_BINARY_DIR}/docs    
    COMMAND ${VENV_PYTHON} setup.py build_sphinx -b qthelp --build-dir=${PROJECT_BINARY_DIR}/docs
    WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
)

add_custom_target(standalone
    ALL
    DEPENDS ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages/speedwagon ${PROJECT_BINARY_DIR}/standalone/pytest/pytest.py
    # COMMAND ${CMAKE_COMMAND} -E copy_directory ${embedded_python_SOURCE_DIR}/ ${PROJECT_BINARY_DIR}/standalone/
    )

add_custom_command(
    OUTPUT
        ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages/speedwagon
    DEPENDS wheel
    COMMAND ${VENV_PYTHON} -m pip install ${PROJECT_BINARY_DIR}/speedwagon-${PROJECT_VERSION}-py3-none-any.whl -t ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
    )
add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/standalone/pytest/pytest.py
    DEPENDS wheel
    COMMAND ${VENV_PYTHON} -m pip install pytest -t ${PROJECT_BINARY_DIR}/standalone/pytest --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
    )
    # set_property(DIRECTORY ${PROJECT_BINARY_DIR}/standalone PROPERTY ADDITIONAL_MAKE_CLEAN_FILES Lib)
set(SPEEDWAGON_PYTHON_INTERP pythonw.exe)

configure_file(templates/speedwagon.bat.in standalone/speedwagon.bat @ONLY)
# install embedded Python to standalone build path
add_custom_command(TARGET standalone PRE_BUILD 
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${embedded_python_SOURCE_DIR}/ ${PROJECT_BINARY_DIR}/standalone/
    )

configure_file(${PROJECT_SOURCE_DIR}/LICENSE ${PROJECT_BINARY_DIR}/LICENSE.txt)

include(CTest)
add_custom_command(TARGET standalone POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${PYTHON_TEST_CONFIG_PTH_FILE} ${PROJECT_BINARY_DIR}/standalone/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth
    COMMENT "Fixing up python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth"
)
install(FILES ${PYTHON_INSTALL_CONFIG_PTH_FILE} DESTINATION bin)
install(DIRECTORY ${PROJECT_BINARY_DIR}/standalone/
    DESTINATION bin
    PATTERN "pytest" EXCLUDE
    PATTERN "Lib" EXCLUDE
    PATTERN "python.exe" EXCLUDE
    PATTERN "pythonw.exe" EXCLUDE
    PATTERN "python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth" EXCLUDE
    )

install(PROGRAMS ${PROJECT_BINARY_DIR}/standalone/python.exe ${PROJECT_BINARY_DIR}/standalone/pythonw.exe
    DESTINATION bin
    )

install(DIRECTORY ${PROJECT_BINARY_DIR}/standalone/Lib/
    DESTINATION Lib
    )

add_test(NAME unittests
    WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/standalone
    COMMAND python -m pytest ${PROJECT_SOURCE_DIR}/tests --rootdir=${PROJECT_BINARY_DIR}/standalone
    )

set(CPACK_PACKAGE_VENDOR "University Library at The University of Illinois at Urbana Champaign: Preservation Services")
set(CPACK_WIX_UPGRADE_GUID C81EC876-C4BD-11E7-9268-005056C00008)
set(CPACK_PACKAGE_VERSION_MAJOR ${CMAKE_PROJECT_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${CMAKE_PROJECT_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${CMAKE_PROJECT_VERSION_PATCH})
set(CPACK_PACKAGE_ICON "${PROJECT_SOURCE_DIR}/speedwagon/favicon.ico")
set(CPACK_WIX_PRODUCT_ICON "${PROJECT_SOURCE_DIR}/speedwagon/favicon.ico")
set(CPACK_PACKAGE_NAME Speedwagon)
set(CPACK_PACKAGE_INSTALL_DIRECTORY Speedwagon)
set(CPACK_WIX_PROGRAM_MENU_FOLDER Speedwagon)
set(CPACK_RESOURCE_FILE_LICENSE "${PROJECT_BINARY_DIR}/LICENSE.txt")
set(CPACK_WIX_EXTRA_SOURCES ${PROJECT_BINARY_DIR}/configs/install/wix_start_menu.wxs)
set(CPACK_WIX_PATCH_FILE ${PROJECT_SOURCE_DIR}/extra/patch.xml)

if(DEFINED ENV{build_number})
    string(TOLOWER ${CMAKE_SYSTEM_PROCESSOR} PROCESSOR_TYPE)
    set(CPACK_PACKAGE_FILE_NAME ${CPACK_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION_MAJOR}.${CPACK_PACKAGE_VERSION_MINOR}.${CPACK_PACKAGE_VERSION_PATCH}-$ENV{build_number}-${PROCESSOR_TYPE})
endif()

configure_file(templates/wix_start_menu.wvs.in configs/install/wix_start_menu.wxs @ONLY)
include(CPack)
