#!groovy
@Library("ds-utils@v0.2.3") // Uses library from https://github.com/UIUCLibrary/Jenkins_utils
import org.ds.*

@Library("devpi") _

def PKG_VERSION = "unknown"
//def PKG_NAME = "unknown"
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
        def item_selected = false
        def default_generator = "WIX"

        if(BuildWix){
            cpack_generators << "WIX"
            item_selected = true
        }

        if(BuildNSIS){
            cpack_generators << "NSIS"
            item_selected = true
        }
        if(BuildZip){
            cpack_generators << "ZIP"
            item_selected = true
        }
        if(item_selected == false){
            cpack_generators << default_generator
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

def get_pkg_name(pythonHomePath){
    node("Python3"){
        checkout scm
        bat "dir"
        script{
            def pkg_name = bat(returnStdout: true, script: "@${pythonHomePath}\\python  setup.py --name").trim()
            deleteDir()
            return pkg_name
        }
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
        PKG_NAME = get_pkg_name("${tool 'CPython-3.6'}")
        DEVPI = credentials("DS_devpi")
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
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_MSI", defaultValue: false, description: "Create a standalone wix based .msi installer")
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
                        anyOf{
                            equals expected: true, actual: params.FRESH_WORKSPACE
                            triggeredBy "TimerTriggerCause"
                        }
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
                            bat "${tool 'CPython-3.6'}\\python -m pip install pip --upgrade --quiet && ${tool 'CPython-3.6'}\\python -m pip list > logs/pippackages_system_${env.NODE_NAME}.log"
                        }
                        bat "${tool 'CPython-3.6'}\\python -m venv venv && venv\\Scripts\\pip.exe install tox devpi-client sphinx==1.6.7"


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
                                PKG_VERSION = bat(returnStdout: true, script: "@${tool 'CPython-3.6'}\\python setup.py --version").trim()
                                DOC_ZIP_FILENAME = "${env.PKG_NAME}-${PKG_VERSION}.doc.zip"
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
                            bat "pipenv install --dev --deploy && pipenv run pip list > ..\\logs\\pippackages_pipenv_${NODE_NAME}.log && pipenv check"

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

                        dir("source"){
                            lock("system_pipenv_${NODE_NAME}"){
                                bat "${tool 'CPython-3.6'}\\python.exe -m pipenv run python setup.py build -b ${WORKSPACE}\\build 2> ${WORKSPACE}\\logs\\build_errors.log"
                            }
                        }
                    }
                    post{
                        always{
                            archiveArtifacts artifacts: "logs/build_errors.log"
                            recordIssues(tools: [pyLint(pattern: 'logs/build_errors.log')])
                        }
                        cleanup{
                            cleanWs(patterns: [[pattern: 'logs/build_errors', type: 'INCLUDE']])
                        }
                    }
                }
                stage("Sphinx Documentation"){
                    steps {
                        echo "Building docs on ${env.NODE_NAME}"
                        dir("source"){
                            lock("system_pipenv_${NODE_NAME}"){
                                bat "${tool 'CPython-3.6'}\\python -m pipenv run python setup.py build_sphinx --build-dir ${WORKSPACE}\\build\\docs 2> ${WORKSPACE}\\logs\\build_sphinx.log & type ${WORKSPACE}\\logs\\build_sphinx.log"
                            }
                        }
                    }
                    post{
                        always {
                            recordIssues(tools: [pep8(pattern: 'logs/build_sphinx.log')])
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
                        dir("source"){
                            bat returnStatus: true, script: "pipenv run mypy -p speedwagon --html-report ${WORKSPACE}\\reports\\mypy\\html > ${WORKSPACE}\\logs\\mypy.log"
                        }
                    }
                    post {
                        always {
                            archiveArtifacts "logs\\mypy.log"
                            recordIssues(tools: [myPy(pattern: 'logs/mypy.log')])

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
                        dir("source"){
                            bat returnStatus: true, script: "pipenv run flake8 speedwagon --tee --output-file=${WORKSPACE}\\logs\\flake8.log"
                        }
                    }
                    post {
                        always {
                              archiveArtifacts 'logs/flake8.log'

                              recordIssues(tools: [flake8(pattern: 'logs/flake8.log')])
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
                        bat "pipenv run coverage combine && pipenv run coverage xml -o ${WORKSPACE}\\reports\\coverage.xml && pipenv run coverage html -d ${WORKSPACE}\\reports\\coverage"

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

                    when{
                        anyOf{
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                            triggeredBy "TimerTriggerCause"
                        }
                    }
                    stages{
                        stage("CMake Build"){
                            options{
                                timeout(5)
                            }
                            steps {
                                bat """if not exist "cmake_build" mkdir cmake_build
                                if not exist "logs" mkdir logs
                                """
                                cmakeBuild buildDir: 'cmake_build',
                                    cleanBuild: true,
                                    cmakeArgs: "--config Release --parallel ${NUMBER_OF_PROCESSORS} -DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=${WORKSPACE}/python_deps_cache -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv -DPYTHON_EXECUTABLE=${tool 'CPython-3.6'}\\python.exe -DCTEST_DROP_LOCATION=${WORKSPACE}/logs/ctest",
                                    generator: 'Visual Studio 14 2015 Win64',
                                    installation: "${CMAKE_VERSION}",
                                    sourceDir: 'source',
                                    steps: [[args: "-- /flp1:warningsonly;logfile=${WORKSPACE}\\logs\\cmake-msbuild.log", withCmake: true]]

                            }
                            post{
                                always{
                                    archiveArtifacts artifacts: "logs/cmake-msbuild.log"
                                    recordIssues(tools: [msBuild(pattern: 'logs/cmake-msbuild.log')])
                                }
                                cleanup{
                                    cleanWs deleteDirs: true, patterns: [[pattern: 'logs/cmake-msbuild.log', type: 'INCLUDE']]
                                }
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
                            }
                            post{
                                always {
                                    ctest(
                                        arguments: "-T submit",
                                        installation: "${CMAKE_VERSION}",
                                        workingDir: 'cmake_build'
                                        )
                                    capture_ctest_results("logs/ctest")
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
                                cpack(
                                    arguments: "-C Release -G ${generate_cpack_arguments(params.PACKAGE_WINDOWS_STANDALONE_MSI, params.PACKAGE_WINDOWS_STANDALONE_NSIS, params.PACKAGE_WINDOWS_STANDALONE_ZIP)} --config cmake_build/CPackConfig.cmake -B ${WORKSPACE}/dist -V",
                                    installation: "${CMAKE_VERSION}"
                                )
                            }
                            post {
                                success{
                                    archiveArtifacts artifacts: "dist/*.msi,dist/*.exe,dist/*.zip", fingerprint: true
                                    stash includes: "dist/*.msi,dist/*.exe,dist/*.zip", name: "STANDALONE_INSTALLERS"
                                }
                                failure {
                                    dir("cmake_build"){
                                        archiveArtifacts allowEmptyArchive: true, artifacts: "**/wix.log"
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
                            cleanWs deleteDirs: true, patterns: [
                                [pattern: 'cmake_build', type: 'INCLUDE'],
                                [pattern: '*@tmp', type: 'INCLUDE'],
                                [pattern: 'temp', type: 'INCLUDE'],
                                [pattern: 'logs', type: 'INCLUDE'],
                                [pattern: 'generatedJUnitFiles', type: 'INCLUDE']
                            ]
                        }
                    }
                }
            }


        }
        stage("Deploy to Devpi"){
            when {
                allOf{
                    anyOf{
                        equals expected: true, actual: params.DEPLOY_DEVPI
                        triggeredBy "TimerTriggerCause"
                    }
                    anyOf {
                        equals expected: "master", actual: env.BRANCH_NAME
                        equals expected: "dev", actual: env.BRANCH_NAME
                    }
                }
            }
            options{
                timestamps()
                }

            stages{

                stage("Deploy to Devpi Staging") {

                    steps {
                        unstash 'DOCS_ARCHIVE'
                        unstash 'PYTHON_PACKAGES'
                        dir("source"){
                            bat "${WORKSPACE}\\venv\\Scripts\\devpi use https://devpi.library.illinois.edu"
                            bat "${WORKSPACE}\\venv\\Scripts\\python -m devpi login ${env.DEVPI_USR} --password ${env.DEVPI_PSW} && ${WORKSPACE}\\venv\\Scripts\\python -m devpi use /${env.DEVPI_USR}/${env.BRANCH_NAME}_staging"
//                            }
                            script {
                                bat "${WORKSPACE}\\venv\\Scripts\\python -m devpi upload --from-dir ${WORKSPACE}\\dist"
                                try {
                                    bat "${WORKSPACE}\\venv\\Scripts\\python -m devpi upload --only-docs --from-dir ${WORKSPACE}\\dist\\${DOC_ZIP_FILENAME}"
                                } catch (exc) {
                                    echo "Unable to upload to devpi with docs."
                                }
                            }
        //                    }
                        }
                    }
                }
                stage("Test DevPi packages") {
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
                            stages{

                                stage("Creating Env for DevPi to test sdist"){
                                    steps {
                                        lock("system_python_${NODE_NAME}"){
                                            bat "${tool 'CPython-3.6'}\\python -m venv venv"
                                        }
                                        bat "venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip.exe install setuptools --upgrade && venv\\Scripts\\pip.exe install tox detox devpi-client"
                                    }
                                }
                                stage("Testing sdist"){
                                    steps{
                                            timeout(10){
                                                bat "venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu/${env.BRANCH_NAME}_staging"
                                                devpiTest(
                                                    devpiExecutable: "venv\\Scripts\\devpi.exe",
                                                    url: "https://devpi.library.illinois.edu",
                                                    index: "${env.BRANCH_NAME}_staging",
                                                    pkgName: "${env.PKG_NAME}",
                                                    pkgVersion: "${PKG_VERSION}",
                                                    pkgRegex: "tar.gz",
                                                    detox: false
                                                )
                                            }
                                    }
                                }

                            }
                            post{
                                cleanup{
                                    cleanWs deleteDirs: true, patterns: [
                                            [pattern: 'certs', type: 'INCLUDE'],
                                            [pattern: '*tmp', type: 'INCLUDE']
                                        ]
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
                            stages{
                                stage("Creating Env for DevPi to test whl"){
                                    steps{
                                        lock("system_python_${NODE_NAME}"){
                                            bat "${tool 'CPython-3.6'}\\python -m pip install pip --upgrade && ${tool 'CPython-3.6'}\\python -m venv venv "
                                        }
                                        bat "venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip.exe install setuptools --upgrade && venv\\Scripts\\pip.exe install tox detox devpi-client"
                                    }
                                }
                                stage("Testing Whl"){
                                    steps {
                                            timeout(10){
                                                devpiTest(
                                                    devpiExecutable: "venv\\Scripts\\devpi.exe",
                                                    url: "https://devpi.library.illinois.edu",
                                                    index: "${env.BRANCH_NAME}_staging",
                                                    pkgName: "${env.PKG_NAME}",
                                                    pkgVersion: "${PKG_VERSION}",
                                                    pkgRegex: "whl",
                                                    detox: false
                                                )
                                        }
                                    }
                                }
                            }


                            post{
                                failure{
                                    cleanWs deleteDirs: true, patterns: [[pattern: 'venv', type: 'INCLUDE']]
                                }
                                cleanup{
                                    cleanWs deleteDirs: true, patterns: [
                                            [pattern: 'certs', type: 'INCLUDE'],
                                            [pattern: '*tmp', type: 'INCLUDE']
                                        ]
                                }
                            }
                        }
                    }
                    post {
                        success {
                            echo "it Worked. Pushing file to ${env.BRANCH_NAME} index"
                                bat "venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu/${env.BRANCH_NAME}_staging"
                                    bat "devpi login ${env.DEVPI_USR} --password ${env.DEVPI_PSW} && venv\\Scripts\\devpi.exe use http://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}_staging && venv\\Scripts\\devpi.exe push ${env.PKG_NAME}==${PKG_VERSION} DS_Jenkins/${env.BRANCH_NAME}"

//                                }
                        }
                    }
                }
                stage("Deploy to DevPi Production") {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION
                            branch "master"
                        }
                    }
                    steps {
                        input "Release ${env.PKG_NAME} ${PKG_VERSION} to DevPi Production?"
                            bat "venv\\Scripts\\devpi.exe login ${env.DEVPI_USR} --password ${env.DEVPI_PSW} && venv\\Scripts\\devpi.exe use /${env.DEVPI_USR}/${env.BRANCH_NAME}_staging && venv\\Scripts\\devpi.exe push ${env.PKG_NAME}==${PKG_VERSION} production/release"
                    }
                    post{
                        success{
                            jiraComment body: "Version ${PKG_VERSION} was added to https://devpi.library.illinois.edu/production/release index.", issueKey: "${params.JIRA_ISSUE_VALUE}"
                        }
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

                stage("Deploy Standalone Build to SCCM") {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_SCCM
                            anyOf{
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                            }
                            branch "master"
                        }
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    steps {
                        unstash "STANDALONE_INSTALLERS"
                        unstash "Deployment"
                        script{
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
            script{
                def help_info = "Pipeline failed. If the problem is old cached data, you might need to purge the testing environment. Try manually running the pipeline again with the parameter FRESH_WORKSPACE checked."
                echo "${help_info}"
                if (env.BRANCH_NAME == "master"){
                    emailext attachLog: true, body: "${help_info}\n${JOB_NAME} has current status of ${currentBuild.currentResult}. Check attached logs or ${JENKINS_URL} for more details.", recipientProviders: [developers()], subject: "${JOB_NAME} Regression"
                }
            }
        }
        cleanup {
             dir("source"){
                 bat "pipenv run python setup.py clean --all"
             }




            script {
                if (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "dev"){
                        try {
                            bat "venv\\Scripts\\devpi.exe login ${env.DEVPI_USR} --password ${env.DEVPI_PSW} && venv\\Scripts\\devpi.exe use /${env.DEVPI_USR}/${env.BRANCH_NAME}_staging && devpi remove -y ${env.PKG_NAME}==${PKG_VERSION}"
                        } catch (Exception ex) {
                            echo "Failed to remove ${env.PKG_NAME}==${PKG_VERSION} from ${env.DEVPI_USR}/${env.BRANCH_NAME}_staging"
                    }

                }
            }
            cleanWs deleteDirs: true, patterns: [
                    [pattern: 'logs', type: 'INCLUDE'],
                    [pattern: 'dist', type: 'INCLUDE'],
                    [pattern: 'build', type: 'INCLUDE'],
                    [pattern: 'reports', type: 'INCLUDE'],
                    [pattern: '*tmp', type: 'INCLUDE']
                ]
        }

    }
}
