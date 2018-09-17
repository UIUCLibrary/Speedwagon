include(CTest)
file(GLOB pytests RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} test_*.py)
foreach(pytest_file ${pytests})
    message(STATUS "Found ${pytest_file}")

    execute_process(
        COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest ${PROJECT_SOURCE_DIR}/tests/${pytest_file} -qq --collect-only
        OUTPUT_VARIABLE PYTEST_COLLECTION
        ERROR_VARIABLE pytest_std
        )
    if(PYTEST_COLLECTION)
        string(REPLACE "\n" ";" PYTEST_COLLECTION ${PYTEST_COLLECTION})

        foreach(test_name ${PYTEST_COLLECTION})
            string(REGEX MATCH "::test_.*" test_name ${test_name})
            if(test_name)
                string(REPLACE "::" "" test_name ${test_name})
                add_test(NAME ${PROJECT_NAME}.pytest.${pytest_file}.${test_name}
                    WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/standalone
                    COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest ${PROJECT_SOURCE_DIR}/tests/${pytest_file} -k ${test_name} --rootdir=${PROJECT_BINARY_DIR}/standalone
                )
                message(STATUS "Added ${PROJECT_NAME}.pytest.${pytest_file}.${test_name} to CTest")
            endif()
        endforeach()
    else()
        add_test(NAME ${PROJECT_NAME}.pytest.${pytest_file}
                   WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/standalone
            COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest ${PROJECT_SOURCE_DIR}/tests/${pytest_file} --rootdir=${PROJECT_BINARY_DIR}/standalone
        )

    endif(PYTEST_COLLECTION)


#    add_test(NAME ${PROJECT_NAME}.pytest.${pytest_file}
#        WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/standalone
#        COMMAND ${PROJECT_BINARY_DIR}/standalone/python -m pytest ${PROJECT_SOURCE_DIR}/tests/${pytest_file} --rootdir=${PROJECT_BINARY_DIR}/standalone
#    )

endforeach()
