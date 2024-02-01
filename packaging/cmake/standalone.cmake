include(packaging/cmake/python_functions.cmake)

get_python_version(
        MAJOR SPEEDWAGON_VERSION_MAJOR
        MINOR SPEEDWAGON_VERSION_MINOR
        PATCH SPEEDWAGON_VERSION_PATCH
        VERSION SPEEDWAGON_VERSION
)
message(STATUS "Speedwagon version discovered - ${SPEEDWAGON_VERSION}")
#project(Speedwagon
#        LANGUAGES NONE
#        VERSION ${SPEEDWAGON_VERSION_MAJOR}.${SPEEDWAGON_VERSION_MINOR}.${SPEEDWAGON_VERSION_PATCH})

find_file(SPEEDWAGON_DOC_PDF
        NAMES speedwagon.pdf
        )

get_embedded_python_url(
        VERSION ${Python_VERSION}
        URL_VAR EMBEDDED_PYTHON_URL
)


FetchContent_Declare(embedded_python
        URL ${EMBEDDED_PYTHON_URL}
        SOURCE_DIR ${EMBEDDED_PYTHON_DESTINATION}
        )
FetchContent_GetProperties(embedded_python)


if (NOT embedded_python_POPULATED)
    message(STATUS "Fetching Embedded Distribution of Python version ${Python_VERSION} for ${CMAKE_SYSTEM_PROCESSOR}")
    FetchContent_Populate(embedded_python)

    # Get pointer size. Used for CPack and deciding if the version of Python
    # used is 32 bit or 64 bit
    execute_process(
            COMMAND ${Python_EXECUTABLE} -c "import struct;import sys;sys ;sys.exit(struct.calcsize('P'))"
            RESULTS_VARIABLE  PYTHON_EMBEDDED_P_SIZE
    )
    set(CMAKE_SIZEOF_VOID_P ${PYTHON_EMBEDDED_P_SIZE})
    if("${PYTHON_EMBEDDED_P_SIZE}" STREQUAL "8")
        set(CPACK_SYSTEM_NAME "win64")
    endif()
    message(STATUS "Fetching Embedded Distribution of Python version ${Python_VERSION} for ${CMAKE_SYSTEM_PROCESSOR} - Done")

    find_file(PYTHON_EMBEDDED_PTH_FILE
            NAMES python${Python_VERSION_MAJOR}${Python_VERSION_MINOR}._pth
            HINTS ${embedded_python_SOURCE_DIR}
            NO_DEFAULT_PATH
            )

    set(PYTHON_INSTALL_CONFIG_PTH_FILE "${CMAKE_CURRENT_BINARY_DIR}/configs/install/python${Python_VERSION_MAJOR}${Python_VERSION_MINOR}._pth")
    set(PYTHON_TEST_CONFIG_PTH_FILE "${CMAKE_CURRENT_BINARY_DIR}/configs/test/python${Python_VERSION_MAJOR}${Python_VERSION_MINOR}._pth")

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

# if build_number is set. make that the PROJECT_VERSION tweak
if(DEFINED ENV{build_number})
    set(CMAKE_PROJECT_VERSION_TWEAK $ENV{build_number})
    set(${PROJECT_NAME}_VERSION_TWEAK $ENV{build_number})
endif()

create_virtual_env()
execute_process(COMMAND ${VENV_PYTHON} -m pip install wheel)
if(SPEEDWAGON_CACHE_PYTHON_WHEEL_DEPENDENCIES)
    if(SPEEDWAGON_REQUIREMENTS_FILE)
        create_dep_wheels(
                PYTHON_EXE ${VENV_PYTHON}
                REQUIREMENTS_FILES
                ${SPEEDWAGON_REQUIREMENTS_FILE}
                ${PROJECT_SOURCE_DIR}/requirements-dev.txt
        )
    else()
        create_dep_wheels(
                PYTHON_EXE ${VENV_PYTHON}
                REQUIREMENTS_FILES
                ${PROJECT_SOURCE_DIR}/requirements-gui.txt
                ${PROJECT_SOURCE_DIR}/requirements-dev.txt
        )

    endif()
endif()

if(SPEEDWAGON_SYNC_PYTHON_BUILD_VENV)
    if(SPEEDWAGON_REQUIREMENTS_FILE)
        install_venv_deps(
                PYTHON_EXE ${VENV_PYTHON}
                REQUIREMENTS_FILES
                ${PROJECT_SOURCE_DIR}/requirements-dev.txt
                ${SPEEDWAGON_REQUIREMENTS_FILE}
        )
    else()
        install_venv_deps(
                PYTHON_EXE ${VENV_PYTHON}
                REQUIREMENTS_FILES
                ${PROJECT_SOURCE_DIR}/requirements-dev.txt
                ${PROJECT_SOURCE_DIR}/requirements-gui.txt
        )
    endif()
endif()

add_custom_target(wheel
        DEPENDS ${PROJECT_BINARY_DIR}/speedwagon-${SPEEDWAGON_VERSION}-py3-none-any.whl
        )

add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/speedwagon-${SPEEDWAGON_VERSION}-py3-none-any.whl
        COMMAND ${VENV_PYTHON} -m build --wheel --outdir  ${PROJECT_BINARY_DIR}
        WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
        MAIN_DEPENDENCY pyproject.toml
        )

add_custom_target(docs
        DEPENDS
        docs/html/index.html
        docs/qthelp/index.html
        )
add_custom_command(
        OUTPUT
        docs/html/index.html
        COMMAND ${VENV_PYTHON} -m sphinx -b html --build-dir=${PROJECT_BINARY_DIR}/docs
        COMMAND ${VENV_PYTHON} -m sphinx -b qthelp --build-dir=${PROJECT_BINARY_DIR}/docs
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
        COMMAND ${VENV_PYTHON} -m sphinx -b qthelp --build-dir=${PROJECT_BINARY_DIR}/docs
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
if(SPEEDWAGON_REQUIREMENTS_FILE)
    add_custom_command(
            OUTPUT
            ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages/speedwagon
            DEPENDS wheel
            COMMAND ${VENV_PYTHON} -m pip install ${PROJECT_BINARY_DIR}/speedwagon-${SPEEDWAGON_VERSION}-py3-none-any.whl[QT] -r ${SPEEDWAGON_REQUIREMENTS_FILE} -t ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE} --no-deps
            COMMENT "Installing ${PROJECT_NAME} to standalone build"
    )
    else()
        add_custom_command(
                OUTPUT
                ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages/speedwagon
                DEPENDS wheel
                COMMAND ${VENV_PYTHON} -m pip install ${PROJECT_BINARY_DIR}/speedwagon-${SPEEDWAGON_VERSION}-py3-none-any.whl[QT] -t ${PROJECT_BINARY_DIR}/standalone/Lib/site-packages --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
                COMMENT "Installing ${PROJECT_NAME} to standalone build"
        )

endif()

if(SPEEDWAGON_REQUIREMENTS_FILE)

    add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/standalone/pytest/pytest.py
            DEPENDS wheel
            COMMAND ${VENV_PYTHON} -m pip install pytest pytest-qt pytest-mock -r ${SPEEDWAGON_REQUIREMENTS_FILE} -t ${PROJECT_BINARY_DIR}/standalone/pytest --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
            COMMENT "Adding PySide6, pytest, and pytest-qt to standalone virtual environment"
            )
    else()
        add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/standalone/pytest/pytest.py
                DEPENDS wheel
                COMMAND ${VENV_PYTHON} -m pip install pytest pytest-qt pytest-mock -t ${PROJECT_BINARY_DIR}/standalone/pytest --find-links ${SPEEDWAGON_PYTHON_DEPENDENCY_CACHE}
                COMMENT "Adding PySide6, pytest, and pytest-qt to standalone virtual environment"
                )
endif()
set(SPEEDWAGON_PYTHON_INTERP python.exe)


include(CTest)
if(WIN32)
    list(APPEND TOP_LEVEL_FILES ${PROJECT_SOURCE_DIR}/packaging/cmake/speedwagon.vbs)
    configure_file(${PROJECT_SOURCE_DIR}/packaging/cmake/templates/speedwagon.bat.in ${PROJECT_BINARY_DIR}/speedwagon.bat @ONLY)
    list(APPEND TOP_LEVEL_FILES ${PROJECT_BINARY_DIR}/speedwagon.bat)

    configure_file(packaging/cmake/templates/README.txt.in ${PROJECT_BINARY_DIR}/README.txt @ONLY)
    list(APPEND TOP_LEVEL_FILES ${PROJECT_BINARY_DIR}/README.txt)
    # install embedded Python to standalone build path
    add_custom_command(TARGET standalone PRE_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_directory ${embedded_python_SOURCE_DIR}/ ${PROJECT_BINARY_DIR}/standalone/
            COMMENT "Adding Python standalone distribution to build"
            )
    add_custom_command(TARGET standalone POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different ${PYTHON_TEST_CONFIG_PTH_FILE} ${PROJECT_BINARY_DIR}/standalone/python${Python_VERSION_MAJOR}${Python_VERSION_MINOR}._pth
            COMMENT "Fixing up python${Python_VERSION_MAJOR}${Python_VERSION_MINOR}._pth"
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
                ENCODING UTF8
                )

        message(STATUS "PYTEST_COLLECTION= ${PYTEST_COLLECTION}")
        if(PYTEST_COLLECTION)
            string(REPLACE "\n" ";" PYTEST_COLLECTION ${PYTEST_COLLECTION})

            foreach(test_name ${PYTEST_COLLECTION})
                if(test_name)
                    if(test_name MATCHES "tests collected" )
                        continue()
                    endif()
                    if(test_name MATCHES "^1" )
                        continue()
                    endif()
                    string(STRIP ${test_name} test_name)
                    set(FULL_TEST_NAME "${PROJECT_NAME}.pytest${test_name}")
                    add_test(NAME ${FULL_TEST_NAME}
                            WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/standalone
                            COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest "${PROJECT_SOURCE_DIR}/${test_name}" -v --full-trace -raP -c ${PROJECT_SOURCE_DIR}/pyproject.toml
                            )
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
            set_tests_properties(${PROJECT_NAME}.pytest.${pytest_file} PROPERTIES
                    ENVIRONMENT "PYTHONDONTWRITEBYTECODE=x"
                    )

        endif(PYTEST_COLLECTION)
    endforeach()

    ###########################################
    include(packaging/cmake/packaging.cmake)

    install(DIRECTORY ${PROJECT_BINARY_DIR}/standalone/
            DESTINATION bin
            PATTERN "pytest" EXCLUDE
            PATTERN "Lib" EXCLUDE
            PATTERN "python.exe" EXCLUDE
            PATTERN "pythonw.exe" EXCLUDE
            PATTERN "python${Python_VERSION_MAJOR}${Python_VERSION_MINOR}._pth" EXCLUDE
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
