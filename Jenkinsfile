#!groovy
// @Library("ds-utils@v0.2.3") // Uses library from https://github.com/UIUCLibrary/Jenkins_utils
import org.ds.*
import static groovy.json.JsonOutput.* // For pretty printing json data

def CMAKE_VERSION = "cmake3.13"
@Library(["devpi", "PythonHelpers"]) _

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
def sanitize_chocolatey_version(version){
    script{
        def dot_to_slash_pattern = '(?<=\\d)\\.?(?=(dev|b|a|rc)(\\d)?)'

//        def rc_pattern = "(?<=\d(\.?))rc((?=\d)?)"
        def dashed_version = version.replaceFirst(dot_to_slash_pattern, "-")

        def beta_pattern = "(?<=\\d(\\.?))b((?=\\d)?)"
        if(dashed_version.matches(beta_pattern)){
            return dashed_version.replaceFirst(beta_pattern, "beta")
        }

        def alpha_pattern = "(?<=\\d(\\.?))a((?=\\d)?)"
        if(dashed_version.matches(alpha_pattern)){
            return dashed_version.replaceFirst(alpha_pattern, "alpha")
        }
        return dashed_version
        return new_version
    }
}

def run_tox(){
    bat "if not exist logs mkdir logs"
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

def run_pylint(){
    bat "if not exist logs mkdir logs"
    catchError(buildResult: 'SUCCESS', message: 'Pylint found issues', stageResult: 'UNSTABLE') {
        bat(
            script: 'pylint speedwagon -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > reports\\pylint.txt',
            label: "Running pylint"
        )
    }
    script{
        if(env.BRANCH_NAME == "master"){
            bat(
                script: 'pylint speedwagon  -r n --msg-template="{path}:{module}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > reports\\pylint_issues.txt',
                label: "Running pylint for sonarqube",
                returnStatus: true
            )
        }
    }
}

def make_chocolatey_distribution(install_file, packageversion, dest){
    script{
        def maintainername = "Henry Borchers"
        def sanitized_packageversion=sanitize_chocolatey_version(packageversion)
        def packageSourceUrl="https://github.com/UIUCLibrary/Speedwagon"
        def installerType='msi'
        def installer = findFiles(glob: "${install_file}")[0]
        def install_file_name = installer.name
        def install_file_path = "${pwd()}\\${installer.path}"
        dir("${dest}"){
            powershell(
                label: "Making chocolatey Package Configuration",
                script: "choco new speedwagon packageversion=${sanitized_packageversion} maintainername='\"${maintainername}\"' packageSourceUrl='${packageSourceUrl}' InstallerType='${installerType}' InstallerFile='${install_file_name}'"
            )
            powershell(
                label: "Adding ${install_file} to package",
                script: "Copy-Item \"${install_file_path}\" -Destination speedwagon\\tools\\"
            )

            powershell(
                label: "Creating Package",
                script: "cd speedwagon; choco pack"
            )
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
        script: "python -m pipenv run sphinx-build docs/source build\\docs\\latex -b latex -d ${WORKSPACE}\\build\\docs\\.doctrees --no-color -w ${WORKSPACE}\\logs\\build_sphinx_latex.log"
        )
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


def test_msi_install(){

    bat "if not exist logs mkdir logs"
    script{

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
def build_standalone(){
    stage("Building Standalone"){

        unstash "SPEEDWAGON_DOC_PDF"
        bat """if not exist "cmake_build" mkdir cmake_build
    if not exist "logs" mkdir logs
    if not exist "logs\\ctest" mkdir logs\\ctest
    if not exist "temp" mkdir temp
    """
    //C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat -no_logo -arch=amd64 -host_arch=amd64
    //cd ${WORKSPACE}\\source && cmake -B ${WORKSPACE}\\cmake_build -G Ninja -DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=c:\\wheel_cache -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv -DPYTHON_EXECUTABLE=\"${powershell(script: '(Get-Command python).path', returnStdout: true).trim()}\"  -DSPEEDWAGON_DOC_PDF=${WORKSPACE}/dist/docs/speedwagon.pdf
    //C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat -no_logo -arch=amd64 -host_arch=amd64 && cd ${WORKSPACE}\\cmake_build && cmake --build .
        script{
            def PYTHON_EXECUTABLE = powershell(script: '(Get-Command python).path', returnStdout: true).trim()
            cmakeBuild(
                buildDir: 'cmake_build',
                cmakeArgs: """-DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=c:\\wheel_cache
        -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv
//         -DPYTHON_EXECUTABLE=\"${PYTHON_EXECUTABLE}\"
        -DSPEEDWAGON_DOC_PDF=${WORKSPACE}/dist/docs/speedwagon.pdf""",
                generator: 'Ninja',
                installation: 'InSearchPath',
                steps: [
                    [withCmake: true]
                ]
            )
        }
    }
    stage("Testing standalone"){

        ctest(
            arguments: "-T test -C Release -j ${NUMBER_OF_PROCESSORS}",
            installation: 'InSearchPath',
            workingDir: 'cmake_build'
            )
    }
    stage("Packaging standalone"){
        script{
            def packaging_msi = false
            if(params.PACKAGE_WINDOWS_STANDALONE_MSI || params.PACKAGE_WINDOWS_STANDALONE_CHOLOCATEY){
                packaging_msi = true
            }
            def cpack_generators = generate_cpack_arguments(packaging_msi, params.PACKAGE_WINDOWS_STANDALONE_NSIS, params.PACKAGE_WINDOWS_STANDALONE_ZIP)
            cpack(
                arguments: "-C Release -G ${cpack_generators} --config cmake_build/CPackConfig.cmake -B ${WORKSPACE}/dist -V",
                installation: 'InSearchPath'
            )
        }
    }
}
pipeline {
    agent none
    triggers {
       parameterizedCron '@daily % PACKAGE_WINDOWS_STANDALONE_MSI=true; DEPLOY_DEVPI=true; TEST_RUN_TOX=true'
    }
    options {
        disableConcurrentBuilds()  //each branch has 1 job running at a time
//        buildDiscarder logRotator(artifactDaysToKeepStr: '10', artifactNumToKeepStr: '10')
        //preserveStashes(buildCount: 5)
    }
    environment {
        build_number = get_build_number()
        PIPENV_NOSPIN = "True"
    }
    libraries {
      lib('devpi')
      lib('PythonHelpers')
    }
    parameters {
        string(name: 'JIRA_ISSUE_VALUE', defaultValue: "PSR-83", description: 'Jira task to generate about updates.')
        booleanParam(name: "TEST_RUN_TOX", defaultValue: false, description: "Run Tox Tests")

        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_MSI", defaultValue: false, description: "Create a standalone wix based .msi installer")

        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_NSIS", defaultValue: false, description: "Create a standalone NULLSOFT NSIS based .exe installer")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_ZIP", defaultValue: false, description: "Create a standalone portable package")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_CHOLOCATEY", defaultValue: false, description: "Create package for the Chocolatey package manager")

        booleanParam(name: "DEPLOY_DEVPI", defaultValue: false, description: "Deploy to DevPi on https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: "DEPLOY_DEVPI_PRODUCTION", defaultValue: false, description: "Deploy to https://devpi.library.illinois.edu/production/release")

        booleanParam(name: "DEPLOY_CHOLOCATEY", defaultValue: false, description: "Deploy to Chocolatey repository")
        booleanParam(name: "DEPLOY_HATHI_TOOL_BETA", defaultValue: false, description: "Deploy standalone to https://jenkins.library.illinois.edu/nexus/service/rest/repository/browse/prescon-beta/")
        booleanParam(name: "DEPLOY_SCCM", defaultValue: false, description: "Request deployment of MSI installer to SCCM")
        booleanParam(name: "DEPLOY_DOCS", defaultValue: false, description: "Update online documentation")
        string(name: 'DEPLOY_DOCS_URL_SUBFOLDER', defaultValue: "speedwagon", description: 'The directory that the docs should be saved under')
    }

    stages {

        stage("Configure"){
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
                                    cleanWs(
                                        deleteDirs: true,
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
                            label 'Windows&&Docker'
                          }
                    }
                    steps {
                        bat "(if not exist logs mkdir logs) && pipenv run python setup.py build -b ${WORKSPACE}\\build 2> ${WORKSPACE}\\logs\\build_errors.log"
                    }
                    post{
                        always{
                            archiveArtifacts artifacts: "logs/build_errors.log"
                        }
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
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
                                    zip archive: true, dir: "${WORKSPACE}/build/docs/html", glob: '', zipFile: "dist/${PKG_NAME}-${PKG_VERSION}.doc.zip"
                                    stash includes: "build/docs/html/**,dist/*.doc.zip", name: 'SPEEDWAGON_DOC_HTML'
                                    publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'build/docs/html', reportFiles: 'index.html', reportName: 'Documentation', reportTitles: ''])
                                }
                                cleanup{
                                    cleanWs(notFailBuild: true)
                                }
                            }
                        }
                        stage("Convert to pdf"){
                            agent{
                                dockerfile {
                                    filename 'ci/docker/makepdf/lite/Dockerfile'
                                    label "docker && linux"
                                }
                            }
                            steps{
                                unstash "latex_docs"
                                sh "mkdir -p dist/docs && cd build/docs/latex && make && cd ${WORKSPACE} && mv build/docs/latex/*.pdf dist/docs/"
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
                                catchError(buildResult: "UNSTABLE", message: 'Did not pass all Behave BDD tests', stageResult: "UNSTABLE") {
                                    bat "coverage run --parallel-mode --source=speedwagon -m behave --junit --junit-directory ${WORKSPACE}\\reports\\tests\\behave"
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
                                catchError(buildResult: "UNSTABLE", message: 'Did not pass all pytest tests', stageResult: "UNSTABLE") {
                                    bat "coverage run --parallel-mode --source=speedwagon -m pytest --junitxml=${WORKSPACE}/reports/tests/pytest/${junit_filename} --junit-prefix=${env.NODE_NAME}-pytest"
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
                                bat "python setup.py build_ui && sphinx-build -b doctest docs\\source ${WORKSPACE}\\build\\docs -d ${WORKSPACE}\\build\\docs\\doctrees --no-color -w ${WORKSPACE}/logs/doctest.txt"
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
                                catchError(buildResult: "SUCCESS", message: 'MyPy found issues', stageResult: "UNSTABLE") {
                                    bat script: "mypy -p speedwagon --html-report ${WORKSPACE}\\reports\\mypy\\html > ${WORKSPACE}\\logs\\mypy.log"
                                }
                            }
                            post {
                                always {
                                    archiveArtifacts "logs/mypy.log"
                                    recordIssues(tools: [myPy(pattern: "logs/mypy.log")])
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
                                run_tox()
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
                                run_pylint()
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
                                    bat script: "(if not exist logs mkdir logs) && flake8 speedwagon --tee --output-file=${WORKSPACE}\\logs\\flake8.log"
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
                            bat "coverage combine && coverage xml -o ${WORKSPACE}\\reports\\coverage.xml && coverage html -d ${WORKSPACE}\\reports\\coverage"
                            stash includes: "reports/coverage.xml", name: "COVERAGE_REPORT_DATA"
                            publishHTML([
                                allowMissing: true,
                                alwaysLinkToLastBuild: false,
                                keepAll: false,
                                reportDir: "reports/coverage",
                                reportFiles: 'index.html',
                                reportName: 'Coverage', reportTitles: ''
                            ])
                            publishCoverage(
                                adapters: [
                                        coberturaAdapter('reports/coverage.xml')
                                    ],
                                sourceFileResolver: sourceFiles('STORE_ALL_BUILD')
                            )
                        }
                    }
                }
            }
            post{
                cleanup{
                    cleanWs(patterns: [
                            [pattern: 'reports/coverage.xml', type: 'INCLUDE'],
                            [pattern: 'reports/coverage', type: 'INCLUDE'],
                            [pattern: '.coverage', type: 'INCLUDE']
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
           }
            environment{
                scannerHome = tool name: 'sonar-scanner-3.3.0', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
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
                    recordIssues(tools: [sonarQube(pattern: 'reports/sonar-report.json')])
                }
                cleanup{
                    cleanWs(deleteDirs: true,
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
                                    label 'Windows&&Docker'
                                  }
                            }
                            steps{
                                timeout(5){
                                    unstash "PYTHON_BUILD_FILES"
                                    bat script: "python setup.py build -b build sdist -d dist --format zip bdist_wheel -d dist"
                                }
                            }
                            post{
                                always{
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
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_CHOLOCATEY
                            equals expected: true, actual: params.DEPLOY_CHOLOCATEY
                        }
                        beforeAgent true
                    }
                    environment {
                        PIP_EXTRA_INDEX_URL="https://devpi.library.illinois.edu/production/release"
                        PIP_TRUSTED_HOST="devpi.library.illinois.edu"
                    }

                    stages{
                        stage("CMake Build"){
                            agent {
                                dockerfile {
                                    filename 'ci/docker/windows_standalone/Dockerfile'
                                    label 'Windows&&Docker'
                                    args "-u ContainerAdministrator"
                                  }
                            }
                            steps {
                                build_standalone()

                            }
                            post {
                                success{
                                    stash includes: "dist/*.msi,dist/*.exe,dist/*.zip", name: "STANDALONE_INSTALLERS"
                                    archiveArtifacts artifacts: "dist/*.msi,dist/*.exe,dist/*.zip", fingerprint: true
                                }
                                failure {
                                    archiveArtifacts allowEmptyArchive: true, artifacts: "dist/**/wix.log,dist/**/*.wxs"
                                }
                                always{
                                    archiveArtifacts(
                                        allowEmptyArchive: true,
                                        artifacts: "logs/*.log"
                                        )
                                }

                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        notFailBuild: true
                                    )
                                }
                            }
                        }
                        stage("Testing MSI Install"){
                            agent {
                              docker {
                                args '-u ContainerAdministrator'
                                image 'mcr.microsoft.com/windows/servercore:ltsc2019'
                                label 'Windows&&Docker'
                              }
                            }

                            when{
                                anyOf{
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_CHOLOCATEY
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                    equals expected: true, actual: params.DEPLOY_CHOLOCATEY
                                }
                                beforeAgent true
                            }
                            options{
                                timeout(15)
                                skipDefaultCheckout(true)
                            }
                            steps{
                                unstash 'STANDALONE_INSTALLERS'
                                script{
                                    def msi_file = findFiles(glob: "dist/*.msi")[0].path
                                    powershell "New-Item -ItemType Directory -Force -Path ${WORKSPACE}\\logs; Write-Host \"Installing ${msi_file}\"; msiexec /i ${msi_file} /qn /norestart /L*v! ${WORKSPACE}\\logs\\msiexec.log"
                                }
                                //test_msi_install()
                            }
                            post {
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        notFailBuild: true
                                    )
                                }
                            }
                        }
                        stage("Package MSI for Chocolatey"){
                            agent {
                                dockerfile {
                                    filename 'ci/docker/chocolatey/Dockerfile'
                                    label 'Windows&&Docker'
                                  }
                            }
                            options{
                                timeout(15)
                            }
                            when{
                                anyOf{
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_CHOLOCATEY
                                    equals expected: true, actual: params.DEPLOY_CHOLOCATEY
                                }
                                beforeAgent true
                            }
                            steps{
                                unstash 'STANDALONE_INSTALLERS'
                                script{
                                    make_chocolatey_distribution(
                                        findFiles(glob: "dist/*.msi")[0],
                                        get_package_version("DIST-INFO", "speedwagon.dist-info/METADATA"),
                                        "chocolatey_package"
                                        )
                                }
                            }
                            post {
                                success{
                                    stash includes: "chocolatey_package/speedwagon/*.nupkg", name: "CHOCOLATEY_PACKAGE"
                                    archiveArtifacts(
                                        allowEmptyArchive: true,
                                        artifacts: "chocolatey_package/speedwagon/*.nupkg"
                                        )
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        notFailBuild: true
                                    )
                                }
                            }
                        }
                        stage("Testing Chocolatey Package: Install"){
                            when{
                                anyOf{
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_CHOLOCATEY
                                    equals expected: true, actual: params.DEPLOY_CHOLOCATEY
                                }
                                beforeAgent true
                            }
                            agent {
                                dockerfile {
                                    filename 'ci/docker/chocolatey/Dockerfile'
                                    args '-u ContainerAdministrator'
                                    label 'Windows&&Docker'
                                  }
                            }
                            steps{
                                unstash "CHOCOLATEY_PACKAGE"
                                bat 'choco install speedwagon -y --pre -dv -s %WORKSPACE%\\chocolatey_package\\speedwagon'
                                bat "speedwagon --version"
                            }
                        }
                    }
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
//            options{
//                timestamps()
//            }
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
                        bat "python -m venv venv && venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip install devpi-client"
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
                                label "Windows && Python3"
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
                                        bat "python -m venv venv && venv\\Scripts\\python.exe -m pip install pip --upgrade && venv\\Scripts\\pip.exe install setuptools --upgrade && venv\\Scripts\\pip.exe install \"tox<3.7\" detox devpi-client"
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
                                cleanup{
                                    cleanWs deleteDirs: true
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
                stage("Deploy to Chocolatey") {
                    when{
                        equals expected: true, actual: params.DEPLOY_CHOLOCATEY
                        beforeInput true
                        beforeAgent true
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/chocolatey/Dockerfile'
                            args '-u ContainerAdministrator'
                            label 'Windows&&Docker'
                          }
                    }
                    input {
                      message 'Select Chocolatey server'
                      parameters {
                        choice choices: ['https://jenkins.library.illinois.edu/nexus/repository/chocolatey-hosted-beta/', 'https://jenkins.library.illinois.edu/nexus/repository/chocolatey-hosted-public/'], description: 'Chocolatey Server to deploy to', name: 'CHOCOLATEY_SERVER'
                        credentials credentialType: 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl', defaultValue: 'NEXUS_NUGET_API_KEY', description: 'Nuget API key for Chocolatey', name: 'CHOCO_REPO_KEY', required: true
                      }
                    }
                    steps{
                        unstash "CHOCOLATEY_PACKAGE"
                        withCredentials([string(credentialsId: "${CHOCO_REPO_KEY}", variable: 'KEY')]) {
                            bat(
                                label: "Deploying to Chocolatey",
                                script: "cd chocolatey_package\\speedwagon && choco push -s %CHOCOLATEY_SERVER% -k %KEY%"

                            )
                        }

                    }
                }
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
                        label "Windows"
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
