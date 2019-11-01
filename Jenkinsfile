#!groovy
@Library("ds-utils@v0.2.3") // Uses library from https://github.com/UIUCLibrary/Jenkins_utils
import org.ds.*
import static groovy.json.JsonOutput.* // For pretty printing json data

@Library(["devpi", "PythonHelpers"]) _
def CMAKE_VERSION = "cmake3.13"

def get_package_version(stashName, metadataFile){
    ws {
        unstash "${stashName}"
        script{
            def props = readProperties interpolate: true, file: "${metadataFile}"
            deleteDir()
            return props.Version
        }
    }
}

def get_package_name(stashName, metadataFile){
    ws {
        unstash "${stashName}"
        script{
            def props = readProperties interpolate: true, file: "${metadataFile}"
            deleteDir()
            return props.Name
        }
    }
}

def run_sonarScanner(){
    withSonarQubeEnv(installationName: "sonarqube.library.illinois.edu") {
        bat(
            label: "Running sonar scanner",
            script: '\
"%scannerHome%/bin/sonar-scanner" \
-D"sonar.projectBaseDir=%WORKSPACE%/source" \
-D"sonar.python.coverage.reportPaths=%WORKSPACE%/reports/coverage.xml" \
-D"sonar.python.xunit.reportPath=%WORKSPACE%/reports/tests/pytest/%junit_filename%" \
-D"sonar.working.directory=%WORKSPACE%\\.scannerwork" \
-X'
        )

    }
    script{
        def sonarqube_result = waitForQualityGate(abortPipeline: false)
        if (sonarqube_result.status != 'OK') {
            unstable "SonarQube quality gate: ${sonarqube_result.status}"
        }

        def outstandingIssues = get_sonarqube_unresolved_issues(".scannerwork/report-task.txt")
        writeJSON file: 'reports/sonar-report.json', json: outstandingIssues

    }
}

def check_jira_issue(issue, outputFile){
    script{
        def issue_response = jiraGetIssue idOrKey: issue, site: 'bugs.library.illinois.edu'
        try{
            def input_data = readJSON text: toJson(issue_response.data)
            writeJSON file: outputFile, json: input_data
            archiveArtifacts allowEmptyArchive: true, artifacts: outputFile
        }
        catch (Exception ex) {
            echo "Unable to create ${outputFile}. Reason: ${ex}"
        }
    }
}

def deploy_hathi_beta(){
    unstash "STANDALONE_INSTALLERS"
    unstash "DOCS_ARCHIVE"
    unstash "DIST-INFO"
    script{
        def props = readProperties interpolate: true, file: 'speedwagon.dist-info/METADATA'
        deploy_artifacts_to_url('dist/*.msi,dist/*.exe,dist/*.zip,dist/docs/*.pdf', "https://jenkins.library.illinois.edu/nexus/repository/prescon-beta/speedwagon/${props.Version}/", params.JIRA_ISSUE_VALUE)
    }
}

def run_cmake_build(){
    bat """if not exist "cmake_build" mkdir cmake_build
if not exist "logs" mkdir logs
if not exist "logs\\ctest" mkdir logs\\ctest
if not exist "temp" mkdir temp
"""
    bat "C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat -no_logo -arch=amd64 -host_arch=amd64 && cd ${WORKSPACE}\\source && cmake -B ${WORKSPACE}\\cmake_build -G Ninja -DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=c:\\wheel_cache -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv -DPYTHON_EXECUTABLE=\"${powershell(script: '(Get-Command python).path', returnStdout: true).trim()}\"  -DSPEEDWAGON_DOC_PDF=${WORKSPACE}/dist/docs/speedwagon.pdf"
    bat "C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat -no_logo -arch=amd64 -host_arch=amd64 && cd ${WORKSPACE}\\cmake_build && cmake --build ."
}


def process_mypy_logs(path){
    archiveArtifacts "${path}"
    stash includes: "${path}", name: "MYPY_LOGS"
    node("Windows"){
        checkout scm
        unstash "MYPY_LOGS"
        recordIssues(tools: [myPy(pattern: "${path}")])
        deleteDir()
    }
}
def check_jira_project(project, outputFile){

    script {

        def jira_project = jiraGetProject idOrKey: project, site: 'bugs.library.illinois.edu'
        try{
            def input_data = readJSON text: toJson(jira_project.data)
            writeJSON file: outputFile, json: input_data
            archiveArtifacts allowEmptyArchive: true, artifacts: outputFile
        }
        catch (Exception ex) {
            echo "Unable to create ${outputFile}. Reason: ${ex}"
        }
    }
}
def check_jira(project, issue){
    check_jira_project(project, 'logs/jira_project_data.json')
    check_jira_issue(issue, "logs/jira_issue_data.json")

}

def build_sphinx(){
        bat "if not exist logs mkdir logs"
        dir("source"){
            bat(
                label: "Building HTML docs on ${env.NODE_NAME}",
                script: "python -m pipenv run sphinx-build docs/source ${WORKSPACE}\\build\\docs\\html -d ${WORKSPACE}\\build\\docs\\.doctrees -w ${WORKSPACE}\\logs\\build_sphinx.log"
                )
            bat(
                label: "Building LaTex docs on ${env.NODE_NAME}",
                script: "python -m pipenv run sphinx-build docs/source ..\\build\\docs\\latex -b latex -d ${WORKSPACE}\\build\\docs\\.doctrees -w ${WORKSPACE}\\logs\\build_sphinx_latex.log"
                )
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
    }
}

def get_sonarqube_unresolved_issues(report_task_file){
    script{

        def props = readProperties  file: '.scannerwork/report-task.txt'
        def response = httpRequest url : props['serverUrl'] + "/api/issues/search?componentKeys=" + props['projectKey'] + "&resolved=no"
        def outstandingIssues = readJSON text: response.content
        return outstandingIssues
    }
}

def remove_from_devpi(devpiExecutable, pkgName, pkgVersion, devpiIndex, devpiUsername, devpiPassword){
    script {
                try {
                    bat "${devpiExecutable} login ${devpiUsername} --password ${devpiPassword}"
                    bat "${devpiExecutable} use ${devpiIndex}"
                    bat "${devpiExecutable} remove -y ${pkgName}==${pkgVersion}"
                } catch (Exception ex) {
                    echo "Failed to remove ${pkgName}==${pkgVersion} from ${devpiIndex}"
            }

    }
}

def report_help_info(){
    script{
        def help_info = "Pipeline failed. If the problem is old cached data, you might need to purge the testing environment. Try manually running the pipeline again with the parameter FRESH_WORKSPACE checked."
        echo "${help_info}"
        if (env.BRANCH_NAME == "master"){
            emailext attachLog: true, body: "${help_info}\n${JOB_NAME} has current status of ${currentBuild.currentResult}. Check attached logs or ${JENKINS_URL} for more details.", recipientProviders: [developers()], subject: "${JOB_NAME} Regression"
        }
    }
}
def get_build_number(){
    script{
        def versionPrefix = ""

        if(currentBuild.getBuildCauses()[0].shortDescription == "Started by timer"){
            versionPrefix = "Nightly"
        }

        return VersionNumber(projectStartDate: '2017-11-08', versionNumberString: '${BUILD_DATE_FORMATTED, "yy"}${BUILD_MONTH, XX}${BUILDS_THIS_MONTH, XXX}', versionPrefix: '', worstResultForIncrement: 'SUCCESS')
    }
}


def runtox(){
    script{
        withEnv(
            [
                'PIP_INDEX_URL="https://devpi.library.illinois.edu/production/release"',
                'PIP_TRUSTED_HOST="devpi.library.illinois.edu"',
                'TOXENV="py"'
            ]
        ) {

            bat "python -m pip install pipenv tox"
            try{
                // Don't use result-json=${WORKSPACE}\\logs\\tox_report.json because
                // Tox has a bug that fails when trying to write the json report
                // when --parallel is run at the same time
                bat "tox -p=auto -o -vv --workdir ${WORKSPACE}\\.tox"
            } catch (exc) {
                bat "tox -vv --workdir ${WORKSPACE}\\.tox --recreate"
            }
        }
    }

}
def deploy_to_nexus(filename, deployUrl, credId){
    script{
        withCredentials([usernamePassword(credentialsId: credId, passwordVariable: 'nexusPassword', usernameVariable: 'nexusUsername')]) {
             bat(
                 label: "Deploying ${filename} to ${deployUrl}",
                 script: "curl -v --upload ${filename} ${deployUrl} -u %nexusUsername%:%nexusPassword%"
             )
        }
    }
}
def deploy_artifacts_to_url(regex, urlDestination, jiraIssueKey){
    script{
        def installer_files  = findFiles glob: 'dist/*.msi,dist/*.exe,dist/*.zip'
        def simple_file_names = []

        installer_files.each{
            simple_file_names << it.name
        }


        input "Update standalone ${simple_file_names.join(', ')} to '${urlDestination}'? More information: ${currentBuild.absoluteUrl}"

        def new_urls = []
        try{
            installer_files.each{
                def deployUrl = "${urlDestination}" + it.name
                  deploy_to_nexus(it, deployUrl, "jenkins-nexus")
                  new_urls << deployUrl
            }
        } finally{
            def url_message_list = new_urls.collect{"* " + it}.join("\n")
            def jira_message = """The following beta file(s) are now available:
${url_message_list}
"""
            echo "${jira_message}"
            jiraComment body: "${jira_message}", issueKey: "${jiraIssueKey}"
        }
    }
}

def deploy_sscm(file_glob, pkgVersion, jiraIssueKey){
    script{
        def msi_files = findFiles glob: "${file_glob}"
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

        jiraComment body: "Version ${pkgVersion} sent to staging for user testing.", issueKey: "${jiraIssueKey}"
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

def postLogFileOnPullRequest(title, filename){
    script{
        if (env.CHANGE_ID){
            def log_file = readFile filename
            if(log_file.length() == 0){
                return
            }

            pullRequest.comment("""${title}
${log_file}
"""
            )
        }
    }
}


def testPythonPackages(pkgRegex, testEnvs, pipcache){
    script{
        def taskData = []
        def pythonPkgs = findFiles glob: pkgRegex

        pythonPkgs.each{ fileName ->
            testEnvs.each{ testEnv->

                testEnv['images'].each{ dockerImage ->
                    taskData.add(
                        [
                            file: fileName,
                            dockerImage: dockerImage,
                            label: testEnv['label']
                        ]
                    )
                }
            }
        }
        def taskRunners = [:]
        taskData.each{
            taskRunners["Testing ${it['file']} with ${it['dockerImage']}"]={
                //node(it['label']){
                ws{
                    try{
                        def testImage = docker.image(it['dockerImage']).inside("-v ${pipcache}:c:/pipcache"){
                            echo "Testing ${it['file']} with ${it['dockerImage']}"
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                            bat "if not exist pipcache mkdir pipcache"
                            powershell(
                                label: "Installing Certs required to download python dependencies",
                                script: "certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst"
                                )
                            bat "pip config --user set global.download-cache c:/pipcache"
                            bat(
                                script: "pip install tox",
                                label: "Installing Tox"
                            )
                            bat(
                                label:"Running tox tests with ${it['file']}",
                                script:"tox -c tox.ini --installpkg=${it['file']} -e py -vv"
                                )

                        }
                    }
                    finally{
                        cleanWs(
                            deleteDirs: true,
                            patterns: [[pattern: 'pipcache/**', type: 'EXCLUDE']]
                            )
                    }
                }

            }
        }
        parallel taskRunners
    }
}

def testMsiInstall(dockerfilePath, dockerImageName, dockerContainerName, logsPath){
    unstash 'STANDALONE_INSTALLERS'
    dir(logsPath){
        bat "dir > nul"
    }
    script{
         withEnv([
            "DOCKER_IMAGE_NAME=${dockerImageName.toLowerCase()}",
            "DOCKER_CONTAINER_NAME=${dockerContainerName.toLowerCase()}",
            "DOCKER_LOGS_PATH=${logsPath}"
            ]){
            bat(
                label: "Build Windows Docker Container",
                script: "docker build  -t %DOCKER_IMAGE_NAME% -f ${dockerfilePath} ./source "
                )
            try{

                def dockerSha = powershell(
                    label: "Run Docker Container with ${logsPath} mounted",
                    script: 'docker run -d -t -v "$((Get-Location).Path)\\$($env:DOCKER_LOGS_PATH):c:\\logs" -v "$((Get-Location).Path)\\dist:c:\\dist" --name $($env:DOCKER_CONTAINER_NAME) $($env:DOCKER_IMAGE_NAME)',
                    returnStdout: true
                ).trim()

                bat(
                    label: "Run install script",
                    script: "docker exec ${dockerSha} powershell.exe -executionpolicy bypass -file c:/scripts/run_install.ps1"
                )

            } finally {
                bat(
                    label: "Stopping ${DOCKER_CONTAINER_NAME} container",
                    returnStatus: true,
                    script: "docker stop --time=1 ${DOCKER_CONTAINER_NAME}"
                    )

                bat(
                    label: "Removing ${DOCKER_CONTAINER_NAME} container",
                    returnStatus: true,
                    script: "docker rm ${DOCKER_CONTAINER_NAME}"
                    )

            }
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
        checkoutToSubdirectory("source")
        buildDiscarder logRotator(artifactDaysToKeepStr: '10', artifactNumToKeepStr: '10')
        preserveStashes(buildCount: 5)
    }
    environment {
        PIPENV_CACHE_DIR="${WORKSPACE}\\..\\.virtualenvs\\cache\\"
        WORKON_HOME ="${WORKSPACE}\\pipenv"
        build_number = get_build_number()
        PIPENV_NOSPIN = "True"
    }
    parameters {
        booleanParam(name: "FRESH_WORKSPACE", defaultValue: false, description: "Purge workspace before staring and checking out source")
        string(name: 'JIRA_ISSUE_VALUE', defaultValue: "PSR-83", description: 'Jira task to generate about updates.')
        booleanParam(name: "TEST_RUN_TOX", defaultValue: true, description: "Run Tox Tests")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_MSI", defaultValue: false, description: "Create a standalone wix based .msi installer")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_NSIS", defaultValue: false, description: "Create a standalone NULLSOFT NSIS based .exe installer")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_ZIP", defaultValue: false, description: "Create a standalone portable package")

        booleanParam(name: "DEPLOY_DEVPI", defaultValue: false, description: "Deploy to DevPi on https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: "DEPLOY_DEVPI_PRODUCTION", defaultValue: false, description: "Deploy to https://devpi.library.illinois.edu/production/release")

        booleanParam(name: "DEPLOY_HATHI_TOOL_BETA", defaultValue: false, description: "Deploy standalone to https://jenkins.library.illinois.edu/nexus/service/rest/repository/browse/prescon-beta/")
        booleanParam(name: "DEPLOY_SCCM", defaultValue: false, description: "Request deployment of MSI installer to SCCM")
        booleanParam(name: "DEPLOY_DOCS", defaultValue: false, description: "Update online documentation")
        string(name: 'DEPLOY_DOCS_URL_SUBFOLDER', defaultValue: "speedwagon", description: 'The directory that the docs should be saved under')
    }

    stages {

        stage("Configure"){
            // environment{
            //    PATH = "${tool 'CPython-3.6'};${tool 'CPython-3.6'}\\Scripts;${PATH}"
            //}
            stages{
                stage("Initial setup"){
                    parallel{
                        //stage("Purge all existing data in workspace"){
                        //    when{
                        //        anyOf{
                        //            equals expected: true, actual: params.FRESH_WORKSPACE
                        //            triggeredBy "TimerTriggerCause"
                        //        }
                        //    }
                        //    steps{
                        //        deleteDir()
                        //        dir("source"){
                        //           checkout scm
                        //        }
                        //    }
                        //}
                        stage("Testing Jira epic"){
                            agent any
                            options {
                                skipDefaultCheckout(true)

                            }
                            steps {
                                check_jira_project('PSR',, 'logs/jira_project_data.json')
                                check_jira_issue("${params.JIRA_ISSUE_VALUE}", "logs/jira_issue_data.json")

                            }
                            post{
                                cleanup{
                                    cleanWs(patterns: [[pattern: "logs/*.json", type: 'INCLUDE']])
                                }
                            }

                        }
                        stage("Getting Distribution Info"){
                            agent {
                                dockerfile {
                                    filename 'ci\\docker\\python37\\Dockerfile'
                                    dir 'source'
                                    label 'Windows&&Docker'
                                 }
                            }
                            steps{
                                dir("source"){
                                    bat "python setup.py dist_info"
                                }
                            }
                            post{
                                success{
                                    dir("source"){
                                        stash includes: "speedwagon.dist-info/**", name: 'DIST-INFO'
                                        archiveArtifacts artifacts: "speedwagon.dist-info/**"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        stage('Build') {

            parallel {
                stage("Building Python Library"){
                    agent {
                        dockerfile {
                            filename 'ci/docker/python37/Dockerfile'
                            dir 'source'
                            label 'Windows&&Docker'
                          }
                    }
                    steps {
                        bat "if not exist logs mkdir logs"
                        //lock("system_pipenv_${NODE_NAME}"){
                        bat "cd source && pipenv run python setup.py build -b ${WORKSPACE}\\build 2> ${WORKSPACE}\\logs\\build_errors.log"
                        //}
                    }
                    post{
                        always{
                            archiveArtifacts artifacts: "logs/build_errors.log"
                            recordIssues(tools: [pyLint(pattern: 'logs/build_errors.log')])
                        }
                        cleanup{
                            cleanWs(patterns: [[pattern: 'logs/build_errors', type: 'INCLUDE']])
                        }
                        success{
                            stash includes: "build/lib/**", name: 'PYTHON_BUILD_FILES'
                        }
                    }
                }
                stage("Sphinx Documentation"){
                    environment{
                        PKG_NAME = get_package_name("DIST-INFO", "speedwagon.dist-info/METADATA")
                        PKG_VERSION = get_package_version("DIST-INFO", "speedwagon.dist-info/METADATA")
                    }
                    stages{
                        stage("Build Sphinx"){
                            // environment{
                            //     PATH = "${tool 'CPython-3.6'};${tool 'CPython-3.6'}\\Scripts;${PATH}"
                            // }
                            agent {
                                dockerfile {
                                    filename 'ci/docker/python37/Dockerfile'
                                    dir 'source'
                                    label 'Windows&&Docker'
                                  }
                            }
                            steps {
                                build_sphinx()
                            }
                            post{
                                always{
                                    archiveArtifacts artifacts: 'logs/build_sphinx.log,logs/latex/speedwagon.log'
                                    recordIssues(tools: [sphinxBuild(pattern: 'logs/build_sphinx.log')])
                                    postLogFileOnPullRequest("Sphinx build result",'logs/build_sphinx.log')
                                }
                                success{
                                    stash includes: "build/docs/latex/*", name: 'latex_docs'
                                    script{
                                        def DOC_ZIP_FILENAME = "${PKG_NAME}-${PKG_VERSION}.doc.zip"
                                        zip archive: true, dir: "${WORKSPACE}/build/docs/html", glob: '', zipFile: "dist/${DOC_ZIP_FILENAME}"
                                        stash includes: "build/docs/html/**", name: 'SPEEDWAGON_DOC_HTML'
                                    }
                                    publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'build/docs/html', reportFiles: 'index.html', reportName: 'Documentation', reportTitles: ''])
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns:
                                            [
                                                [pattern: "dist", type: 'INCLUDE'],
                                            ]
                                    )
                                }
                            }
                        }
                        stage("Convert to pdf"){
                            agent{
                                dockerfile {
                                    filename 'source/ci/docker/makepdf/lite/Dockerfile'
                                    label "docker && linux"
                                }
                            }
                            steps{
                                unstash "latex_docs"
                                sh "mkdir -p dist/docs"
                                dir("build/docs/latex"){
                                    sh "make"
                                }
                                sh "mv build/docs/latex/*.pdf dist/docs/"
                            }
                            post{
                                success{
                                    stash includes: "dist/docs/*.pdf", name: 'SPEEDWAGON_DOC_PDF'
                                    archiveArtifacts artifacts: "dist/docs/*.pdf"
                                }
                                cleanup{
                                    deleteDir()
                                }
                            }
                        }
                    }
                    post{

                        success{
                            unstash "SPEEDWAGON_DOC_PDF"
                            unstash "SPEEDWAGON_DOC_HTML"
                            stash includes: "dist/*.docs.zip,build/docs/html/**,dist/docs/*.pdf", name: 'DOCS_ARCHIVE'
                        }
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns:
                                    [
                                        [pattern: 'logs/build_sphinx.log', type: 'INCLUDE'],
                                        [pattern: "build/docs/latex", type: 'INCLUDE'],
                                        [pattern: "dist", type: 'INCLUDE'],
                                    ]
                                )
                        }
                    }
                }
            }
        }
        stage("Test") {
            environment{
                //PATH = "${tool 'CPython-3.6'};${tool 'CPython-3.6'}\\Scripts;${PATH}"
                junit_filename = "junit-${env.NODE_NAME}-${env.GIT_COMMIT.substring(0,7)}-pytest.xml"
            }
            agent {
                dockerfile {
                    filename 'ci/docker/python37/Dockerfile'
                    dir 'source'
                    label 'Windows&&Docker'
                  }
            }
            stages{
                stage("Run Tests"){
                    parallel {
                        stage("Run Behave BDD Tests") {
                            steps {
                                bat "if not exist reports mkdir reports"
                                dir("source"){
                                    catchError(buildResult: "UNSTABLE", message: 'Did not pass all Behave BDD tests', stageResult: "UNSTABLE") {
                                        bat "coverage run --parallel-mode --source=speedwagon -m behave --junit --junit-directory ${WORKSPACE}\\reports\\tests\\behave"
                                    }
                                }
                            }
                            post {
                                always {
                                    junit "reports/tests/behave/*.xml"
                                }
                            }
                        }
                        stage("Run PyTest Unit Tests"){
                            steps{
                                bat "if not exist logs mkdir logs"
                                dir("source"){
                                    catchError(buildResult: "UNSTABLE", message: 'Did not pass all pytest tests', stageResult: "UNSTABLE") {
                                        bat "coverage run --parallel-mode --source=speedwagon -m pytest --junitxml=${WORKSPACE}/reports/tests/pytest/${junit_filename} --junit-prefix=${env.NODE_NAME}-pytest"
                                    }
                                }
                            }
                            post {
                                always {
                                    junit "reports/tests/pytest/${junit_filename}"
                                }
                            }
                        }
                        stage("Run Doctest Tests"){
                            steps {
                                dir("source"){
                                    bat "sphinx-build -b doctest docs\\source ${WORKSPACE}\\build\\docs -d ${WORKSPACE}\\build\\docs\\doctrees -w ${WORKSPACE}/logs/doctest.txt"
                                }
                            }
                            post{
                                always {
                                    archiveArtifacts artifacts: "logs/doctest.txt"
                                    postLogFileOnPullRequest("Doctest result",'logs/doctest.txt')
                                }
                                cleanup{
                                    cleanWs(patterns: [[pattern: 'logs/doctest.txt', type: 'INCLUDE']])
                                }
                            }
                        }
                        stage("Run MyPy Static Analysis") {
                            steps{
                                bat "if not exist logs mkdir logs"
                                dir("source"){
                                    catchError(buildResult: "SUCCESS", message: 'MyPy found issues', stageResult: "UNSTABLE") {
                                        bat script: "mypy -p speedwagon --html-report ${WORKSPACE}\\reports\\mypy\\html > ${WORKSPACE}\\logs\\mypy.log"
                                    }
                                }
                            }
                            post {
                                always {
                                    process_mypy_logs("logs/mypy.log")
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
                            environment {
                              PIP_INDEX_URL = "https://devpi.library.illinois.edu/production/release"
                              PIP_TRUSTED_HOST = "devpi.library.illinois.edu"
                              TOXENV = "py"
                            }
                            steps {
                                bat "if not exist logs mkdir logs"
                                dir("source"){
                                    runtox()
                                }
                            }
                            post{
                                always{
                                    archiveArtifacts allowEmptyArchive: true, artifacts: '.tox/py*/log/*.log,.tox/log/*.log'
                                }
                                cleanup{
                                    cleanWs deleteDirs: true, patterns: [
                                        [pattern: '.tox', type: 'INCLUDE']
                                    ]
                                }
                            }
                        }
                        stage("Run Flake8 Static Analysis") {
                            steps{
                                bat "if not exist logs mkdir logs"
                                catchError(buildResult: "SUCCESS", message: 'Flake8 found issues', stageResult: "UNSTABLE") {
                                    bat script: "cd source && flake8 speedwagon --tee --output-file=${WORKSPACE}\\logs\\flake8.log"
                                }
                            }
                            post {
                                always {
                                      archiveArtifacts 'logs/flake8.log'
                                      recordIssues(tools: [flake8(pattern: 'logs/flake8.log')])
                                      postLogFileOnPullRequest("flake8 result",'logs/flake8.log')
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
                                bat "coverage combine && coverage xml -o ${WORKSPACE}\\reports\\coverage.xml && coverage html -d ${WORKSPACE}\\reports\\coverage"
                            }
                            publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: "reports/coverage", reportFiles: 'index.html', reportName: 'Coverage', reportTitles: ''])
                            publishCoverage adapters: [
                                            coberturaAdapter('reports/coverage.xml')
                                            ],
                                        sourceFileResolver: sourceFiles('STORE_ALL_BUILD')
                        }
                    }
                }
                stage("Run Sonarqube Analysis"){
                    when{
                        equals expected: "master", actual: env.BRANCH_NAME
                    }
                   // options{
                   //     timeout(5)
                   // }
                    environment{
                        scannerHome = tool name: 'sonar-scanner-3.3.0', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                        PATH = "${WORKSPACE}\\venv\\Scripts;${PATH}"
                    }
                    steps{
                        run_sonarScanner()
                    }
                    post{
                        always{
                            archiveArtifacts(
                                allowEmptyArchive: true,
                                artifacts: ".scannerwork/report-task.txt"
                            )
                            stash includes: "reports/sonar-report.json", name: 'SONAR_REPORT'
                            archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/sonar-report.json'
                            node('Windows'){
                                checkout scm
                                unstash "SONAR_REPORT"
                                recordIssues(tools: [sonarQube(pattern: 'reports/sonar-report.json')])
                                deleteDir()
                            }
                        }
                    }
                }
            }
            post{
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
                    stages{
                        stage("Packaging sdist and wheel"){
                            agent {
                              docker {
                                image 'python:3.7'
                              }
                            }
                            options{
                                timeout(3)
                            }
                            steps{
                                unstash "PYTHON_BUILD_FILES"
                                dir("source"){
                                    powershell "certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst"
                                    bat "pip install pyqt_distutils"
                                    bat script: "python setup.py build -b ../build sdist -d ../dist --format zip bdist_wheel -d ../dist"
                                }
                            }
                            post{
                                success{
                                    stash includes: "dist/*.whl,dist/*.tar.gz,dist/*.zip", name: 'PYTHON_PACKAGES'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'source', type: 'EXCLUDE']
                                            ]
                                        )
                                }
                            }

                        }
                        stage("Testing Python Packages"){
                            agent {
                                label "windows&&docker"
                            }
                            environment{
                                PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release"
                                PIP_TRUSTED_HOST="devpi.library.illinois.edu"
                            }
                            steps{
                                unstash 'PYTHON_PACKAGES'
                                bat "if not exist pipcache mkdir pipcache"
                                testPythonPackages(
                                    "dist/*.whl,dist/*.tar.gz,dist/*.zip",
                                    [
                                        [
                                            images:
                                                [
                                                    "python:3.6-windowsservercore",
                                                    "python:3.7"
                                                ],
                                            label: "windows&&docker"
                                        ]
                                    ],
                                    "${WORKSPACE}\\pipcache"
                                )
                            }
                            post{
                                cleanup{
                                    cleanWs()
                                }
                            }
                        }
                    }
                    post {
                        success {
                            unstash 'PYTHON_PACKAGES'
                            archiveArtifacts artifacts: "dist/*.whl,dist/*.tar.gz,dist/*.zip", fingerprint: true

                        }
                        cleanup{
                            cleanWs deleteDirs: true, patterns: [[pattern: 'dist/*.whl,dist/*.tar.gz,dist/*.zip', type: 'INCLUDE']]
                        }
                    }
                }
                stage("Windows Standalone"){
                    when{
                        anyOf{
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                            triggeredBy "TimerTriggerCause"
                        }
                    }
                    environment {
                        PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release"
                        PIP_TRUSTED_HOST="devpi.library.illinois.edu"
                    //    PATH = "${tool 'CPython-3.6'};${tool(name: 'WixToolset_311', type: 'com.cloudbees.jenkins.plugins.customtools.CustomTool')};$PATH"
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/windows_standalone/Dockerfile'
                            dir 'source'
                            label 'Windows&&Docker'
                          }
                    }
                    stages{
                        stage("CMake Build"){

                            //options{
                            //    timeout(10)
                            //}
                            steps {
                                unstash "DOCS_ARCHIVE"
                                run_cmake_build()
                            }
                        }
                        stage("CTest"){
                            options{
                                timeout(3)
                            }
                            steps {
                                ctest(
                                    arguments: "-T test -C Release -j ${NUMBER_OF_PROCESSORS}",
                                    installation: 'InSearchPath',
                                    workingDir: 'cmake_build'
                                    )

                            }
                            //post{
                            //    always {
                            //        ctest(
                            //            arguments: "-T submit",
                            //            installation: 'InSearchPath',
                            //            workingDir: 'cmake_build'
                            //            )
                            //        capture_ctest_results("logs/ctest")
                            //    }
                            //}

                        }
                        stage("CPack"){
                            options{
                                timeout(10)
                            }
                            steps {
                                cpack(
                                    arguments: "-C Release -G ${generate_cpack_arguments(params.PACKAGE_WINDOWS_STANDALONE_MSI, params.PACKAGE_WINDOWS_STANDALONE_NSIS, params.PACKAGE_WINDOWS_STANDALONE_ZIP)} --config cmake_build/CPackConfig.cmake -B ${WORKSPACE}/dist -V",
                                    installation: 'InSearchPath'
                                )

                            }
                            post {
                                success{
                                    stash includes: "dist/*.msi,dist/*.exe,dist/*.zip", name: "STANDALONE_INSTALLERS"
                                    archiveArtifacts artifacts: "dist/*.msi,dist/*.exe,dist/*.zip", fingerprint: true

                                }
                                failure {
                                    archiveArtifacts allowEmptyArchive: true, artifacts: "dist/**/wix.log,dist/**/*.wxs"
                                }
                            }
                        }
                    }
                    post {
                        failure {
                            cleanWs(
                                deleteDirs: true,
                                disableDeferredWipeout: true,
                                patterns: [
                                    [pattern: 'standalone_venv ', type: 'INCLUDE'],
                                    [pattern: 'python_deps_cache', type: 'INCLUDE'],

                                    ]
                                )
                            dir("standalone_venv"){
                                deleteDir()
                            }
                        }
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                disableDeferredWipeout: true,
                                patterns: [
                                    [pattern: 'cmake_build', type: 'INCLUDE'],
                                    [pattern: '*@tmp', type: 'INCLUDE'],
                                    [pattern: 'source', type: 'INCLUDE'],
                                    [pattern: 'temp', type: 'INCLUDE'],
                                    [pattern: 'dist', type: 'INCLUDE'],
                                    [pattern: 'logs', type: 'INCLUDE'],
                                    [pattern: 'generatedJUnitFiles', type: 'INCLUDE']
                                ]
                            )
                        }
                    }
                }
            }


        }
        stage("Testing MSI Install"){

            agent {
                label "Docker && Windows && 1903"
            }
            when{
                anyOf{
                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                    triggeredBy "TimerTriggerCause"
                }
            }
            options{
                timeout(3)
                skipDefaultCheckout(true)
            }
            steps{

                checkout scm
                bat "if not exist logs mkdir logs"
                script{
                    unstash 'STANDALONE_INSTALLERS'
                    def docker_image_name = "test-image:${env.BRANCH_NAME}_${currentBuild.number}"
                    try {
                        def testImage = docker.build(docker_image_name, "-f ./ci/docker/test_installation/Dockerfile .")
                        testImage.inside{
                            // Copy log files from c:\\logs in the docker container to workspace\\logs
                            bat "cd ${WORKSPACE}\\logs && copy c:\\logs\\*.log"
                            bat 'dir "%PROGRAMFILES%\\Speedwagon"'
                        }
                    } finally{
                        bat "docker image rm -f ${docker_image_name}"
                    }

                }

            }
            post{
                always{
                    archiveArtifacts(
                        allowEmptyArchive: true,
                        artifacts: "logs/*.log"
                        )
                }
                cleanup{
                    cleanWs()
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
            environment{
                PATH = "${WORKSPACE}\\venv\\Scripts;${tool 'CPython-3.6'};${tool 'CPython-3.6'}\\Scripts;${PATH}"
                DEVPI = credentials("DS_devpi")
                PKG_VERSION = get_package_version("DIST-INFO", "speedwagon.dist-info/METADATA")
                PKG_NAME = get_package_name("DIST-INFO", "speedwagon.dist-info/METADATA")
            }

            stages{

                stage("Deploy to Devpi Staging") {

                    steps {
                        unstash 'DOCS_ARCHIVE'
                        unstash 'PYTHON_PACKAGES'
                        bat "pip install devpi-client && devpi use https://devpi.library.illinois.edu && devpi login %DEVPI_USR% --password %DEVPI_PSW% && devpi use /%DEVPI_USR%/${env.BRANCH_NAME}_staging && devpi upload --from-dir dist"
                    }
                }
                stage("Test DevPi packages") {
                    parallel {
                        stage("Source Distribution: .zip") {
                            agent {
                                node {
                                    label "Windows && Python3 && !Docker"
                                }
                            }
                            options {
                                skipDefaultCheckout(true)
                            }

                            stages{

                                stage("Creating Env for DevPi to test sdist"){
                                    environment{
                                        PATH = "${tool 'CPython-3.6'};${PATH}"
                                    }
                                    steps {
                                        lock("system_python_${NODE_NAME}"){
                                            bat "python -m venv venv && venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip.exe install setuptools --upgrade && venv\\Scripts\\pip.exe install \"tox<3.7\" detox devpi-client"
                                        }
                                    }
                                }
                                stage("Testing sdist"){
                                    environment{
                                        PATH = "${tool 'CPython-3.6'};${tool 'CPython-3.6'}\\Scripts;${tool 'CPython-3.7'};$PATH"
                                    }
                                    options{
                                        timeout(10)
                                    }
                                    steps{
                                        bat "devpi use https://devpi.library.illinois.edu/${env.BRANCH_NAME}_staging"
                                        devpiTest(
                                            devpiExecutable: "${powershell(script: '(Get-Command devpi).path', returnStdout: true).trim()}",
                                            url: "https://devpi.library.illinois.edu",
                                            index: "${env.BRANCH_NAME}_staging",
                                            pkgName: "${PKG_NAME}",
                                            pkgVersion: "${PKG_VERSION}",
                                            pkgRegex: "zip",
                                            detox: false
                                        )
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
                                    label "Windows && Python3 && !Docker"
                                }
                            }
                            options {
                                skipDefaultCheckout(true)
                            }
                            environment{
                                PATH = "${tool 'CPython-3.6'};${tool 'CPython-3.6'}\\Scripts;${tool 'CPython-3.7'};$PATH"
                            }
                            stages{
                                stage("Creating Env for DevPi to test whl"){
                                    steps{
                                        lock("system_python_${NODE_NAME}"){
                                            bat "python -m pip install pip --upgrade && python -m venv venv && venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip.exe install setuptools --upgrade && venv\\Scripts\\pip.exe install \"tox<3.7\"  detox devpi-client"
                                        }
                                    }
                                }
                                stage("Testing Whl"){
                                    options{
                                        timeout(10)
                                    }
                                    steps {
                                        // TODO: Rebuild devpiTest to work with Docker containers
                                        devpiTest(
                                            devpiExecutable: "${powershell(script: '(Get-Command devpi).path', returnStdout: true).trim()}",
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
                            bat(
                                label: "it Worked. Pushing file to ${env.BRANCH_NAME} index",
                                script:"venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu/${env.BRANCH_NAME}_staging && devpi login ${env.DEVPI_USR} --password ${env.DEVPI_PSW} && venv\\Scripts\\devpi.exe use http://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}_staging && venv\\Scripts\\devpi.exe push ${PKG_NAME}==${PKG_VERSION} DS_Jenkins/${env.BRANCH_NAME}"
                            )
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
                        input "Release ${PKG_NAME} ${PKG_VERSION} to DevPi Production?"
                        bat "venv\\Scripts\\devpi.exe login ${env.DEVPI_USR} --password ${env.DEVPI_PSW} && venv\\Scripts\\devpi.exe use /${env.DEVPI_USR}/${env.BRANCH_NAME}_staging && venv\\Scripts\\devpi.exe push ${PKG_NAME}==${PKG_VERSION} production/release"
                    }
                    post{
                        success{
                            jiraComment body: "Version ${PKG_VERSION} was added to https://devpi.library.illinois.edu/production/release index.", issueKey: "${params.JIRA_ISSUE_VALUE}"
                        }
                    }
                }
            }
            post{
                cleanup{
                    remove_from_devpi("venv\\Scripts\\devpi.exe", "${PKG_NAME}", "${PKG_VERSION}", "/${env.DEVPI_USR}/${env.BRANCH_NAME}_staging", "${env.DEVPI_USR}", "${env.DEVPI_PSW}")
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
                        deploy_hathi_beta()
                    }
                    post{
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: '*dist-info', type: 'INCLUDE'],
                                    [pattern: 'dist.*', type: 'INCLUDE']
                                ]
                            )
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
                    environment{
                        PKG_VERSION = get_package_version("DIST-INFO", "speedwagon.dist-info/METADATA")
                        PKG_NAME = get_package_name("DIST-INFO", "speedwagon.dist-info/METADATA")
                    }
                    steps {
                        unstash "STANDALONE_INSTALLERS"
                        unstash "Deployment"
                        dir("dist"){
                            deploy_sscm("*.msi", "${PKG_VERSION}", "${params.JIRA_ISSUE_VALUE}")
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
            report_help_info()
            //dir("source"){
            //    bat "\"${tool 'CPython-3.6'}\\Scripts\\pipenv\" --rm"
            //}
        }
        cleanup {
            cleanWs(
                deleteDirs: true,
                patterns: [
                    [pattern: 'logs', type: 'INCLUDE'],
                    [pattern: '.scannerwork', type: 'INCLUDE'],
                    [pattern: 'source', type: 'INCLUDE'],
                    [pattern: 'dist', type: 'INCLUDE'],
                    [pattern: 'build', type: 'INCLUDE'],
                    [pattern: 'reports', type: 'INCLUDE'],
                    [pattern: '*tmp', type: 'INCLUDE']
                ],

            )
        }

    }
}
