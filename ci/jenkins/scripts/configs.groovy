def getConfigurations(){
    def configs = [
        "3.7": [
            test_docker_image: "python:3.7",
            tox_env: "py37",
            dockerfiles:[
                windows: "ci/docker/python/windows/Dockerfile",
                linux: "ci/docker/python/linux/jenkins/Dockerfile"
            ],
            pkgRegex: [
                wheel: "*.whl",
                sdist: "*.tar.gz"
            ]
        ],
        "3.8": [
            test_docker_image: "python:3.8",
            tox_env: "py38",
            dockerfiles:[
                windows: "ci/docker/python/windows/Dockerfile",
                linux: "ci/docker/python/linux/jenkins/Dockerfile"
            ],
            pkgRegex: [
                wheel: "*.whl",
                sdist: "*.tar.gz"
            ]
        ],
        "3.9": [
            test_docker_image: "python:3.9",
            tox_env: "py39",
            dockerfiles:[
                windows: "ci/docker/python/windows/Dockerfile",
                linux: "ci/docker/python/linux/jenkins/Dockerfile"
            ],
            pkgRegex: [
                wheel: "*.whl",
                sdist: "*.tar.gz"
            ]
        ]
    ]

//         "3.6": [
//             "os":[
//                 "linux":[
//                     base_image: "python:3.6",
//                     agents: [
//                         build:[
//                             dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                             label: "linux && docker",
//                             additionalBuildArgs: "--build-arg PYTHON_VERSION=3.6",
//                         ],
//                         package:[
//                             dockerfile: "ci/docker/python/linux/package/Dockerfile",
//                             label: "linux && docker",
//                             additionalBuildArgs: "--build-arg PYTHON_VERSION=3.6",
//                         ],
//                         test:[
//                             sdist:[
//                                 dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                                 label: "linux && docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_VERSION=3.6",
//                             ],
//                             whl:[
//                                 dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                                 label: "linux && docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_VERSION=3.6",
//                             ]
//                         ],
//                         devpi: [
//                             whl: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/linux/build/Dockerfile',
//                                     label: 'linux && docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_VERSION=3.6 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
//                                 ]
//                             ],
//                             sdist: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/linux/build/Dockerfile',
//                                     label: 'linux && docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_VERSION=3.6 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
//                                 ]
//                             ]
//                         ]
//                     ],
//                     devpiSelector: [
//                             sdist: "zip",
//                             whl: "36m-manylinux*.*whl",
//                     ],
//                 ],
//                 "windows":[
//                     python_install_url:"https://www.python.org/ftp/python/3.6.8/python-3.6.8-amd64.exe",
//                     base_image: "python:3.6-windowsservercore",
//                     agents: [
//                         build:[
//                             dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                             label: "windows && Docker",
//                             additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.6.8/python-3.6.8-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                         ],
//                         package:[
//                             dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                             label: "windows && Docker",
//                             additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.6.8/python-3.6.8-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                         ],
//                         test:[
//                             whl: [
//                                 dockerfile: "ci/docker/python/windows/msvc/test/Dockerfile",
//                                 label: "windows && Docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_DOCKER_IMAGE_BASE=python:3.6-windowsservercore",
//                             ],
//                             sdist: [
//                                 dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                                 label: "windows && Docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.6.8/python-3.6.8-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                             ]
//                         ],
//                         devpi: [
//                             whl: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/deploy/devpi/test/windows/whl/Dockerfile',
//                                     label: 'Windows&&Docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_DOCKER_IMAGE_BASE=python:3.6-windowsservercore'
//                                 ]
//                             ],
//                             sdist: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/windows/msvc/build/Dockerfile',
//                                     label: 'Windows&&Docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.6.8/python-3.6.8-amd64.exe --build-arg CHOCOLATEY_SOURCE'
//                                 ]
//                             ]
//                         ]
//                     ],
//                     devpiSelector: [
//                         sdist: "zip",
//                         whl: "36m-win*.*whl",
//                     ]
//                 ]
//             ],
//             tox_env: "py36",
//             pkgRegex: [
//                 whl: "*cp36*.whl",
//                 sdist: "*.zip",
//                 devpi_wheel_regex: "36m-win*.*whl"
//             ],
//         ],
//         "3.7": [
//             "os":[
//                 "linux":[
//                     base_image: "python:3.7",
//                     agents: [
//                         build:[
//                             dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                             label: "linux && docker",
//                             additionalBuildArgs: "--build-arg PYTHON_VERSION=3.7",
//                         ],
//                         package:[
//                             dockerfile: "ci/docker/python/linux/package/Dockerfile",
//                             label: "linux && docker",
//                             additionalBuildArgs: "--build-arg PYTHON_VERSION=3.7",
//                         ],
//                         test:[
//                             whl: [
//                                 dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                                 label: "linux && docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_VERSION=3.7",
//                             ],
//                             sdist: [
//                                 dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                                 label: "linux && docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_VERSION=3.7",
//                             ]
//                         ],
//                         devpi: [
//                             whl: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/linux/build/Dockerfile',
//                                     label: 'linux && docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_VERSION=3.7 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
//                                 ]
//                             ],
//                             sdist: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/linux/build/Dockerfile',
//                                     label: 'linux && docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_VERSION=3.7 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
//                                 ]
//                             ]
//                         ]
//                     ],
//                     devpiSelector: [
//                         sdist: "zip",
//                         whl: "37m-manylinux*.*whl",
//                     ],
//                 ],
//                 "windows":[
//                     python_install_url:"https://www.python.org/ftp/python/3.7.5/python-3.7.5-amd64.exe",
//                     base_image: "python:3.7",
//                     agents: [
//                         build:[
//                             dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                             label: "windows && Docker",
//                             additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.7.5/python-3.7.5-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                         ],
//                         package:[
//                             dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                             label: "windows && Docker",
//                             additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.7.5/python-3.7.5-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                         ],
//                         test:[
//                             whl: [
//                                 dockerfile: "ci/docker/python/windows/msvc/test/Dockerfile",
//                                 label: "windows && Docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_DOCKER_IMAGE_BASE=python:3.7",
//                             ],
//                             sdist: [
//                                 dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                                 label: "windows && Docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.7.5/python-3.7.5-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                             ]
//                         ],
//                         devpi: [
//                             whl: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/deploy/devpi/test/windows/whl/Dockerfile',
//                                     label: 'Windows&&Docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_DOCKER_IMAGE_BASE=python:3.7'
//                                 ]
//                             ],
//                             sdist: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/windows/msvc/build/Dockerfile',
//                                     label: 'Windows&&Docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.7.5/python-3.7.5-amd64.exe --build-arg CHOCOLATEY_SOURCE'
//                                 ]
//                             ]
//                         ]
//                     ],
//                     devpiSelector: [
//                         sdist: "zip",
//                         whl: "37m-win*.*whl",
//                     ],
//                 ]
//             ],
//             tox_env: "py37",
//             pkgRegex: [
//                 whl: "*cp37*.whl",
//                 sdist: "*.zip",
//                 devpi_wheel_regex: "37m-win*.*whl"
//             ],
//         ],
//         "3.8": [
//             "os":[
//                 "linux":[
//                     base_image: "python:3.8",
//                     agents: [
//                         build:[
//                             dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                             label: "linux && docker",
//                             additionalBuildArgs: "--build-arg PYTHON_VERSION=3.8",
//                         ],
//                         package:[
//                             dockerfile: "ci/docker/python/linux/package/Dockerfile",
//                             label: "linux && docker",
//                             additionalBuildArgs: "--build-arg PYTHON_VERSION=3.8",
//                         ],
//                         test:[
//                             whl: [
//                                 dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                                 label: "linux && docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_VERSION=3.8",
//                             ],
//                             sdist: [
//                                 dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                                 label: "linux && docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_VERSION=3.8",
//                             ]
//                         ],
//                         devpi: [
//                             whl: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/linux/build/Dockerfile',
//                                     label: 'linux && docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_VERSION=3.8 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
//                                 ]
//                             ],
//                             sdist: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/linux/build/Dockerfile',
//                                     label: 'linux && docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_VERSION=3.8 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
//                                 ]
//                             ]
//                         ]
//                     ],
//                     devpiSelector: [
//                             sdist: "zip",
//                             whl: "38-manylinux*.*whl",
//                     ],
//                 ],
//                 "windows":[
//                     python_install_url:"https://www.python.org/ftp/python/3.8.3/python-3.8.3-amd64.exe",
//                     base_image: "python:3.8",
//                     agents: [
//                         build:[
//                             dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                             label: "windows && Docker",
//                             additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.8.3/python-3.8.3-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                         ],
//                         package:[
//                             dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                             label: "windows && Docker",
//                             additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.8.3/python-3.8.3-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                         ],
//                         test:[
//                             whl: [
//                                 dockerfile: "ci/docker/python/windows/msvc/test/Dockerfile",
//                                 label: "windows && Docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_DOCKER_IMAGE_BASE=python:3.8",
//                             ],
//                             sdist: [
//                                 dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                                 label: "windows && Docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.8.3/python-3.8.3-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                             ]
//                         ],
//                         devpi: [
//                             whl: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/deploy/devpi/test/windows/whl/Dockerfile',
//                                     label: 'Windows&&Docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_DOCKER_IMAGE_BASE=python:3.8'
//                                 ]
//                             ],
//                             sdist: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/windows/msvc/build/Dockerfile',
//                                     label: 'Windows&&Docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.8.3/python-3.8.3-amd64.exe --build-arg CHOCOLATEY_SOURCE'
//                                 ]
//                             ]
//                         ]
//                     ],
//                     devpiSelector: [
//                         sdist: "zip",
//                         whl: "38-win*.*whl",
//                     ],
//                 ]
//             ],
//             tox_env: "py38",
//             pkgRegex: [
//                 whl: "*cp38*.whl",
//                 sdist: "*.zip",
//                 devpi_wheel_regex: "38-win*.*whl"
//             ],
//         ],
//         "3.9": [
//             "os":[
//                 "linux":[
//                     base_image: "python:3.9",
//                     agents: [
//                         build:[
//                             dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                             label: "linux && docker",
//                             additionalBuildArgs: "--build-arg PYTHON_VERSION=3.9",
//                         ],
//                         package:[
//                             dockerfile: "ci/docker/python/linux/package/Dockerfile",
//                             label: "linux && docker",
//                             additionalBuildArgs: "--build-arg PYTHON_VERSION=3.9",
//                         ],
//                         test:[
//                             whl: [
//                                 dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                                 label: "linux && docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_VERSION=3.9",
//                             ],
//                             sdist: [
//                                 dockerfile: "ci/docker/python/linux/build/Dockerfile",
//                                 label: "linux && docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_VERSION=3.9",
//                             ]
//                         ],
//                         devpi: [
//                             whl: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/linux/build/Dockerfile',
//                                     label: 'linux && docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_VERSION=3.9 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
//                                 ]
//                             ],
//                             sdist: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/linux/build/Dockerfile',
//                                     label: 'linux && docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_VERSION=3.9 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
//                                 ]
//                             ]
//                         ]
//                     ],
//                     devpiSelector: [
//                             sdist: "zip",
//                             whl: "39-manylinux*.*whl",
//                     ],
//                 ],
//                 "windows":[
//                     python_install_url:"https://www.python.org/ftp/python/3.9.0/python-3.9.0-amd64.exe",
//                     base_image: "python:3.9",
//                     agents: [
//                         build:[
//                             dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                             label: "windows && Docker",
//                             additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.9.0/python-3.9.0-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                         ],
//                         package:[
//                             dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                             label: "windows && Docker",
//                             additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.9.0/python-3.9.0-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                         ],
//                         test:[
//                             whl: [
//                                 dockerfile: "ci/docker/python/windows/msvc/test/Dockerfile",
//                                 label: "windows && Docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_DOCKER_IMAGE_BASE=python:3.9",
//                             ],
//                             sdist: [
//                                 dockerfile: "ci/docker/python/windows/msvc/build/Dockerfile",
//                                 label: "windows && Docker",
//                                 additionalBuildArgs: "--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.9.0/python-3.9.0-amd64.exe --build-arg CHOCOLATEY_SOURCE",
//                             ]
//                         ],
//                         devpi: [
//                             whl: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/deploy/devpi/test/windows/whl/Dockerfile',
//                                     label: 'Windows&&Docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_DOCKER_IMAGE_BASE=python:3.9'
//                                 ]
//                             ],
//                             sdist: [
//                                 dockerfile: [
//                                     filename: 'ci/docker/python/windows/msvc/build/Dockerfile',
//                                     label: 'Windows&&Docker',
//                                     additionalBuildArgs: '--build-arg PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.9.0/python-3.9.0-amd64.exe --build-arg CHOCOLATEY_SOURCE'
//                                 ]
//                             ]
//                         ]
//                     ],
//                     devpiSelector: [
//                         sdist: "zip",
//                         whl: "39-win*.*whl",
//                     ],
//                 ]
//             ],
//             tox_env: "py39",
//             pkgRegex: [
//                 whl: "*cp39*.whl",
//                 sdist: "*.zip",
//                 devpi_wheel_regex: "39-win*.*whl"
//             ],
//         ]
//     ]
    return configs
}

// def CONFIGURATIONS = [
//

return this
