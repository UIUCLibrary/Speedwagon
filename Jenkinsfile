#!groovy
@Library("ds-utils@v0.2.3") // Uses library from https://github.com/UIUCLibrary/Jenkins_utils
import org.ds.*

def name = "unknown"
def version = "unknown"
def CMAKE_VERSION = "cmake3.11.2"

pipeline {
    agent {
        label "Windows && Python3 && longfilenames && WIX"
    }
    
    triggers {
        cron('@daily')
    }

    options {
        disableConcurrentBuilds()  //each branch has 1 job running at a time
        timeout(20)  // Timeout after 20 minutes. This shouldn't take this long but it hangs for some reason
        checkoutToSubdirectory("source")
    }

    environment {
        // mypy_args = "--junit-xml=mypy.xml"
        PIPENV_CACHE_DIR="${WORKSPACE}\\..\\.virtualenvs\\cache\\"
        WORKON_HOME ="${WORKSPACE}\\pipenv\\"
        build_number = VersionNumber(projectStartDate: '2017-11-08', versionNumberString: '${BUILD_DATE_FORMATTED, "yy"}${BUILD_MONTH, XX}${BUILDS_THIS_MONTH, XXX}', versionPrefix: '', worstResultForIncrement: 'SUCCESS')
        PIPENV_NOSPIN = "True"
        // pytest_args = "--junitxml=reports/junit-{env:OS:UNKNOWN_OS}-{envname}.xml --junit-prefix={env:OS:UNKNOWN_OS}  --basetemp={envtmpdir}"
    }

    parameters {
        // string(name: "PROJECT_NAME", defaultValue: "Speedwagon", description: "Name given to the project")
        string(name: 'JIRA_ISSUE', defaultValue: "PSR-83", description: 'Jira task to generate about updates.')   
        booleanParam(name: "BUILD_DOCS", defaultValue: true, description: "Build documentation")
        // file description: 'Build with alternative requirements.txt file', name: 'requirements.txt'
        booleanParam(name: "TEST_RUN_PYTEST", defaultValue: true, description: "Run PyTest unit tests") 
        booleanParam(name: "TEST_RUN_BEHAVE", defaultValue: true, description: "Run Behave unit tests")
        booleanParam(name: "TEST_RUN_DOCTEST", defaultValue: true, description: "Test documentation")
        booleanParam(name: "TEST_RUN_FLAKE8", defaultValue: true, description: "Run Flake8 static analysis")
        booleanParam(name: "TEST_RUN_MYPY", defaultValue: true, description: "Run MyPy static analysis")
        booleanParam(name: "TEST_RUN_TOX", defaultValue: true, description: "Run Tox Tests")
        booleanParam(name: "PACKAGE_PYTHON_FORMATS", defaultValue: true, description: "Create native Python packages")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE", defaultValue: true, description: "Windows Standalone")
        booleanParam(name: "DEPLOY_DEVPI", defaultValue: true, description: "Deploy to DevPi on https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: "DEPLOY_DEVPI_PRODUCTION", defaultValue: false, description: "Deploy to https://devpi.library.illinois.edu/production/release")
        booleanParam(name: "DEPLOY_HATHI_TOOL_BETA", defaultValue: false, description: "Deploy standalone to \\\\storage.library.illinois.edu\\HathiTrust\\Tools\\beta\\")
        booleanParam(name: "DEPLOY_SCCM", defaultValue: false, description: "Request deployment of MSI installer to SCCM")
        booleanParam(name: "DEPLOY_DOCS", defaultValue: false, description: "Update online documentation")
        string(name: 'URL_SUBFOLDER', defaultValue: "speedwagon", description: 'The directory that the docs should be saved under')
    }
    
    stages {
        stage("Testing Jira epic"){
            agent any
            when {
                equals expected: true, actual: params.UPDATE_JIRA_EPIC
                // expression {params.UPDATE_JIRA_EPIC == true}
            }
            steps {
                echo "Finding Jira epic"
                script {
                    // def result = jiraSearch "issue = $params.JIRA_ISSUE"
                    // jiraComment body: 'Just a test', issueKey: 'PSR-83'
                    def result = jiraGetIssue idOrKey: 'PSR-83', site: 'https://bugs.library.illinois.edu'
                    echo "result = ${result}"
                    // def result = jiraIssueSelector(issueSelector: [$class: 'DefaultIssueSelector'])
                    // def result = jiraIssueSelector(issueSelector: [$class: 'JqlIssueSelector', jql: "issue = $params.JIRA_ISSUE"])
                    // if(result.isEmpty()){
                    //     echo "Jira issue not found"
                    //     error("Jira issue not found")

                    // } else {
                    //     echo "Located ${result}"
                    // }
                }

            }
        }
        stage("Configure Environment"){
            steps {
                dir("logs"){
                    echo "Cleaning out logs directory"
                    deleteDir()
                }
                
                dir("build"){
                    echo "Cleaning out build directory"
                    deleteDir()
                }
                
                // bat "dir ${WORKSPACE}\\..\\${JOB_BASE_NAME}\\${NODE_NAME}"
                echo "Building on: ${NODE_NAME}."
                lock("system_python_${NODE_NAME}"){
                    bat "${tool 'CPython-3.6'} -m pip install --upgrade pip --quiet"
                    bat "${tool 'CPython-3.6'} -m pip install --upgrade pipenv sphinx devpi-client --quiet"
                }
                bat "${tool 'CPython-3.6'} -m pip --version"
                dir("python_deps"){
                    bat "dir"
                }
                dir("source") {
                    stash includes: 'deployment.yml', name: "Deployment"
                    script {
                        name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                        version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                    }
                    tee("${WORKSPACE}/logs/pippackages_system_${NODE_NAME}.log") {
                        bat "${tool 'CPython-3.6'} -m pip list"
                    }
                    
                    timeout(5) {
                        bat "${tool 'CPython-3.6'} -m pipenv install --dev"
                    }

                    tee("${WORKSPACE}/logs/pippackages_pipenv_${NODE_NAME}.log") {
                        bat "${tool 'CPython-3.6'} -m pipenv run pip list"
                    }
                
                }            
            }
            post{
                always{
                    archiveArtifacts artifacts: "logs/*.log"
                }
                success{
                    echo """Successfully configured build environment.
Source from the repository is located in source/
log files are located in logs/
pipenv virtual environments are located in pipenv/
"""
                }
                // cleanup{
                //     bat "del pippackages_system_${NODE_NAME}.log"
                //     bat "del pippackages_pipenv_${NODE_NAME}.log"
                // }
            }
        }
        stage('Build') {
            parallel {
                stage("Python Package"){
                    steps {
                        
                        tee('logs/build.log') {
                            dir("source"){
                                lock("system_pipenv_${NODE_NAME}"){
                                    powershell "Start-Process -NoNewWindow -FilePath ${tool 'CPython-3.6'} -ArgumentList '-m pipenv run python setup.py build -b ${WORKSPACE}\\build' -Wait"
                                }
                                // bat script: "${tool 'CPython-3.6'} -m pipenv run python setup.py build -b ${WORKSPACE}\\build"
                            }
                        }
                    }
                    post{
                        always{
                            warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'Pep8', pattern: 'logs/build.log']]
                            archiveArtifacts artifacts: "logs/*.log"
                            // bat "dir build"
                        }
                        failure{
                            echo "Failed to build Python package"
                        }
                        success{
                            echo "Successfully built project is ./build."
                        }
                    }
                }
                stage("Sphinx documentation"){
                    when {
                        equals expected: true, actual: params.BUILD_DOCS
                    }
                    steps {
                        // bat 'mkdir "build/docs/html"'
                        echo "Building docs on ${env.NODE_NAME}"
                        tee('logs/build_sphinx.log') {
                            dir("source"){
                                lock("system_pipenv_${NODE_NAME}"){
                                    bat script: "${tool 'CPython-3.6'} -m pipenv run python setup.py build_sphinx --build-dir ${WORKSPACE}\\build\\docs"  
                                }
                            }   
                        }
                    }
                    post{
                        always {
                            warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'Pep8', pattern: 'logs/build_sphinx.log']]
                            archiveArtifacts artifacts: 'logs/build_sphinx.log'
                        }
                        success{
                            publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'build/docs/html', reportFiles: 'index.html', reportName: 'Documentation', reportTitles: ''])
                            script{
                                // Multibranch jobs add the slash and add the branch to the job name. I need only the job name
                                def alljob = env.JOB_NAME.tokenize("/") as String[]
                                def project_name = alljob[0]
                                dir('build/docs/') {
                                    zip archive: true, dir: 'html', glob: '', zipFile: "${project_name}-${env.BRANCH_NAME}-docs-html-${env.GIT_COMMIT.substring(0,7)}.zip"
                                }
                            }
                        }
                        failure{
                            echo "Failed to build Python package"
                        }
                    }
                }
            }
        }
        stage("Test") {
            parallel {
                stage("Run Behave BDD Tests") {
                    when {
                       equals expected: true, actual: params.TEST_RUN_BEHAVE
                    }
                    steps {
                        dir("source"){
                            bat "pipenv run behave --junit --junit-directory ${WORKSPACE}\\reports\\behave"
                        }
                        
                    }
                    post {
                        always {
                            bat "dir reports"
                            junit "reports/behave/*.xml"
                        }
                    }
                }
                stage("Run Pytest Unit Tests"){
                    when {
                       equals expected: true, actual: params.TEST_RUN_PYTEST
                    }
                    environment{
                        junit_filename = "junit-${env.NODE_NAME}-${env.GIT_COMMIT.substring(0,7)}-pytest.xml"
                    }
                    steps{
                        dir("source"){
                            bat "pipenv run py.test --junitxml=${WORKSPACE}/reports/pytest/${junit_filename} --junit-prefix=${env.NODE_NAME}-pytest --cov-report html:${WORKSPACE}/reports/pytestcoverage/ --cov=speedwagon"    
                        }                    
                    }
                    post {
                        always {
                            publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: "reports/pytestcoverage", reportFiles: 'index.html', reportName: 'Coverage', reportTitles: ''])
                            junit "reports/pytest/${junit_filename}"
                        }
                    }
                }
                stage("Run Doctest Tests"){
                    when {
                       equals expected: true, actual: params.TEST_RUN_DOCTEST
                    }
                    steps {
                        dir("source"){
                            dir("reports/doctests"){
                                echo "Cleaning doctest reports directory"
                                deleteDir()
                            }
                            bat "pipenv run sphinx-build -b doctest docs\\source ${WORKSPACE}\\build\\docs -d ${WORKSPACE}\\build\\docs\\doctrees"
                            
                        }
                        bat "move build\\docs\\output.txt ${WORKSPACE}\\reports\\doctest.txt"
                    }
                    post{
                        always {
                            bat "dir ${WORKSPACE}\\reports"
                            
                            archiveArtifacts artifacts: "reports/doctest.txt"
                        }
                    }
                }
                stage("Run MyPy Static Analysis") {
                    when {
                        equals expected: true, actual: params.TEST_RUN_MYPY
                    }
                    steps{
                        script{
                            try{
                                tee('logs/mypy.log') {
                                    dir("source"){
                                        bat "pipenv run mypy -p speedwagon --html-report ${WORKSPACE}\\reports\\mypy\\html"
                                    }
                                }
                            } catch (exc) {
                                echo "MyPy found some warnings"
                            }      
                    
                        }
                    }
                    post {
                        always {
                            warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'MyPy', pattern: 'logs/mypy.log']], unHealthy: ''
                            publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/mypy/html/', reportFiles: 'index.html', reportName: 'MyPy HTML Report', reportTitles: ''])
                        }
                    }
                }
                stage("Run Tox test") {
                    when{
                        equals expected: true, actual: params.TEST_RUN_TOX
                    }
                    steps {
                        dir("source"){
                            script{
                                try{
                                    bat "pipenv run tox --workdir ${WORKSPACE}\\.tox"
                                } catch (exc) {
                                    bat "pipenv run tox --workdir ${WORKSPACE}\\.tox --recreate"
                                }
                            }
                            
                        }
                    }
                }
                stage("Run Flake8 Static Analysis") {
                    when {
                        equals expected: true, actual: params.TEST_RUN_FLAKE8
                    }
                    steps{
                        script{
                            try{
                                tee('reports/flake8.log') {
                                    dir("source"){
                                        bat "pipenv run flake8 speedwagon --format=pylint"
                                    }
                                }
                            } catch (exc) {
                                echo "flake8 found some warnings"
                            }
                        }
                    }
                    post {
                        always {
                            warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'PyLint', pattern: 'reports/flake8.log']], unHealthy: ''
                        }
                    }
                }
            }
        }
        stage("Packaging") {
            parallel {
                stage("Source and Wheel formats"){
                    when {
                        equals expected: true, actual: params.PACKAGE_PYTHON_FORMATS
                    }
                    
                    steps{
                        dir("source"){
                            bat script: "pipenv run python setup.py sdist -d ${WORKSPACE}\\dist bdist_wheel -d ${WORKSPACE}\\dist"
                        }
                    }
                    
                    post {
                        success {
                            dir("dist") {
                                archiveArtifacts artifacts: "*.whl", fingerprint: true
                                archiveArtifacts artifacts: "*.tar.gz", fingerprint: true
                                archiveArtifacts artifacts: "*.zip", fingerprint: true
                            }
                        }
                        failure {
                            echo "Failed to package."
                        }
                    }
                }
                // stage("Windows Standalone"){
                //     agent {
                //         node {
                //             label "Windows && VS2015 && DevPi"
                //         }
                //     }
                //     environment {
                //         VSCMD_START_DIR = "${env.WORKSPACE}"
                //         PIPENV_CACHE_DIR="${WORKSPACE}\\..\\.virtualenvs\\cache\\"
                //         // PIPENV_VENV_IN_PROJECT="True"
                //         WORKON_HOME ="${WORKSPACE}\\..\\.virtualenvs\\${JOB_NAME}\\${NODE_NAME}"
                //         // PIPENV_CACHE_DIR="${USERPROFILE}\\.virtualenvs\\cache\\"
                //         // WORKON_HOME = "./venv"
                //     }
                //     // PACKAGE_WINDOWS_STANDALONE
                //     when {
                //         not { changeRequest()}
                //         equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE
                //     }
                //     steps {

                //         script{
                //             lock("system_python_${NODE_NAME}"){
                //                 def powershell_command = "Start-Process -NoNewWindow -FilePath ${tool 'CPython-3.6'} -ArgumentList '-m pip install --upgrade pip pipenv' -Wait"
                //                 echo "${powershell_command}"
                //                 powershell "${powershell_command}"

                //             }
                //         }
                //         bat "${tool 'CPython-3.6'} -m venv venv"

                //         script{
                //             try{
                //                 bat "${WORKSPACE}\\venv\\Scripts\\python.exe -m pip install -U pip"
                //             } catch (exc) {
                //                 bat "${WORKSPACE}\\venv\\Scripts\\python.exe -m pip install -U pip --no-cache-dir"
                //             }
                //         }

                //         tee('build_standalone.log') {
                //             dir("source"){
                //                 bat script: "${tool 'CPython-3.6'} -m pipenv lock -r"
                //                 bat script: "${tool 'CPython-3.6'} -m pipenv lock -r > requirements.txt"
                //                 bat script: "${tool 'CPython-3.6'} -m pipenv lock -rd > requirements-dev.txt"

                //                 // bat "venv\\Scripts\\python.exe -m pip install -U pip"
                //                 bat "${WORKSPACE}\\venv\\Scripts\\pip.exe install -U setuptools>=30.3.0"
                //                 bat "${WORKSPACE}\\venv\\Scripts\\pip.exe install -r requirements-dev.txt"
                //                 script{
                //                     def requirements = readFile 'requirements.txt'
                //                     writeFile file: 'requirements.txt', text: "${requirements}setuptools>=30.3.0\n"
                //                     // def python_path = powershell returnStdout: true, script: 'pipenv --py'.trim()
                //                     // def python_path = "python.exe"
                //                     // echo "python_path = ${python_path}"
                //                     bat "mkdir build"
                //                     // powershell "windows_build\\build.ps1 -python_path ${WORKSPACE}\\venv\\Scripts\\python.exe"
                //                     powershell "windows_build\\build.ps1 -PYTHON_HOME ${WORKSPACE}\\venv"
                //                 }
                //             }
                //         }
                //     }
                //     post {
                //         failure {
                //             bat "pipenv uninstall --all"
                //             bat "pipenv run pipenv-resolver --clear"
                //         }
                //         success {
                //             dir("source/dist") {
                //                 stash includes: "*.msi", name: "msi"
                //                 archiveArtifacts artifacts: "*.msi", fingerprint: true
                //             }
                //         }
                //         always {
                //             archiveArtifacts artifacts: 'build_standalone.log', allowEmptyArchive: true
                //             warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'MSBuild', pattern: 'build_standalone.log']]
                //         }
                //     }
                // }
                stage("Windows Standalone"){
                    agent {
                        node {
                            label "Windows && Python3 && longfilenames && WIX"
                            customWorkspace "c:/Jenkins/temp/${JOB_NAME}/standalone_build"
                        }
                    }
                    options{
                        retry(2)
                    }
                    stages{
                        stage("CMake Build"){
                            steps {
                                tee('build_standalone_cmake.log') {
                                    dir("cmake_build") {
                                        bat "dir"
                                        cmake arguments: "${WORKSPACE}/source -DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=${WORKSPACE}/python_deps -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv", installation: "${CMAKE_VERSION}"
                                        // TODO: When upgrading to CMAKE 3.12 use the generic build parallel argument
                                        cmake arguments: "--build . --config Release -- /maxcpucount:${NUMBER_OF_PROCESSORS}", installation: "${CMAKE_VERSION}"
                                    }
                                }
                            }
                        }
                        stage("CTest Build"){
                            steps {
                                tee('test_standalone_cmake.log') {
                                    dir("cmake_build") {
                                        ctest arguments: '-C Release --output-on-failure -C Release --no-compress-output -T test', installation: "${CMAKE_VERSION}"
                                    }
                                }
                            }
                            post{
                                always {
                                    script {
                                        def ctest_results = findFiles glob: 'Testing/**/Test.xml'
                                        ctest_results.each{ ctest_result ->
                                            echo "Found ${ctest_result}"
                                            archiveArtifacts artifacts: "${ctest_result}", fingerprint: true
                                            xunit testTimeMargin: '3000',
                                                thresholdMode: 1,
                                                thresholds: [
                                                    failed(),
                                                    skipped()
                                                ],
                                                tools: [
                                                    CTest(
                                                        deleteOutputFiles: true,
                                                        failIfNotNew: true,
                                                        pattern: "${ctest_result}",
                                                        skipNoTestFiles: false,
                                                        stopProcessingIfError: true
                                                        )
                                                    ]
                                            bat "del ${ctest_result}"
                                        }
                                        
                                    }
                                    archiveArtifacts artifacts: 'build_standalone_cmake.log', allowEmptyArchive: true
                                    warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'MSBuild', pattern: 'build_standalone_cmake.log']]
                                }
                            }
                        }
                        stage("CPack WIX"){
                            steps {
                                dir("cmake_build") {
                                    cpack arguments: '-C Release -G WIX -V', installation: "${CMAKE_VERSION}"
                                }
                            }
                            post {
                                success{
                                    dir("cmake_build") {
                                        script{   
                                            def install_files = findFiles glob: "*.msi"
                                            install_files.each { installer_file ->
                                                echo "Found ${installer_file}"
                                                archiveArtifacts artifacts: "${installer_file}", fingerprint: true
                                            }
                                        }
                                        stash includes: "*.msi", name: "msi"
                                    }
                                }
                                always{
                                    dir("cmake_build"){
                                        script {
                                            def wix_logs = findFiles glob: "**/wix.log"
                                            wix_logs.each { wix_log ->
                                                archiveArtifacts artifacts: "${wix_log}" 
                                            }
                                        }
                                    }
                                }
                                failure {
                                    script{
                                        try{
                                            def wix_logs = findFiles glob: "**/wix.log"
                                            wix_logs.each { wix_log ->
                                                def error_message = readFile("${wix_log}")
                                                echo "${error_message}"
                                            }
                                            // def error_message = readFile("cmake_build/_CPack_Packages/win64/WIX/wix.log")
                                            // echo "${error_message}"
                                        } catch (exc) {
                                            echo "read the wix logs."
                                        }
                                        dir("cmake_build"){
                                            cmake arguments: "--build . --target clean", installation: "${CMAKE_VERSION}"
                                        }
                                    }
                                }
                                cleanup{
                                   dir("cmake_build"){
                                       bat "del *.msi"
                                   }
                                }
                         
                            }
                        }
                        stage("CPack NSIS"){
                            steps {
                                dir("cmake_build") {
                                    cpack arguments: '-C Release -G NSIS -V', installation: "${CMAKE_VERSION}"
                                }
                            }
                            post {
                                success{
                                    dir("cmake_build") {
                                        script{   
                                            def install_files = findFiles glob: "Speedwagon*.exe"
                                            install_files.each { installer_file ->
                                                echo "Found ${installer_file}"
                                                archiveArtifacts artifacts: "${installer_file}", fingerprint: true
                                            }
                                        }
                                    }
                                }                               
                                failure {
                                    dir("cmake_build"){
                                        cmake arguments: "--build . --target clean", installation: "${CMAKE_VERSION}"
                                    }
                                }
                                cleanup{
                                   dir("cmake_build"){
                                       bat "del *.msi"
                                   }
                                }
                         
                            }
                        }
                    }
                }
            }

        }
        
        stage("Deploy to Devpi Staging") {
            // when {
            //     expression { params.DEPLOY_DEVPI == true && (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "dev")}
            // }
            when {
                allOf{
                    equals expected: true, actual: params.DEPLOY_DEVPI
                    anyOf {
                        equals expected: "master", actual: env.BRANCH_NAME
                        equals expected: "dev", actual: env.BRANCH_NAME
                    }
                }
            }
            steps {
                dir("source"){
                    bat "devpi use https://devpi.library.illinois.edu"
                    withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                        bat "${tool 'CPython-3.6'} -m devpi login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                        bat "${tool 'CPython-3.6'} -m devpi use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                        script {
                            bat "${tool 'CPython-3.6'} -m devpi upload --from-dir ${WORKSPACE}\\dist"
                            try {
                                bat "${tool 'CPython-3.6'} -m devpi upload --only-docs --from-dir ${WORKSPACE}\\dist"
                            } catch (exc) {
                                echo "Unable to upload to devpi with docs."
                            }
                        }
                    }
                }
            }
        }
        stage("Test DevPi packages") {
            when {
                allOf{
                    equals expected: true, actual: params.DEPLOY_DEVPI
                    anyOf {
                        equals expected: "master", actual: env.BRANCH_NAME
                        equals expected: "dev", actual: env.BRANCH_NAME
                    }
                }
            }

            // when {
            //     expression { params.DEPLOY_DEVPI == true && (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "dev")}
            // }
            parallel {
                stage("Source Distribution: .tar.gz") {
                    agent {
                        node {
                            label "Windows && Python3"
                        }
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    steps {
                        bat "${tool 'CPython-3.6'} -m venv venv"
                        bat "venv\\Scripts\\pip.exe install tox devpi-client"
                        script {
                            withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                                    bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                                    bat "venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                                    echo "Testing Source package in devpi"
                                    bat "venv\\Scripts\\devpi.exe test --index https://devpi.library.illinois.edu/${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging ${name} -s tar.gz"
                            }
                        }
                    }
                }
                stage("Source Distribution: .zip") {
                    agent {
                        node {
                            label "Windows && Python3"
                        }
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    steps {
                        bat "${tool 'CPython-3.6'} -m venv venv"
                        bat "venv\\Scripts\\pip.exe install tox devpi-client"
                        script {
                            // def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                            // def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                            withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                                bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                            }

                            bat "venv\\Scripts\\devpi.exe use /DS_Jenkins/${env.BRANCH_NAME}_staging"
                            echo "Testing Source package in devpi"
                            bat "venv\\Scripts\\devpi.exe test --index https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}_staging ${name} -s zip"
                        }
                    }
                }
                stage("Built Distribution: .whl") {
                    agent {
                        node {
                            label "Windows && Python3"
                        }
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    steps {
                        bat "${tool 'CPython-3.6'} -m venv venv"
                        bat "venv\\Scripts\\pip.exe install tox devpi-client"
                        script {
                            withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                                bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                            }
                        }
                        bat "venv\\Scripts\\devpi.exe use /DS_Jenkins/${env.BRANCH_NAME}_staging"
                        echo "Testing Whl package in devpi"
                        bat "venv\\Scripts\\devpi.exe test --index https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}_staging ${name} -s whl --verbose"
                    }
                }
            }
            post {
                success {
                    echo "it Worked. Pushing file to ${env.BRANCH_NAME} index"
                    script {
                        // def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                        // def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                        withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                            bat "devpi login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                            
                        }
                    }
                    bat "devpi use /DS_Jenkins/${env.BRANCH_NAME}_staging"
                    bat "devpi push ${name}==${version} DS_Jenkins/${env.BRANCH_NAME}"

                }
            }
        }
        stage("Deploy"){
            parallel {
                stage("Deploy Online Documentation") {
                    when{
                        equals expected: true, actual: params.DEPLOY_DOCS
                    }
                    steps{
                        script {
                            if(!params.BUILD_DOCS){
                                bat "pipenv run python setup.py build_sphinx"
                            }
                        }
                        
                        dir("build/docs/html/"){
                            input 'Update project documentation?'
                            sshPublisher(
                                publishers: [
                                    sshPublisherDesc(
                                        configName: 'apache-ns - lib-dccuser-updater', 
                                        sshLabel: [label: 'Linux'], 
                                        transfers: [sshTransfer(excludes: '', 
                                        execCommand: '', 
                                        execTimeout: 120000, 
                                        flatten: false, 
                                        makeEmptyDirs: false, 
                                        noDefaultExcludes: false, 
                                        patternSeparator: '[, ]+', 
                                        remoteDirectory: "${params.DEPLOY_DOCS_URL_SUBFOLDER}", 
                                        remoteDirectorySDF: false, 
                                        removePrefix: '', 
                                        sourceFiles: '**')], 
                                    usePromotionTimestamp: false, 
                                    useWorkspaceInPromotion: false, 
                                    verbose: true
                                    )
                                ]
                            )
                        }
                    }
                }
                stage("Deploy standalone to Hathi tools Beta"){
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_HATHI_TOOL_BETA
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE
                        }
                    }
                    steps {
                        unstash "msi"
                        input 'Update standalone to //storage.library.illinois.edu/HathiTrust/Tools/beta/?'
                        cifsPublisher(
                                    publishers: [[
                                        configName: 'hathitrust tools', 
                                        transfers: [[
                                            cleanRemote: false, 
                                            excludes: '', 
                                            flatten: false, 
                                            makeEmptyDirs: false, 
                                            noDefaultExcludes: false, 
                                            patternSeparator: '[, ]+', 
                                            remoteDirectory: 'beta', 
                                            remoteDirectorySDF: false, 
                                            removePrefix: '', 
                                            sourceFiles: '*.msi'
                                            ]], 
                                        usePromotionTimestamp: false, 
                                        useWorkspaceInPromotion: false, 
                                        verbose: false
                                        ]]
                                )
                    }
                }
                stage("Deploy to DevPi Production") {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION
                            equals expected: true, actual: params.DEPLOY_DEVPI
                            branch "master"
                        }
                    }
                    steps {
                        script {
                            // def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                            // def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                            input "Release ${name} ${version} to DevPi Production?"
                            withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                                bat "devpi login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                                bat "devpi use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                                bat "devpi push ${name}==${version} production/release"
                            }
                        }
                    }
                }
                stage("Deploy Standalone Build to SCCM") {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_SCCM
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE
                            branch "master"
                        }
                        // expression { params.RELEASE == "Release_to_devpi_and_sccm"}
                    }

                    steps {
                        unstash "msi"
                        script{
                            // def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                            def msi_files = findFiles glob: '*.msi'

                            def deployment_request = requestDeploy yaml: "deployment.yml", file_name: msi_files[0]
                            cifsPublisher(
                                publishers: [[
                                    configName: 'SCCM Staging', 
                                    transfers: [[
                                        cleanRemote: false, 
                                        excludes: '', 
                                        flatten: false, 
                                        makeEmptyDirs: false, 
                                        noDefaultExcludes: false, 
                                        patternSeparator: '[, ]+', 
                                        remoteDirectory: '', 
                                        remoteDirectorySDF: false, 
                                        removePrefix: '', 
                                        sourceFiles: '*.msi'
                                        ]], 
                                    usePromotionTimestamp: false, 
                                    useWorkspaceInPromotion: false, 
                                    verbose: false
                                    ]]
                                )

                            // deployStash("msi", "${env.SCCM_STAGING_FOLDER}/${name}/")
                            
                            input("Deploy to production?")
                            writeFile file: "deployment_request.txt", text: deployment_request
                            echo deployment_request
                            cifsPublisher(
                                publishers: [[
                                    configName: 'SCCM Upload', 
                                    transfers: [[
                                        cleanRemote: false, 
                                        excludes: '', 
                                        flatten: false, 
                                        makeEmptyDirs: false, 
                                        noDefaultExcludes: false, 
                                        patternSeparator: '[, ]+', 
                                        remoteDirectory: '', 
                                        remoteDirectorySDF: false, 
                                        removePrefix: '', 
                                        sourceFiles: '*.msi'
                                        ]], 
                                    usePromotionTimestamp: false, 
                                    useWorkspaceInPromotion: false, 
                                    verbose: false
                                    ]]
                            )
                            // deployStash("msi", "${env.SCCM_UPLOAD_FOLDER}")
                        }
                    }
                    post {
                        success {
                            archiveArtifacts artifacts: "deployment_request.txt"
                        }
                    }
                }
            }
        }

    }
    post {
        failure {
            echo "Failed!"
            // deleteDir()
            // cleanWs(patterns: [[pattern: 'source', type: 'EXCLUDE'], [pattern: 'pipenv', type: 'EXCLUDE']])
            // bat "pipenv uninstall --all"
            // bat "pipenv run pipenv-resolver --clear"

        }

        cleanup {
            // dir("source"){
            //     bat "pipenv run python setup.py clean --all"
            // }
            
        
            dir('dist') {
                deleteDir()
            }
            dir('build') {
                deleteDir()
            }
            script {
                if (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "dev"){
                    // def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                    // def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                    
                    withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                        bat "devpi login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                        bat "devpi use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                        try {
                            bat "devpi remove -y ${name}==${version}"
                        } catch (Exception ex) {
                            echo "Failed to remove ${name}==${version} from ${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                        }   
                    }

                }
            }
            bat "dir"
        }
    }
}
