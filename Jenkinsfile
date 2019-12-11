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

def build_sphinx_stage(){
    bat "if not exist logs mkdir logs"
    dir("source"){
        bat(label: "Install pipenv",
            script: "python -m pipenv install --dev"
            )
        bat(label: "Run build_ui",
            script: "pipenv run python setup.py build_ui"
            )
        bat(
            label: "Building HTML docs on ${env.NODE_NAME}",
            script: "python -m pipenv run sphinx-build docs/source ${WORKSPACE}\\build\\docs\\html -d ${WORKSPACE}\\build\\docs\\.doctrees --no-color -w ${WORKSPACE}\\logs\\build_sphinx.log"
            )
        bat(
            label: "Building LaTex docs on ${env.NODE_NAME}",
            script: "python -m pipenv run sphinx-build docs/source ..\\build\\docs\\latex -b latex -d ${WORKSPACE}\\build\\docs\\.doctrees --no-color -w ${WORKSPACE}\\logs\\build_sphinx_latex.log"
            )
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
def get_build_number(){
    script{
        def versionPrefix = ""

        if(currentBuild.getBuildCauses()[0].shortDescription == "Started by timer"){
            versionPrefix = "Nightly"
        }

        return VersionNumber(projectStartDate: '2017-11-08', versionNumberString: '${BUILD_DATE_FORMATTED, "yy"}${BUILD_MONTH, XX}${BUILDS_THIS_MONTH, XXX}', versionPrefix: '', worstResultForIncrement: 'SUCCESS')
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
        bat(
            label: "Creating a docker volume for a shared pipcache",
            script: "docker volume create pipcache"
        )
        taskData.each{
            taskRunners["Testing ${it['file']} with ${it['dockerImage']}"]={
                ws{
                    def testImage = docker.image(it['dockerImage']).inside("-v pipcache:C:/Users/ContainerAdministrator/AppData/Local/pip/Cache"){
                        try{
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                            powershell(
                                label: "Installing Certs required to download python dependencies",
                                script: "certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst"
                                )
                            bat(
                                script: "pip install tox",
                                label: "Installing Tox"
                                )
                            bat(
                                label:"Running tox tests with ${it['file']}",
                                script:"tox -c tox.ini --installpkg=${it['file']} -e py -vv"
                                )
                        }finally {
                            cleanWs deleteDirs: true, notFailBuild: true
                        }

                    }
                }

            }
        }
        parallel taskRunners
    }
}


pipeline {
    agent none
    triggers {
       parameterizedCron '@daily % PACKAGE_WINDOWS_STANDALONE_MSI=true; DEPLOY_DEVPI=true; TEST_RUN_TOX=true'
    }
    options {
        disableConcurrentBuilds()  //each branch has 1 job running at a time
        checkoutToSubdirectory("source")
        buildDiscarder logRotator(artifactDaysToKeepStr: '10', artifactNumToKeepStr: '10')
        preserveStashes(buildCount: 5)
    }
    environment {
        build_number = get_build_number()
        PIPENV_NOSPIN = "True"
    }
    parameters {
        string(name: 'JIRA_ISSUE_VALUE', defaultValue: "PSR-83", description: 'Jira task to generate about updates.')
        booleanParam(name: "TEST_RUN_TOX", defaultValue: false, description: "Run Tox Tests")
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
                                checkout scm
                                bat "python setup.py dist_info"
                            }
                            post{
                                success{
                                    stash includes: "speedwagon.dist-info/**", name: 'DIST-INFO'
                                    archiveArtifacts artifacts: "speedwagon.dist-info/**"
                                }
                                cleanup{
                                    cleanWs(deleteDirs: true,
                                            patterns: [[pattern: "source", type: 'EXCLUDE']],
                                            notFailBuild: true
                                        )
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
                        bat "cd source && pipenv run python setup.py build -b ${WORKSPACE}\\build 2> ${WORKSPACE}\\logs\\build_errors.log"
                    }
                    post{
                        always{
                            archiveArtifacts artifacts: "logs/build_errors.log"
                           
                        }
                        cleanup{
                            //cleanWs(patterns: [[pattern: 'logs/build_errors', type: 'INCLUDE']])
                            cleanWs(deleteDirs: true,
                                    patterns: [[pattern: "source", type: 'EXCLUDE']],
                                    notFailBuild: true
                                )
                        }
                        success{
                            stash includes: "build/lib/**", name: 'PYTHON_BUILD_FILES'
                        }
                    }
                }
                stage("Sphinx Documentation"){

                    agent none
                    stages{
                        stage("Build Sphinx"){
                            environment{
                                PKG_NAME = get_package_name("DIST-INFO", "speedwagon.dist-info/METADATA")
                                PKG_VERSION = get_package_version("DIST-INFO", "speedwagon.dist-info/METADATA")
                            }
                            agent {
                                dockerfile {
                                    filename 'ci/docker/python37/Dockerfile'
                                    dir 'source'
                                    label 'Windows&&Docker'
                                  }
                            }
                            steps {
                                build_sphinx_stage()
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
                                        stash includes: "build/docs/html/**,dist/*.doc.zip", name: 'SPEEDWAGON_DOC_HTML'
                                    }
                                    publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'build/docs/html', reportFiles: 'index.html', reportName: 'Documentation', reportTitles: ''])
                                }
                                cleanup{
                                    cleanWs(patterns: [[pattern: 'source', type: 'EXCLUDE']])
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
                }
            }
        }
        stage("Test") {

            agent {
                dockerfile {
                    filename 'ci\\docker\\python37\\Dockerfile'
                    dir 'source'
                    label 'Windows&&Docker'
                  }
            }
            stages{
                stage("Run Tests"){
                    environment{
                        junit_filename = "junit-${env.NODE_NAME}-${env.GIT_COMMIT.substring(0,7)}-pytest.xml"
                    }
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
                                    stash includes: "reports/tests/pytest/*.xml", name: "PYTEST_UNIT_TEST_RESULTS"
                                }
                            }
                        }
                        stage("Run Doctest Tests"){
                            steps {
                                unstash "PYTHON_BUILD_FILES"
                                dir("source"){
                                    bat "python setup.py build_ui && sphinx-build -b doctest docs\\source ${WORKSPACE}\\build\\docs -d ${WORKSPACE}\\build\\docs\\doctrees --no-color -w ${WORKSPACE}/logs/doctest.txt"
                                }
                            }
                            post{
                                always {
                                    archiveArtifacts artifacts: "logs/doctest.txt"
                                    recordIssues(tools: [sphinxBuild(id: 'doctest', pattern: 'logs/doctest.txt')])
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
                                    //process_mypy_logs("logs/mypy.log")
                                    archiveArtifacts "logs/mypy.log"
                                    stash includes: "logs/mypy.log", name: "MYPY_LOGS"
                                    node("Windows"){
                                        checkout scm
                                        unstash "MYPY_LOGS"
                                        recordIssues(tools: [myPy(pattern: "logs/mypy.log")])
                                        deleteDir()
                                    }
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
                        stage("Run Pylint Static Analysis") {
                            steps{
                                bat "if not exist logs mkdir logs"
                                dir("source"){
                                    catchError(buildResult: 'SUCCESS', message: 'Pylint found issues', stageResult: 'UNSTABLE') {
                                        bat(
                                            script: 'pylint speedwagon -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > ..\\reports\\pylint.txt',
                                            label: "Running pylint"
                                        )
                                    }
                                    bat(
                                        script: 'pylint speedwagon  -r n --msg-template="{path}:{module}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > ..\\reports\\pylint_issues.txt',
                                            label: "Running pylint for sonarqube",
                                            returnStatus: true

                                    )
                                }
                            }
                            post{
                                always{
                                    stash includes: "reports/pylint_issues.txt,reports/pylint.txt", name: 'PYLINT_REPORT'
                                    archiveArtifacts allowEmptyArchive: true, artifacts: "reports/pylint.txt"

                                    recordIssues(tools: [pyLint(pattern: 'reports/pylint.txt')])

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
                            stash includes: "reports/coverage.xml", name: "COVERAGE_REPORT_DATA"
                            publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: "reports/coverage", reportFiles: 'index.html', reportName: 'Coverage', reportTitles: ''])
                            publishCoverage adapters: [
                                            coberturaAdapter('reports/coverage.xml')
                                            ],
                                        sourceFileResolver: sourceFiles('STORE_ALL_BUILD')
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
        stage("Run Sonarqube Analysis"){
                    when{
                        equals expected: "master", actual: env.BRANCH_NAME
                    }
                    agent{
                        label "windows"
                    }
                   options{
                       skipDefaultCheckout true
                   //     timeout(5)
                   }
                    environment{
                        scannerHome = tool name: 'sonar-scanner-3.3.0', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
//                        PATH = "${WORKSPACE}\\venv\\Scripts;${PATH}"
                    }
                    steps{
                        checkout scm
                        unstash "COVERAGE_REPORT_DATA"
                        unstash "PYTEST_UNIT_TEST_RESULTS"
                        unstash "PYLINT_REPORT"
                        withSonarQubeEnv(installationName: "sonarqube.library.illinois.edu") {
                            bat(
                                label: "Running sonar scanner",
                                script: '\
                    "%scannerHome%/bin/sonar-scanner" \
                    -D"sonar.projectBaseDir=%WORKSPACE%" \
                    -Dsonar.python.pylint.reportPath=%WORKSPACE%/reports/pylint.txt \
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
                        cleanup{
                            cleanWs(deleteDirs: true,
                                    patterns: [[pattern: 'source', type: 'EXCLUDE']],
                                    notFailBuild: true
                                )
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
                                dockerfile {
                                    filename 'ci/docker/python37/Dockerfile'
                                    dir 'source'
                                    label 'Windows&&Docker'
                                  }
                            }
                            steps{
                                timeout(5){
                                    unstash "PYTHON_BUILD_FILES"
                                    dir("source"){
    //                                    powershell "certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst"
    //                                    bat "python -m pip -upgrade pip && pip install --upgrade setuptools"
    //                                    bat "pip install--upgrade pyqt_distutils wheel"
                                        bat script: "python setup.py build -b ../build sdist -d ../dist --format zip bdist_wheel -d ../dist"
                                    }
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
                }
                stage("Windows Standalone"){
                    when{
                        anyOf{
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                        }
                        beforeAgent true
                    }
                    environment {
                        PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release"
                        PIP_TRUSTED_HOST="devpi.library.illinois.edu"
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

                            steps {
                                unstash "SPEEDWAGON_DOC_PDF"
                                //run_cmake_build()
                                bat """if not exist "cmake_build" mkdir cmake_build
if not exist "logs" mkdir logs
if not exist "logs\\ctest" mkdir logs\\ctest
if not exist "temp" mkdir temp
"""
                                bat "C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat -no_logo -arch=amd64 -host_arch=amd64 && cd ${WORKSPACE}\\source && cmake -B ${WORKSPACE}\\cmake_build -G Ninja -DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=c:\\wheel_cache -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv -DPYTHON_EXECUTABLE=\"${powershell(script: '(Get-Command python).path', returnStdout: true).trim()}\"  -DSPEEDWAGON_DOC_PDF=${WORKSPACE}/dist/docs/speedwagon.pdf"
                                bat "C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat -no_logo -arch=amd64 -host_arch=amd64 && cd ${WORKSPACE}\\cmake_build && cmake --build ."
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
                            cleanWs(deleteDirs: true,
                                    notFailBuild: true
                                )
                            // cleanWs(
                            //     deleteDirs: true,
                            //     disableDeferredWipeout: true,
                            //     patterns: [
                            //         [pattern: 'cmake_build', type: 'INCLUDE'],
                            //         [pattern: '*@tmp', type: 'INCLUDE'],
                            //         [pattern: 'source', type: 'INCLUDE'],
                            //         [pattern: 'temp', type: 'INCLUDE'],
                            //         [pattern: 'dist', type: 'INCLUDE'],
                            //         [pattern: 'logs', type: 'INCLUDE'],
                            //         [pattern: 'generatedJUnitFiles', type: 'INCLUDE']
                            //     ]
                            // )
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
                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                beforeAgent true
            }
            options{
                timeout(5)
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
            agent{
                label "windows && Python3"
            }
            environment{
                PATH = "${WORKSPACE}\\venv\\Scripts;${tool 'CPython-3.6'};${tool 'CPython-3.6'}\\Scripts;${PATH}"
                DEVPI = credentials("DS_devpi")
                PKG_VERSION = get_package_version("DIST-INFO", "speedwagon.dist-info/METADATA")
                PKG_NAME = get_package_name("DIST-INFO", "speedwagon.dist-info/METADATA")
            }
            stages{
                stage("Installing Devpi Client") {
                    steps{
                        bat "python -m venv venv && venv\\Scripts\\python.exe -m pip install pip --upgrade"
                        bat "venv\\Scripts\\pip install devpi-client"
                    }

                }
                stage("Deploy to Devpi Staging") {
                    steps {
                        unstash 'SPEEDWAGON_DOC_HTML'
                        unstash 'PYTHON_PACKAGES'
                        bat "devpi use https://devpi.library.illinois.edu && devpi login %DEVPI_USR% --password %DEVPI_PSW% && devpi use /%DEVPI_USR%/${env.BRANCH_NAME}_staging && devpi upload --from-dir dist"
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
                                    cleanWs(deleteDirs: true,
                                        notFailBuild: true
                                    )
                                    // cleanWs deleteDirs: true, patterns: [
                                    //         [pattern: 'certs', type: 'INCLUDE'],
                                    //         [pattern: '*tmp', type: 'INCLUDE']
                                    //     ]
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
                    agent any
                    steps{
                        unstash "SPEEDWAGON_DOC_HTML"

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
                        unstash "SPEEDWAGON_DOC_PDF"
                        unstash "SPEEDWAGON_DOC_HTML"
                        unstash "DIST-INFO"
                        script{
                            def props = readProperties interpolate: true, file: 'speedwagon.dist-info/METADATA'
                            deploy_artifacts_to_url('dist/*.msi,dist/*.exe,dist/*.zip,dist/docs/*.pdf', "https://jenkins.library.illinois.edu/nexus/repository/prescon-beta/speedwagon/${props.Version}/", params.JIRA_ISSUE_VALUE)
                        }
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
                    agent any
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
}
