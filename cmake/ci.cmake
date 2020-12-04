find_program(DOCKER NAMES
        docker
        )
set(DOCKER "docker")
set(PROJECT_NAME "speedwagon")
set(JENKINS_CI_DOCKER_IMAGE_NAME "speedwagon")
set(PROJECT_SOURCE_DIR "/Users/hborcher/PycharmProjects/UIUCLibrary/Speedwagon")
set(PROJECT_BINARY_DIR "/Users/hborcher/PycharmProjects/UIUCLibrary/Speedwagon/cmake-build-debug")
execute_process(
    OUTPUT_VARIABLE container_id
    COMMAND
        ${DOCKER} run
        -v ${PROJECT_SOURCE_DIR}/ci/:/workspace/ci/
        -v ${PROJECT_SOURCE_DIR}/cmake/:/workspace/cmake/
        -v ${PROJECT_SOURCE_DIR}/docs/:/workspace/docs/
        -v ${PROJECT_SOURCE_DIR}/features/:/workspace/features/
        -v ${PROJECT_SOURCE_DIR}/speedwagon/:/workspace/speedwagon/
        -v ${PROJECT_SOURCE_DIR}/templates/:/workspace/templates/
        -v ${PROJECT_SOURCE_DIR}/ci/jenkins/casc/:/usr/share/jenkins/ref/casc/
        -v ${PROJECT_SOURCE_DIR}/tests/:/workspace/tests/
        -v ${PROJECT_SOURCE_DIR}/CMakeLists.txt:/workspace/CMakeLists.txt
        -v ${PROJECT_SOURCE_DIR}/extra_commands.py:/workspace/extra_commands.py
        -v ${PROJECT_SOURCE_DIR}/HISTORY.rst:/workspace/HISTORY.rst
        -v ${PROJECT_SOURCE_DIR}/Jenkinsfile:/workspace/Jenkinsfile
        -v ${PROJECT_SOURCE_DIR}/LICENSE:/workspace/LICENSE
        -v ${PROJECT_SOURCE_DIR}/Makefile:/workspace/Makefile
        -v ${PROJECT_SOURCE_DIR}/MANIFEST.in:/workspace/MANIFEST.in
        -v ${PROJECT_SOURCE_DIR}/Pipfile:/workspace/Pipfile
        -v ${PROJECT_SOURCE_DIR}/Pipfile.lock:/workspace/Pipfile.lock
        -v ${PROJECT_SOURCE_DIR}/pyproject.toml:/workspace/pyproject.toml
        -v ${PROJECT_SOURCE_DIR}/pyuic.json:/workspace/pyuic.json
        -v ${PROJECT_SOURCE_DIR}/README.rst:/workspace/README.rst
        -v ${PROJECT_SOURCE_DIR}/requirements.txt:/workspace/requirements.txt
        -v ${PROJECT_SOURCE_DIR}/requirements-dev.txt:/workspace/requirements-dev.txt
        -v ${PROJECT_SOURCE_DIR}/requirements-vendor.txt:/workspace/requirements-vendor.txt
        -v ${PROJECT_SOURCE_DIR}/setup.cfg:/workspace/setup.cfg
        -v ${PROJECT_SOURCE_DIR}/setup.py:/workspace/setup.py
        -v ${PROJECT_SOURCE_DIR}/sonar-project.properties:/workspace/sonar-project.properties
        -v ${PROJECT_SOURCE_DIR}/tox.ini:/workspace/tox.ini
        -v /var/run/docker.sock:/var/run/docker.sock
        -d
        -t ${JENKINS_CI_DOCKER_IMAGE_NAME}
        --runWorkspace /build/${PROJECT_NAME}
        --job-name ${PROJECT_NAME}
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
#file(READ ${PROJECT_BINARY_DIR}/.runn