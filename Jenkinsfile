#!groovy
@Library("ds-utils@v0.2.3") // Uses library from https://github.com/UIUCLibrary/Jenkins_utils
import org.ds.*

@Library("devpi") _

def PKG_VERSION = "unknown"
def PKG_NAME = "unknown"
def CMAKE_VERSION = "cmake3.12"
def JIRA_ISSUE = ""
def DOC_ZIP_FILENAME = "doc.zip"
//                                    script{
////                                        def generator_list = []
////                                        if(params.PACKAGE_WINDOWS_STANDALONE_MSI){
////                                            generator_list << "WIX"
////                                        }
////                                        echo "${generator_list.toString()}"
//                                        def generator_argument = ${params.PACKAGE_WINDOWS_STANDALONE_PACKAGE_GENERATOR}
//                                    }
def check_jira(){
    script {
        // def result = jiraSearch "issue = $params.JIRA_ISSUE"
        // jiraComment body: 'Just a test', issueKey: 'PSR-83'
        def jira_project = jiraGetProject idOrKey: 'PSR', site: 'https://bugs.library.illinois.edu'
        echo "result = ${jira_project.data.toString()}"
        JIRA_ISSUE = jiraGetIssue idOrKey: "${params.JIRA_ISSUE_VALUE}", site: 'https://bugs.library.illinois.edu'
        echo "result = ${JIRA_ISSUE}"
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
def generate_cpack_arguments(BuildWix=true, BuildNSIS=true, BuildZip=true){
    script{
        def cpack_generators = []

        if(BuildWix){
            cpack_generators << "WIX"
        }

        if(BuildNSIS){
            cpack_generators << "NSIS"
        }
        if(BuildZip){
            cpack_generators << "ZIP"
        }
        return "${cpack_generators.join(";")}"
    }

}

def capture_ctest_results(PATH){
    script {

        def glob_expression = "${PATH}/*.xml"

        archiveArtifacts artifacts: "${glob_expression}"
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
                    pattern: "${glob_expression}",
                    skipNoTestFiles: false,
                    stopProcessingIfError: true
                    )
                ]
//        def ctest_results = findFiles glob: "${glob_expression}"
//        ctest_results.each{ ctest_result ->
//            bat "del ${ctest_result}"
//        }
//        dir("${PATH}"){
//            deleteDir()
//        }
    }
}
def cleanup_workspace(){
    dir("logs"){
        echo "Cleaning out logs directory"
        deleteDir()
        bat "dir > nul"
    }

    dir("build"){
        echo "Cleaning out build directory"
        deleteDir()
        bat "dir > nul"
    }

    dir("dist"){
        echo "Cleaning out dist directory"
        deleteDir()
        bat "dir > nul"
    }
}

pipeline {
    agent {
        label "Windows && Python3 && longfilenames && WIX"
    }
    triggers {
        cron('@daily')
    }
    options {
        disableConcurrentBuilds()  //each branch has 1 job running at a time
//        timeout(25)  // Timeout after 20 minutes. This shouldn't take this long but it hangs for some reason
        checkoutToSubdirectory("source")
        buildDiscarder logRotator(artifactDaysToKeepStr: '10', artifactNumToKeepStr: '10')
        preserveStashes(buildCount: 5)
    }
    environment {
        PIPENV_CACHE_DIR="${WORKSPACE}\\..\\.virtualenvs\\cache\\"
        WORKON_HOME ="${WORKSPACE}\\pipenv\\"
        build_number = VersionNumber(projectStartDate: '2017-11-08', versionNumberString: '${BUILD_DATE_FORMATTED, "yy"}${BUILD_MONTH, XX}${BUILDS_THIS_MONTH, XXX}', versionPrefix: '', worstResultForIncrement: 'SUCCESS')
        PIPENV_NOSPIN = "True"
//        DEVPI_JENKINS_PASSWORD=credentials('DS_devpi')
        // pytest_args = "--junitxml=reports/junit-{env:OS:UNKNOWN_OS}-{envname}.xml --junit-prefix={env:OS:UNKNOWN_OS}  --basetemp={envtmpdir}"
    }
    parameters {
        booleanParam(name: "FRESH_WORKSPACE", defaultValue: false, description: "Purge workspace before staring and checking out source")
        // string(name: "PROJECT_NAME", defaultValue: "Speedwagon", description: "Name given to the project")
        string(name: 'JIRA_ISSUE_VALUE', defaultValue: "PSR-83", description: 'Jira task to generate about updates.')
        // file description: 'Build with alternative requirements.txt file', name: 'requirements.txt'
        booleanParam(name: "TEST_RUN_PYTEST", defaultValue: true, description: "Run PyTest unit tests")
        booleanParam(name: "TEST_RUN_BEHAVE", defaultValue: true, description: "Run Behave unit tests")
        booleanParam(name: "TEST_RUN_DOCTEST", defaultValue: true, description: "Test documentation")
        booleanParam(name: "TEST_RUN_FLAKE8", defaultValue: true, description: "Run Flake8 static analysis")
        booleanParam(name: "TEST_RUN_MYPY", defaultValue: true, description: "Run MyPy static analysis")
        booleanParam(name: "TEST_RUN_TOX", defaultValue: true, description: "Run Tox Tests")
        booleanParam(name: "PACKAGE_PYTHON_FORMATS", defaultValue: true, description: "Create native Python packages")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_MSI", defaultValue: true, description: "Create a standalone wix based .msi installer")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_NSIS", defaultValue: false, description: "Create a standalone NULLSOFT NSIS based .exe installer")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_ZIP", defaultValue: false, description: "Create a standalone portable package")

        booleanParam(name: "DEPLOY_DEVPI", defaultValue: true, description: "Deploy to DevPi on https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: "DEPLOY_DEVPI_PRODUCTION", defaultValue: false, description: "Deploy to https://devpi.library.illinois.edu/production/release")
        booleanParam(name: "DEPLOY_HATHI_TOOL_BETA", defaultValue: false, description: "Deploy standalone to \\\\storage.library.illinois.edu\\HathiTrust\\Tools\\beta\\")
        booleanParam(name: "DEPLOY_SCCM", defaultValue: false, description: "Request deployment of MSI installer to SCCM")
        booleanParam(name: "DEPLOY_DOCS", defaultValue: false, description: "Update online documentation")
        string(name: 'DEPLOY_DOCS_URL_SUBFOLDER', defaultValue: "speedwagon", description: 'The directory that the docs should be saved under')
    }

    stages {
        stage("Configure"){
            stages{
                stage("Purge all existing data in workspace"){
                    when{
                        equals expected: true, actual: params.FRESH_WORKSPACE
                    }
                    steps{
                        deleteDir()
                        dir("source"){
                           checkout scm
                        }
                    }
                }
                stage("Testing Jira epic"){
                    agent any
                    steps {
                        echo "Finding Jira epic ${params.JIRA_ISSUE_VALUE}"
                        check_jira()

                    }

                }
                stage("Cleanup"){
                    steps {
                        cleanup_workspace()
                        dir("source") {
                            stash includes: 'deployment.yml', name: "Deployment"
                        }
                    }
                }
                stage("Install Python system dependencies"){
                    steps{

                        lock("system_python_${env.NODE_NAME}"){
                            bat "${tool 'CPython-3.6'} -m pip install pip --upgrade --quiet && ${tool 'CPython-3.6'} -m pip list > logs/pippackages_system_${env.NODE_NAME}.log"
                        }
                        bat "${tool 'CPython-3.6'} -m venv venv && venv\\Scripts\\pip.exe install tox devpi-client"


                    }
                    post{
                        always{
                            archiveArtifacts artifacts: "logs/pippackages_system_*.log"
                        }
                        failure {
                            deleteDir()
                        }
                        cleanup{
                            cleanWs(patterns: [[pattern: "logs/pippackages_system_*.log", type: 'INCLUDE']])
                        }
                    }
                }
                stage("Setting project metadata variables"){
                    steps{
                        script {
                            dir("source"){
                                PKG_NAME = bat(returnStdout: true, script: "@${tool 'CPython-3.6'}  setup.py --name").trim()
                                PKG_VERSION = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                                DOC_ZIP_FILENAME = "${PKG_NAME}-${PKG_VERSION}.doc.zip"
                            }
                        }
                    }
                }
                stage("Installing Pipfile"){
                    options{
                        timeout(5)
                    }
                    steps {
                        dir("source"){
                            bat "pipenv install --dev --deploy && pipenv run pip list > ..\\logs\\pippackages_pipenv_${NODE_NAME}.log"
                            bat "pipenv check"

                        }
                    }
                    post{
                        always{
                            archiveArtifacts artifacts: "logs/pippackages_pipenv_*.log"
                        }
                        failure {
                            deleteDir()
                        }
                        cleanup{
                            cleanWs(patterns: [[pattern: "logs/pippackages_pipenv_*.log", type: 'INCLUDE']])
                        }
                    }
                }
            }
        }
        stage('Build') {
            parallel {
                stage("Python Package"){
                    steps {

//                        tee('logs/build.log') {
                        dir("source"){
                            lock("system_pipenv_${NODE_NAME}"){
                                powershell "& ${tool 'CPython-3.6'} -m pipenv run python setup.py build -b ${WORKSPACE}\\build | tee ${WORKSPACE}\\logs\\build.log"
                            }
                            // bat script: "${tool 'CPython-3.6'} -m pipenv run python setup.py build -b ${WORKSPACE}\\build"
//                            }
                        }
                    }
                    post{
                        always{
                            archiveArtifacts artifacts: "logs/build.log"
                            recordIssues enabledForFailure: true, tools: [[name: 'Setuptools Build', pattern: 'logs/build.log', tool: pyLint()]]
//                            scanForIssues pattern: 'logs/build.log', reportEncoding: '', sourceCodeEncoding: '', tool: pyLint()
//                            warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'Pep8', pattern: 'logs/build.log']]
                            // bat "dir build"
                        }
                        cleanup{
                            cleanWs(patterns: [[pattern: 'logs/build.log', type: 'INCLUDE']])
                        }
                    }
                }
                stage("Sphinx documentation"){
                    steps {
                        echo "Building docs on ${env.NODE_NAME}"
//                        tee('logs/build_sphinx.log') {
                        dir("source"){
                            lock("system_pipenv_${NODE_NAME}"){
                                powershell "& ${tool 'CPython-3.6'} -m pipenv run python setup.py build_sphinx --build-dir ${WORKSPACE}\\build\\docs | tee ${WORKSPACE}\\logs\\build_sphinx.log"
                            }
                        }
//                        }
                    }
                    post{
                        always {
//                            warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'Pep8', pattern: 'logs/build_sphinx.log']]
//                            scanForIssues pattern: 'logs/build_sphinx.log', reportEncoding: '', sourceCodeEncoding: '', tool: pep8()
                            recordIssues enabledForFailure: true, tools: [[name: 'Sphinx Documentation Build', pattern: 'logs/build_sphinx.log', tool: pep8()]]
                            archiveArtifacts artifacts: 'logs/build_sphinx.log'
                        }
                        success{
                            publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'build/docs/html', reportFiles: 'index.html', reportName: 'Documentation', reportTitles: ''])
                            zip archive: true, dir: "${WORKSPACE}/build/docs/html", glob: '', zipFile: "dist/${DOC_ZIP_FILENAME}"
                            stash includes: "dist/${DOC_ZIP_FILENAME},build/docs/html/**", name: 'DOCS_ARCHIVE'

                        }
                        cleanup{
                            cleanWs(patterns:
                                    [
                                        [pattern: 'logs/build_sphinx.log', type: 'INCLUDE'],
                                        [pattern: "dist/${DOC_ZIP_FILENAME}", type: 'INCLUDE']
                                    ]
                                )
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
                            bat "pipenv run coverage run --parallel-mode --source=speedwagon -m behave --junit --junit-directory ${WORKSPACE}\\reports\\behave"
                        }
                    }
                    post {
                        always {
                            junit "reports/behave/*.xml"
                        }
                    }
                }
                stage("Run PyTest Unit Tests"){
                    when {
                       equals expected: true, actual: params.TEST_RUN_PYTEST
                    }
                    environment{
                        junit_filename = "junit-${env.NODE_NAME}-${env.GIT_COMMIT.substring(0,7)}-pytest.xml"
                    }
                    steps{
                        dir("source"){
                            bat "pipenv run coverage run --parallel-mode --source=speedwagon -m pytest --junitxml=${WORKSPACE}/reports/pytest/${junit_filename} --junit-prefix=${env.NODE_NAME}-pytest"
                        }
                    }
                    post {
                        always {
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
                            bat "pipenv run sphinx-build -b doctest docs\\source ${WORKSPACE}\\build\\docs -d ${WORKSPACE}\\build\\docs\\doctrees"
                        }
                        dir("reports"){
                            bat "move ${WORKSPACE}\\build\\docs\\output.txt doctest.txt"
                        }
                    }
                    post{
                        always {
                            bat "dir ${WORKSPACE}\\reports"
                            archiveArtifacts artifacts: "reports/doctest.txt"
                        }
                        cleanup{
                            cleanWs(patterns: [[pattern: 'reports/doctest.txt', type: 'INCLUDE']])
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
//                                tee('logs/mypy.log') {
                                dir("source"){
                                    bat "pipenv run mypy -p speedwagon --html-report ${WORKSPACE}\\reports\\mypy\\html > ${WORKSPACE}\\logs\\mypy.log"
//                                    powershell "& pipenv run mypy -p speedwagon --html-report ${WORKSPACE}\\reports\\mypy\\html | tee ${WORKSPACE}\\logs\\mypy.log"
                                }
//                                }
                            } catch (exc) {
                                echo "MyPy found some warnings"
                            }

                        }
                    }
                    post {
                        always {
                            bat "type ${WORKSPACE}\\logs\\mypy.log"
                            archiveArtifacts "logs\\mypy.log"
//                            warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'MyPy', pattern: 'logs/mypy.log']], unHealthy: ''
//                            scanForIssues pattern: 'logs/mypy.log', reportEncoding: '', sourceCodeEncoding: '', tool: myPy(), blameDisabled: true

                            recordIssues enabledForFailure: true, tools: [[name: 'MyPy', pattern: "logs/mypy.log", tool: myPy()]]
                            publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/mypy/html/', reportFiles: 'index.html', reportName: 'MyPy HTML Report', reportTitles: ''])
                        }
                        cleanup{
                            cleanWs(patterns: [[pattern: 'logs/mypy.log', type: 'INCLUDE']])
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
                                dir("source"){
                                    bat "pipenv run flake8 speedwagon --tee --output-file=${WORKSPACE}\\logs\\flake8.log"
                                }
//                                }
                            } catch (exc) {
                                echo "flake8 found some warnings"
                            }
                        }
                    }
                    post {
                        always {
//                            scanForIssues pattern: 'logs/flake8.log', reportEncoding: '', sourceCodeEncoding: '', tool: pyLint()
                              archiveArtifacts 'logs/flake8.log'

                              recordIssues enabledForFailure: true, tools: [[name: 'Flake8', pattern: 'logs/flake8.log', tool: flake8()]]
//                                recordIssues enabledForFailure: true, tools: [[name: 'Flake8', pattern: 'source/*.py', tool: flake8()]]

//                            warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'PyLint', pattern: 'logs/flake8.log']], unHealthy: ''
                        }
                        cleanup{
                            cleanWs(patterns: [[pattern: 'logs/flake8.log', type: 'INCLUDE']])
                        }
                    }
                }
            }
            post{
                always{
                    dir("source"){
                        bat "pipenv run coverage combine"
                        bat "pipenv run coverage xml -o ${WORKSPACE}\\reports\\coverage.xml"
                        bat "pipenv run coverage html -d ${WORKSPACE}\\reports\\coverage"

                    }
                    publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: "reports/coverage", reportFiles: 'index.html', reportName: 'Coverage', reportTitles: ''])
                    publishCoverage adapters: [
                                    coberturaAdapter('reports/coverage.xml')
                                    ],
                                sourceFileResolver: sourceFiles('STORE_ALL_BUILD')
                }
                cleanup{
                    cleanWs(patterns: [
                            [pattern: 'reports/coverage.xml', type: 'INCLUDE'],
                            [pattern: 'reports/coverage', type: 'INCLUDE'],
                            [pattern: 'source/.coverage', type: 'INCLUDE']
                        ])
//                    cleanWs(patterns: [[pattern: 'reports/coverage', type: 'INCLUDE']])
//                    cleanWs(patterns: [[pattern: 'source/.coverage', type: 'INCLUDE']])

                }
            }
        }
        stage("Packaging") {
            failFast true
            parallel {
                stage("Source and Wheel formats"){
                    when {
                        equals expected: true, actual: params.PACKAGE_PYTHON_FORMATS
                    }
                    stages{

                        stage("Packaging sdist and wheel"){

                            steps{
                                dir("source"){
                                    bat script: "pipenv run python setup.py sdist -d ${WORKSPACE}\\dist bdist_wheel -d ${WORKSPACE}\\dist"
                                }
                            }
                            post {
                                success {
                                    archiveArtifacts artifacts: "dist/*.whl,dist/*.tar.gz,dist/*.zip", fingerprint: true
                                    stash includes: "dist/*.whl,dist/*.tar.gz,dist/*.zip", name: 'PYTHON_PACKAGES'
                                }
                                cleanup{
                                    cleanWs deleteDirs: true, patterns: [[pattern: 'dist/*.whl,dist/*.tar.gz,dist/*.zip', type: 'INCLUDE']]
//                                    remove_files("dist/*.whl,dist/*.tar.gz,dist/*.zip")
                                }
                            }
                        }
                    }
                }
                stage("Windows Standalone"){
                    agent {
                        node {
                            label "Windows && Python3 && longfilenames && WIX"
                            customWorkspace "c:/Jenkins/temp/${JOB_NAME}/standalone_build"
                        }
                    }

//                    environment {
//                        PIPENV_CACHE_DIR="${WORKSPACE}\\pipenvcache\\"
//                        WORKON_HOME ="${WORKSPACE}\\pipenv\\"
//                    }

                    when{
                        anyOf{
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                        }
                    }
                    stages{
                        stage("CMake Build"){
                            options{
                                timeout(5)
                            }
                            steps {
//                                tee("${workspace}/logs/standalone_cmake_build.log") {
                                dir("cmake_build") {
                                    bat "dir > nul"
                                }
                                cmakeBuild buildDir: 'cmake_build',
                                    cleanBuild: true,
                                    cmakeArgs: "--config Release --parallel ${NUMBER_OF_PROCESSORS} -DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=${WORKSPACE}/python_deps_cache -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv -DPYTHON_EXECUTABLE=${tool 'CPython-3.6'} -DCTEST_DROP_LOCATION=${WORKSPACE}/logs/ctest -- -flp:logfile=${WORKSPACE}/logs/cmake-msbuild.log;verbosity=Normal",
                                    generator: 'Visual Studio 14 2015 Win64',
                                    installation: "${CMAKE_VERSION}",
                                    sourceDir: 'source',
                                    steps: [[withCmake: true]]

//                                    cmake arguments: "--build . --config Release --parallel ${NUMBER_OF_PROCESSORS}", installation: "${CMAKE_VERSION}"
//                                }
//                                }
                            }
                            post{
                                always{
                                    archiveArtifacts artifacts: "logs/cmake-msbuild.log"
                                    recordIssues enabledForFailure: true, tools: [[name: 'Standalone Builds Warnings', pattern: "logs/cmake-msbuild.log", tool: msBuild()]]
                                }
//                                    warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'MSBuild', pattern: "${workspace}/logs/standalone_cmake_build.log"]]
                                }
//                            }
                        }
                        stage("CTest"){
                            options{
                                timeout(3)
                            }
                            environment{
                                TMPDIR = "${WORKSPACE}/temp"
                            }
                            steps {
                                dir("${WORKSPACE}/temp"){
                                    bat "dir > nul"
                                }
                                dir("logs/ctest"){
                                    bat "dir"
                                }
                                    ctest(
                                        arguments: "-T test -C Release -j ${NUMBER_OF_PROCESSORS}",
                                        installation: "${CMAKE_VERSION}",
                                        workingDir: 'cmake_build'
                                        )


//                                    }
//                                }
                            }
                            post{
                                always {
                                    ctest(
                                        arguments: "-T submit",
                                        installation: "${CMAKE_VERSION}",
                                        workingDir: 'cmake_build'
                                        )
                                    capture_ctest_results("logs/ctest")

//                                    archiveArtifacts artifacts: 'logs/standalone_cmake_test.log', allowEmptyArchive: true
//                                    warnings canRunOnFailed: true, parserConfigurations: [[parserName: 'MSBuild', pattern: 'logs/standalone_cmake_test.log']]
                                }
                                cleanup{
                                    cleanWs deleteDirs: true, patterns: [
                                            [pattern: 'logs/ctest', type: 'INCLUDE'],
                                            [pattern: 'logs/standalone*.log', type: 'INCLUDE']
                                        ]
                                }

                            }

                        }
                        stage("CPack"){
                            options{
                                timeout(10)
                            }
                            steps {
//                                dir("cmake_build") {
//                                    script{
                                cpack(
                                    arguments: "-C Release -G ${generate_cpack_arguments(params.PACKAGE_WINDOWS_STANDALONE_MSI, params.PACKAGE_WINDOWS_STANDALONE_NSIS, params.PACKAGE_WINDOWS_STANDALONE_ZIP)} --config cmake_build/CPackConfig.cmake -B ${WORKSPACE}/dist -V",
                                    installation: "${CMAKE_VERSION}"
                                )
//                                    }
//                                }
                            }
                            post {
                                success{
                                    archiveArtifacts artifacts: "dist/*.msi,dist/*.exe,dist/*.zip", fingerprint: true
//                                    script{
//                                        def install_files = findFiles glob: "dist/standalone/*.msi,dist/standalone/*.exe,dist/standalone/*.zip"
//                                        install_files.each { installer_file ->
//                                            echo "Found ${installer_file}"
//                                            archiveArtifacts artifacts: "${installer_file}", fingerprint: true
//                                        }
//                                    }
                                    stash includes: "dist/*.msi,dist/*.exe,dist/*.zip", name: "STANDALONE_INSTALLERS"
//                                    }
                                }
                                always{
                                    dir("cmake_build"){
                                        archiveArtifacts allowEmptyArchive: true, artifacts: "**/wix.log"
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
                                        } catch (exc) {
                                            echo "read the wix logs."
                                        }
                                        dir("cmake_build"){
                                            cmake arguments: "--build . --target clean", installation: "${CMAKE_VERSION}"
                                        }
                                    }
                                }
                                cleanup{
                                    cleanWs deleteDirs: true, patterns: [[pattern: 'dist', type: 'INCLUDE']]
                                }

                            }
                        }
                    }
                    post {
                        cleanup{
                            dir("cmake_build"){
                                cmake arguments: "--build . --config Release --target clean", installation: "${CMAKE_VERSION}"
                            }
                        }
                    }
                }
            }


        }
        stage("Deploy to Devpi Staging") {
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
                unstash 'DOCS_ARCHIVE'
                unstash 'PYTHON_PACKAGES'
                unstash 'STANDALONE_INSTALLERS'
                dir("source"){
                    bat "devpi use https://devpi.library.illinois.edu"
                    withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                        bat "${tool 'CPython-3.6'} -m devpi login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD} && ${tool 'CPython-3.6'} -m devpi use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                    }
                    script {
                        bat "${tool 'CPython-3.6'} -m devpi upload --from-dir ${WORKSPACE}\\dist"
                        try {
                            bat "${tool 'CPython-3.6'} -m devpi upload --only-docs --from-dir ${WORKSPACE}\\dist\\${DOC_ZIP_FILENAME}"
                        } catch (exc) {
                            echo "Unable to upload to devpi with docs."
                        }
                    }
//                    }
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
            options{
                timestamps()
            }
            parallel {
                stage("Source Distribution: .tar.gz") {
                    agent {
                        node {
                            label "Windows && Python3"
                        }
                    }
                    environment{
                        TMPDIR = "${WORKSPACE}\\tmp"
                    }
                    options {
                        skipDefaultCheckout(true)

                    }
                    steps {
                            lock("system_python_${NODE_NAME}"){
                                bat "${tool 'CPython-3.6'} -m venv venv"
                            }

                            bat "venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip.exe install setuptools --upgrade && venv\\Scripts\\pip.exe install tox detox devpi-client"
                            lock("${BUILD_TAG}_${NODE_NAME}"){
                                timeout(10){
                                    bat "venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu/${env.BRANCH_NAME}_staging"
                                    devpiTest(
                                        devpiExecutable: "venv\\Scripts\\devpi.exe",
                                        url: "https://devpi.library.illinois.edu",
                                        index: "${env.BRANCH_NAME}_staging",
                                        pkgName: "${PKG_NAME}",
                                        pkgVersion: "${PKG_VERSION}",
                                        pkgRegex: "tar.gz",
                                        detox: false
                                    )
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
                            lock("system_python_${NODE_NAME}"){
                                bat "${tool 'CPython-3.6'} -m venv venv"
                            }
                            bat "venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip.exe install setuptools --upgrade && venv\\Scripts\\pip.exe install tox detox devpi-client"
                            lock("${BUILD_TAG}_${NODE_NAME}"){
                                timeout(10){
                                    devpiTest(
                                        devpiExecutable: "venv\\Scripts\\devpi.exe",
                                        url: "https://devpi.library.illinois.edu",
                                        index: "${env.BRANCH_NAME}_staging",
                                        pkgName: "${PKG_NAME}",
                                        pkgVersion: "${PKG_VERSION}",
                                        pkgRegex: "zip",
                                        detox: false
                                    )
                                }
                            }
//                        }

//                        devpi_login("venv\\Scripts\\devpi.exe", 'DS_devpi', "https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}_staging", "${WORKSPACE}\\certs\\")
////                        script {
////                            withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
////                                bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
////                            }
////
////                        }
////                        bat "venv\\Scripts\\devpi.exe use /DS_Jenkins/${env.BRANCH_NAME}_staging  --clientdir ${WORKSPACE}\\certs\\"
//                        bat "venv\\Scripts\\devpi.exe test --index https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}_staging ${PKG_NAME} -s zip --clientdir ${WORKSPACE}\\certs\\"
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
                        lock("system_python_${NODE_NAME}"){
                            bat "${tool 'CPython-3.6'} -m pip install pip --upgrade && ${tool 'CPython-3.6'} -m venv venv "
                        }
                        bat "venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip.exe install setuptools --upgrade && venv\\Scripts\\pip.exe install tox detox devpi-client"
                        lock("${BUILD_TAG}_${NODE_NAME}"){
                            timeout(5){
                                devpiTest(
                                    devpiExecutable: "venv\\Scripts\\devpi.exe",
                                    url: "https://devpi.library.illinois.edu",
                                    index: "${env.BRANCH_NAME}_staging",
                                    pkgName: "${PKG_NAME}",
                                    pkgVersion: "${PKG_VERSION}",
                                    pkgRegex: "whl",
                                    detox: false
                                )
                            }
                        }
                    }
                    post{
                        failure{
                            cleanWs deleteDirs: true, patterns: [[pattern: 'venv', type: 'INCLUDE']]
                        }
                    }
                }
            }
            post {
                success {
                    echo "it Worked. Pushing file to ${env.BRANCH_NAME} index"
                        bat "venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu/${env.BRANCH_NAME}_staging"
                        withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                            bat "devpi login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD} && venv\\Scripts\\devpi.exe use http://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}_staging && venv\\Scripts\\devpi.exe push ${PKG_NAME}==${PKG_VERSION} DS_Jenkins/${env.BRANCH_NAME}"

                        }
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
                        unstash "DOCS_ARCHIVE"

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
                    post{
                        success{
                            jiraComment body: "Documentation updated. https://www.library.illinois.edu/dccdocs/${params.DEPLOY_DOCS_URL_SUBFOLDER}", issueKey: "${params.JIRA_ISSUE_VALUE}"
                        }
                    }
                }
                stage("Deploy standalone to Hathi tools Beta"){
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_HATHI_TOOL_BETA
                            anyOf{
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                            }
                        }

                    }
                    agent{
                        node{
                            label "Windows"
                        }
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    steps {
                        unstash "STANDALONE_INSTALLERS"
                        script{
                            dir("dist"){
                                def installer_files  = findFiles glob: '*.msi,*.exe,*.zip'
                                input "Update standalone ${installer_files} to //storage.library.illinois.edu/HathiTrust/Tools/beta/?"

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
                                                sourceFiles: "*.msi,*.exe,*.zip",
        //                                            sourceFiles: "*.msi,*.exe,*.zip",
                                                ]],
                                            usePromotionTimestamp: false,
                                            useWorkspaceInPromotion: false,
                                            verbose: false
                                            ]]
                                    )
                                    jiraComment body: "Added \"${installer_files}\" to //storage.library.illinois.edu/HathiTrust/Tools/beta/", issueKey: "${params.JIRA_ISSUE_VALUE}"

                            }
                        }


                    }
                    post{
                        cleanup{

                            cleanWs deleteDirs: true, patterns: [[pattern: 'dist/*.*', type: 'INCLUDE']]
                        }
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
                        input "Release ${PKG_NAME} ${PKG_VERSION} to DevPi Production?"
                        withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                            bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD} && venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging && venv\\Scripts\\devpi.exe push ${PKG_NAME}==${PKG_VERSION} production/release"
                        }
                    }
                    post{
                        success{
                            jiraComment body: "Version ${PKG_VERSION} was added to https://devpi.library.illinois.edu/production/release index.", issueKey: "${params.JIRA_ISSUE_VALUE}"
                        }
                    }
                }
                stage("Deploy Standalone Build to SCCM") {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_SCCM
                            // equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE
                            anyOf{
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                            }
                            branch "master"
                        }
                        // expression { params.RELEASE == "Release_to_devpi_and_sccm"}
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    steps {
                        unstash "STANDALONE_INSTALLERS"
                        unstash "Deployment"
                        script{
                            // def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                            dir("dist"){
                                def msi_files = findFiles glob: '*.msi'
                                def deployment_request = requestDeploy yaml: "${WORKSPACE}/deployment.yml", file_name: msi_files[0]

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
                                jiraComment body: "Version ${PKG_VERSION} sent to staging for user testing.", issueKey: "${params.JIRA_ISSUE_VALUE}"
                                input("Deploy to production?")
                                writeFile file: "${WORKSPACE}/logs/deployment_request.txt", text: deployment_request
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
                            }

                            // deployStash("msi", "${env.SCCM_UPLOAD_FOLDER}")
                        }
                    }
                    post {
                        success {
                            jiraComment body: "Deployment request was sent to SCCM for version ${PKG_VERSION}.", issueKey: "${params.JIRA_ISSUE_VALUE}"
                            archiveArtifacts artifacts: "logs/deployment_request.txt"
                        }
                    }
                }
            }
        }

    }
    post {
        failure {
//            echo "Failed!"

            script{
                def help_info = "Pipeline failed. If the problem is old cached data, you might need to purge the testing environment. Try manually running the pipeline again with the parameter FRESH_WORKSPACE checked."
                echo "${help_info}"
                if (env.BRANCH_NAME == "master"){
                    emailext attachLog: true, body: "${help_info}\n${JOB_NAME} has current status of ${currentBuild.currentResult}. Check attached logs or ${JENKINS_URL} for more details.", recipientProviders: [developers()], subject: "${JOB_NAME} Regression"
                }
            }
//            bat "tree /A /F"
        }
        cleanup {
             dir("source"){
                 bat "pipenv run python setup.py clean --all"
             }




            script {
                if (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "dev"){
                    // def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                    // def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()

                    withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                        try {
                            bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD} && venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging && devpi remove -y ${PKG_NAME}==${PKG_VERSION}"
                        } catch (Exception ex) {
                            echo "Failed to remove ${PKG_NAME}==${PKG_VERSION} from ${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                        }
                    }

                }
            }
            cleanWs deleteDirs: true, patterns: [
                    [pattern: 'logs', type: 'INCLUDE'],
                    [pattern: 'dist', type: 'INCLUDE'],
                    [pattern: 'build', type: 'INCLUDE'],
                    [pattern: 'reports', type: 'INCLUDE'],
                ]
        }

    }
}
