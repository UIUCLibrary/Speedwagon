set(CTEST_PROJECT_NAME standalone)

set(CTEST_SOURCE_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/..)

if(NOT CTEST_CMAKE_GENERATOR)
    set(CTEST_CMAKE_GENERATOR "Visual Studio 14 2015 Win64")
endif()

if(NOT CTEST_BINARY_DIRECTORY)
    set(CTEST_BINARY_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/../build_ci")
endif()

ctest_start(Experimental)
ctest_configure()
ctest_build()
ctest_test()
ctest_submit()
#ctest_empty_binary_directory(${CTEST_BINARY_DIRECTORY})
