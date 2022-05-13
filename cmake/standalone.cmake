include(cmake/python_functions.cmake)

get_python_version(
        ${CMAKE_CURRENT_SOURCE_DIR}/setup.py
        MAJOR SPEEDWAGON_VERSION_MAJOR
        MINOR SPEEDWAGON_VERSION_MINOR
        PATCH SPEEDWAGON_VERSION_PATCH
        VERSION SPEEDWAGON_VERSION
)

#project(Speedwagon
#        LANGUAGES NONE
#        VERSION ${SPEEDWAGON_VERSION_MAJOR}.${SPEEDWAGON_VERSION_MINOR}.${SPEEDWAGON_VERSION_PATCH})

find_file(SPEEDWAGON_DOC_PDF
        NAMES speedwagon.pdf
        )

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
    message(STATUS "Fetching Embedded Distribution of Python version ${PYTHON_VERSION_STRING} for ${CMAKE_SYSTEM_PROCESSOR}")
    FetchContent_Populate(embedded_python)

    # Get pointer size. Used for CPack and deciding if the version of Python
    # used is 32 bit or 64 bit
    execute_process(
            COMMAND python  -c "import struct;import sys;sys ;sys.exit(struct.calcsize('P'))"
            WORKING_DIRECTORY embedded_python_SOURCE_DIR
            RESULTS_VARIABLE  PYTHON_EMBEDDED_P_SIZE
    )
    set(CMAKE_SIZEOF_VOID_P ${PYTHON_EMBEDDED_P_SIZE})
    message(STATUS "Fetching Embedded Distribution of Python version ${PYTHON_VERSION_STRING} for ${CMAKE_SYSTEM_PROCESSOR} - Done")

    find_file(PYTHON_EMBEDDED_PTH_FILE
            NAMES python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth
            HINTS ${embedded_python_SOURCE_DIR}
            NO_DEFAULT_PATH
            )

    set(PYTHON_INSTALL_CONFIG_PTH_FILE "${CMAKE_CURRENT_BINARY_DIR}/configs/install/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth")
    set(PYTHON_TEST_CONFIG_PTH_FILE "${CMAKE_CURRENT_BINARY_DIR}/configs/test/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth")

    create_pth_configure_file(
            SOURCE_PTH_FILE "${PYTHON_EMBEDDED_PTH_FILE}"
            OUTPUT "${PYTHON_INSTALL_CONFIG_PTH_FILE}"
            PYTHON_PATHS "../Lib/site-packages"
    )

    create_pth_configure_file(
            SOURCE_PTH_FILE "${PYTHON_EMBEDDED_PTH_FILE}"
            OUTPUT "${PYTHON_TEST_CONFIG_PTH_FILE}"
            PYTHON_PATHS
            ./Lib/site-packages
            ./pytest
    )

endif()

# Set project Version number based on the metadata
#get_python_version(
#    ${CMAKE_CURRENT_SOURCE_DIR}/setup.py
#    MAJOR CMAKE_PROJECT_VERSION_MAJOR
#    MINOR CMAKE_PROJECT_VERSION_MINOR
#    PATCH CMAKE_PROJECT_VERSION_PATCH
#    VERSION PROJECT_VERSION
#    )
#
#get_python_version(
#    ${PROJECT_SOURCE_DIR}/setup.py
#    MAJOR ${PROJECT_NAME}_VERSION_MAJOR
#    MINOR ${PROJECT_NAME}_VERSION_MINOR
#    PATCH ${PROJECT_NAME}_VERSION_PATCH
#    VERSION ${PROJECT_NAME}_VERSION
#    )

# if build_number is set. make that the PROJECT_VERSION tweak
if(DEFINED ENV{build_number})
    set(CMAKE_PROJECT_VERSION_TWEAK $ENV{build_number})
    set(${PROJECT_NAME}_VERSION_TWEAK $ENV{build_number})
endif()

create_virtual_env()
execute_process(COMMAND ${VENV_PYTHON} -m pip install wheel)

if(SPEEDWAGON_CACHE_PYTHON_WHEEL_DEPENDENCIES)
    create_dep_wheels(
            PYTHON_EXE ${VENV_PYTHON}
            REQUIREMENTS_FILES
            ${PROJECT_SOURCE_DIR}/requirements-gui.txt
            ${PROJECT_SOURCE_DIR}/requirements-dev.txt
    )
endif()

if(SPEEDWAGON_SYNC_PYTHON_BUILD_VENV)
    install_venv_deps(
            PYTHON_EXE ${VENV_PYTHON}
            REQUIREMENTS_FILES
            ${PROJECT_SOURCE_DIR}/requirements-dev.txt
            ${PROJECT_SOURCE_DIR}/requirements-gui.txt
    )
endif()

add_custom_target(wheel
        DEPENDS ${PROJECT_BINARY_DIR}/speedwagon-${SPEEDWAGON_VERSION}-py3-none-any.whl
        )

add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/speedwagon-${SPEEDWAGON_VERSION}-py3-none-any.whl
        COMMAND ${VENV_PYTHON} setup.py build_py --no-compile
        COMMAND ${VENV_PYTHON} setup.py bdist_wheel --bdist-dir ${PROJECT_BINARY_DIR}/python_build --dist-dir ${PROJECT_BINARY_DIR}
        WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
        MAIN_DEPENDENCY setup.py
        )

add_custom_target(docs
        DEPENDS
        docs/html/index.html
        docs/qthelp/index.html
        )
add_custom_command(
        OUTPUT
        docs/html/index.html
        COMMAND ${VENV_PYTHON} setup.py build_sphinx -b html --build-dir=${PROJECT_BINARY_DIR}/docs
        COMMAND ${VENV_PYTHON} setup.py build_sphinx -b qthelp --build-dir=${PROJECT_BINARY_DIR}/docs
        DEPENDS
        ${PROJECT_SOURCE_DIR}/docs/source/conf.py
        ${PROJECT_SOURCE_DIR}/docs/source/about.rst
        ${PROJECT_SOURCE_DIR}/docs/source/history.rst
        ${PROJECT_SOURCE_DIR}/docs/source/index.rst
        ${PROJECT_SOURCE_DIR}/HISTORY.rst
        COMMENT "Generating HTML project documentation"
        WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
)

add_custom_command(
        OUTPUT
        docs/qthelp/index.html
        COMMAND ${VENV_PYTHON} setup.py build_sphinx -b qthelp --build-dir=${PROJECT_BINARY_DIR}/docs
        DEPENDS
        ${PROJECT_SOURCE_DIR}/docs/source/conf.py
        ${PROJECT_SOURCE_DIR}/docs/source/about.rst
        ${PROJECT_SOURCE_DIR}/docs/source/history.rst
        ${PROJECT_SOURCE_DIR}/docs/source/index.rst
        ${PROJECT_SOURCE_DIR}/HISTORY.rst
        COMMENT "Generating QtHelp project documentation"
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
        COMMAND ${VENV_PYTHON} -m pip install ${PROJECT_BINARY_DIR}/speedwagon-${SPEEDWAGON_VERSION}-py3-none-any.whl -t ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
        COMMENT "Installing ${PROJECT_NAME} to standalone build"
)

# If an extra requirements file is requested to be installed, include them in
# the build
if(SPEEDWAGON_EXTRA_REQUIREMENTS_FILE)
    if(EXISTS ${SPEEDWAGON_EXTRA_REQUIREMENTS_FILE})
        add_custom_command(
                TARGET standalone POST_BUILD
                COMMAND ${VENV_PYTHON} -m pip install -r ${SPEEDWAGON_EXTRA_REQUIREMENTS_FILE} -t ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
                COMMENT "Installing dependencies in ${SPEEDWAGON_EXTRA_REQUIREMENTS_FILE} to build"
        )
    else()
        message(WARNING "Unable to located SPEEDWAGON_EXTRA_REQUIREMENTS_FILE value \"${SPEEDWAGON_EXTRA_REQUIREMENTS_FILE}\"")
    endif()
endif(SPEEDWAGON_EXTRA_REQUIREMENTS_FILE)

add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/standalone/pytest/pytest.py
        DEPENDS wheel
        COMMAND ${VENV_PYTHON} -m pip install pytest pytest-qt PySide6 -t ${PROJECT_BINARY_DIR}/standalone/pytest --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
        COMMENT "Adding PySide6, pytest, and pytest-qt to standalone virtual environment"
        )
set(SPEEDWAGON_PYTHON_INTERP python.exe)

include(CTest)
if(WIN32)
    list(APPEND TOP_LEVEL_FILES ${PROJECT_SOURCE_DIR}/cmake/speedwagon.vbs)
    configure_file(templates/speedwagon.bat.in ${PROJECT_BINARY_DIR}/speedwagon.bat @ONLY)
    list(APPEND TOP_LEVEL_FILES ${PROJECT_BINARY_DIR}/speedwagon.bat)

    configure_file(templates/README.txt.in ${PROJECT_BINARY_DIR}/README.txt @ONLY)
    list(APPEND TOP_LEVEL_FILES ${PROJECT_BINARY_DIR}/README.txt)
    # install embedded Python to standalone build path
    add_custom_command(TARGET standalone PRE_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_directory ${embedded_python_SOURCE_DIR}/ ${PROJECT_BINARY_DIR}/standalone/
            COMMENT "Adding Python standalone distribution to build"
            )
    add_custom_command(TARGET standalone POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different ${PYTHON_TEST_CONFIG_PTH_FILE} ${PROJECT_BINARY_DIR}/standalone/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth
            COMMENT "Fixing up python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth"
            )
    install(FILES ${PYTHON_INSTALL_CONFIG_PTH_FILE} DESTINATION bin)
    install(PROGRAMS
            ${PROJECT_BINARY_DIR}/standalone/python.exe
            ${PROJECT_BINARY_DIR}/standalone/pythonw.exe
            DESTINATION bin
            )

    install(DIRECTORY
            ${PROJECT_BINARY_DIR}/standalone/Lib/
            DESTINATION Lib
            )
    #    add_subdirectory(tests)
    ###########################################
    enable_testing()
    execute_process(COMMAND ${VENV_PYTHON} -m pytest --version)

    execute_process(
            COMMAND ${VENV_PYTHON} -m pytest ${PROJECT_SOURCE_DIR}/tests/ -qqq --collect-only
            OUTPUT_VARIABLE PYTHON_TESTS
            OUTPUT_STRIP_TRAILING_WHITESPACE
            RESULTS_VARIABLE PYTEST_RESULT
    )
    if(NOT PYTEST_RESULT EQUAL 0)
        message(FATAL_ERROR "Using pytest to scan tests resulted in Non-zero return code: ${PYTEST_RESULT}")
    endif()

    string(REGEX REPLACE ": [0-9]*" "" PYTHON_TESTS "${PYTHON_TESTS}")
    string(REPLACE "\n" ";" PYTHON_TESTS ${PYTHON_TESTS})

    foreach(pytest_file ${PYTHON_TESTS})
        message(STATUS "Found ${pytest_file}")


        execute_process(COMMAND ${VENV_PYTHON} -m pytest ${PROJECT_SOURCE_DIR}/${pytest_file} -qq --collect-only
                OUTPUT_VARIABLE PYTEST_COLLECTION
                ERROR_VARIABLE pytest_std
                OUTPUT_STRIP_TRAILING_WHITESPACE
                ENCODING AUTO
                )

        message(STATUS "PYTEST_COLLECTION= ${PYTEST_COLLECTION}")
        if(PYTEST_COLLECTION)
            string(REPLACE "\n" ";" PYTEST_COLLECTION ${PYTEST_COLLECTION})

            foreach(test_name ${PYTEST_COLLECTION})
#                string(REGEX MATCH "::test_.*" test_name ${test_name})
                if(test_name)
                    if(test_name MATCHES "tests collected" )
                        continue()
                    endif()
                    if(test_name MATCHES "^1" )
                        continue()
                    endif()
                    string(STRIP ${test_name} test_name)
                    set(FULL_TEST_NAME "${PROJECT_NAME}.pytest${test_name}")
                    string(REPLACE " " "_" FULL_TEST_NAME ${FULL_TEST_NAME})
                    add_test(NAME ${FULL_TEST_NAME}
                            WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/standalone
                            COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest "../../${test_name}" -v --full-trace -raP -c ${PROJECT_SOURCE_DIR}/pyproject.toml
                            )
#                            COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest ../../${test_name} -v --full-trace --rootdir=${PROJECT_BINARY_DIR}/standalone -raP
                    set_tests_properties(${FULL_TEST_NAME} PROPERTIES
                            RESOURCE_LOCK ${pytest_file}
                            ENVIRONMENT "PYTHONDONTWRITEBYTECODE=x"
                            )
                endif()
            endforeach()
        else()
            message(STATUS "Added ${PROJECT_NAME}.pytest.${pytest_file} to CTest")
            add_test(NAME ${PROJECT_NAME}.pytest.${pytest_file}
                    WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/standalone
                    COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest "${PROJECT_SOURCE_DIR}/${pytest_file}" -c ${PROJECT_SOURCE_DIR}/pyproject.toml -raP
                    )
#                    COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest ${PROJECT_SOURCE_DIR}/${pytest_file} --rootdir=${PROJECT_BINARY_DIR}/standalone -raP
            set_tests_properties(${PROJECT_NAME}.pytest.${pytest_file} PROPERTIES
                    ENVIRONMENT "PYTHONDONTWRITEBYTECODE=x"
                    )

        endif(PYTEST_COLLECTION)


        #    add_test(NAME ${PROJECT_NAME}.pytest.${pytest_file}
        #        WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/standalone
        #        COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest ${PROJECT_SOURCE_DIR}/tests/${pytest_file} --rootdir=${PROJECT_BINARY_DIR}/standalone
        #    )

    endforeach()

    ###########################################
    include(cmake/packaging.cmake)

    install(DIRECTORY ${PROJECT_BINARY_DIR}/standalone/
            DESTINATION bin
            PATTERN "pytest" EXCLUDE
            PATTERN "Lib" EXCLUDE
            PATTERN "python.exe" EXCLUDE
            PATTERN "pythonw.exe" EXCLUDE
            PATTERN "python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}._pth" EXCLUDE
            )

    if(EXISTS "${SPEEDWAGON_DOC_PDF}")
        install(FILES ${SPEEDWAGON_DOC_PDF}
                DESTINATION share/doc
                )
        set_property(INSTALL "${CMAKE_INSTALL_PREFIX}/share/doc/speedwagon.pdf"
                PROPERTY CPACK_START_MENU_SHORTCUTS "Documentation"

                )

    endif()

endif()

configure_file(${PROJECT_SOURCE_DIR}/LICENSE ${PROJECT_BINARY_DIR}/LICENSE.txt)



install(FILES
        ${TOP_LEVEL_FILES}
        ${PROJECT_BINARY_DIR}/LICENSE.txt
        DESTINATION .)


include(CPack)
