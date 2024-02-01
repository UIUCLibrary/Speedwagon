find_program(DOCKER NAMES
        docker
        )
find_package(Git REQUIRED)
set(JENKINS_CI_DOCKER_IMAGE_NAME "speedwagon" CACHE STRING "Name docker will use to generate an image to run Jenkinsfile runner")
find_path(JENKINS_CI_CASC_PATH
        NAMES casc
        PATHS ci/jenkins/jenkinsfile-runner
        DOC "Path to locate any Jenkins Configuration as Code files"
        REQUIRED
        )
configure_file(cmake/ci.cmake.in ci.cmake @ONLY)
add_custom_command(OUTPUT .jenkinsci
        COMMAND
            ${DOCKER} build
                -f ci/jenkins/jenkinsfile-runner/Dockerfile
                --build-arg USER_ID
                --build-arg GROUP_ID
                --progress plain
                -t ${JENKINS_CI_DOCKER_IMAGE_NAME}
                --iidfile ${PROJECT_BINARY_DIR}/.jenkinsci
                .
        WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
        DEPENDS
            ci/jenkins/jenkinsfile-runner/plugins.txt
            ci/jenkins/jenkinsfile-runner/Dockerfile
        )

add_custom_target(jenkinsci
        COMMAND ${CMAKE_COMMAND} -P ${PROJECT_BINARY_DIR}/ci.cmake
        DEPENDS .jenkinsci
        )