#!groovy
// @Library("ds-utils@v0.2.3") // Uses library from https://github.com/UIUCLibrary/Jenkins_utils
import org.ds.*
import static groovy.json.JsonOutput.* // For pretty printing json data


def CONFIGURATIONS = [
    "3.7": [
        test_docker_image: "python:3.7",
        tox_env: "py37",
        dockerfiles:[
            windows: "ci/docker/python/windows/Dockerfile",
            linux: "ci/docker/python/linux/Dockerfile"
        ],
        pkgRegex: [
            wheel: "*.whl",
            sdist: "*.zip"
        ]
    ],
    "3.8": [
        test_docker_image: "python:3.8",
        tox_env: "py38",
        dockerfiles:[
            windows: "ci/docker/python/windows/Dockerfile",
            linux: "ci/docker/python/linux/Dockerfile"
        ],
        pkgRegex: [
            wheel: "*.whl",
            sdist: "*.zip"
        ]
    ]
]


def get_build_args(){
    script{
        def CHOCOLATEY_SOURCE = ""
        try{
            CHOCOLATEY_SOURCE = powershell(script: "(Get-ChildItem Env:Path).value", returnStdout: true).trim()
        } finally {
            return CHOCOLATEY_SOURCE?.trim() ? '--build-arg ' + "CHOCOLATEY_REPO=" + CHOCOLATEY_SOURCE : ''
        }
    }
}
def get_package_version(stashName, metadataFile){
    ws {
        unstash "${stashName}"
        script{
            def props = readProperties interpolate: true, file: "${metadataFile}"
            cleanWs(patterns: [[pattern: "${metadataFile}", type: 'INCLUDE']])
            //deleteDir()
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
def gitAddVersionTag(metadataFile){
    script{
        def props = readProperties( interpolate: true, file: metadataFile)
        def commitTag = input message: 'git commit', parameters: [string(defaultValue: "v${props.Version}", description: 'Version to use a a git tag', name: 'Tag', trim: false)]
        withCredentials([usernamePassword(credentialsId: gitCreds, passwordVariable: 'password', usernameVariable: 'username')]) {
            sh(label: "Tagging ${commitTag}",
               script: """git config --local credential.helper "!f() { echo username=\\$username; echo password=\\$password; }; f"
                          git tag -a ${commitTag} -m 'Tagged by Jenkins'
                          git push origin --tags
                          """
            )
        }
    }
}

def run_tox(){
    sh "mkdir -p logs"
    script{
        withEnv(
            [
                'PIP_INDEX_URL="https://devpi.library.illinois.edu/production/release"',
                'PIP_TRUSTED_HOST="devpi.library.illinois.edu"',
                'TOXENV="py"'
            ]
        ) {
            try{
                // Don't use result-json=${WORKSPACE}\\logs\\tox_report.json because
                // Tox has a bug that fails when trying to write the json report
                // when --parallel is run at the same time
                sh "tox -p=auto -o -vv --workdir .tox -e py"
//                 bat "tox -p=auto -o -vv --workdir ${WORKSPACE}\\.tox"
            } catch (exc) {
                sh "tox -vv --workdir .tox --recreate -e py"
            }
        }
    }
}

def run_pylint(){
    catchError(buildResult: 'SUCCESS', message: 'Pylint found issues', stageResult: 'UNSTABLE') {
        sh(
            script: '''mkdir -p reports
                       pylint speedwagon -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > reports/pylint.txt''',
            label: "Running pylint"
        )
    }
    sh(
        script: 'pylint speedwagon  -r n --msg-template="{path}:{module}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > reports/pylint_issues.txt',
        label: "Running pylint for sonarqube",
        returnStatus: true
    )
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
            cleanWs(patterns: [[pattern: "${metadataFile}", type: 'INCLUDE']])
            return props.Name
        }
    }
}

def build_sphinx_stage(){
    sh "mkdir -p logs"
    sh(label: "Run build_ui",
        script: "python setup.py build_ui"
        )

    sh(
        label: "Building HTML docs on ${env.NODE_NAME}",
        script: "python -m sphinx docs/source build/docs/html -d build/docs/.doctrees --no-color -w logs/build_sphinx.log"
        )
    sh(
        label: "Building LaTex docs on ${env.NODE_NAME}",
        script: "python -m sphinx docs/source build/docs/latex -b latex -d build/docs/.doctrees --no-color -w logs/build_sphinx_latex.log"
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


        //input "Update standalone ${simple_file_names.join(', ')} to '${urlDestination}'? More information: ${currentBuild.absoluteUrl}"

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
        writeFile file: "logs/deployment_request.txt", text: deployment_request
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


def testPythonPackages(pkgRegex, testEnvs){
    script{
        def taskData = []
        node("windows"){
            unstash 'PYTHON_PACKAGES'
            def pythonPkgs = findFiles glob: pkgRegex
            pythonPkgs.each{ fileName ->
                def packageStashName = "${fileName.name}"
                stash includes: "${fileName}", name: "${packageStashName}"
                testEnvs.each{ testEnv->
                    testEnv['images'].each{ dockerImage ->
                        taskData.add(
                            [
                                file: fileName,
                                dockerImage: dockerImage,
                                label: testEnv['label'],
                                stashName: "${packageStashName}"
                            ]
                        )
                    }
                }
            }
        }
        def taskRunners = [:]
        taskData.each{
            taskRunners["Testing ${it['file']} with ${it['dockerImage']}"]={
                node("docker && windows"){
                    def testImage = docker.image(it['dockerImage']).inside("-v pipcache:C:/Users/ContainerAdministrator/AppData/Local/pip/Cache"){
                        try{
                            checkout scm
                            unstash "${it['stashName']}"
                            powershell(
                                label: "Installing Certs required to download python dependencies",
                                script: "certutil -generateSSTFromWU roots.sst ; certutil -addstore -f root roots.sst ; del roots.sst"
                                )
                            bat(
                                label: "Installing Tox",
                                script: """python -m pip install pip --upgrade
                                           pip install tox
                                           """,
                                )
                            withEnv([
                                'PIP_EXTRA_INDEX_URL=https://devpi.library.illinois.edu/production/release',
                                'PIP_TRUSTED_HOST=devpi.library.illinois.edu'
                                ]) {
                                bat(
                                    label:"Running tox tests with ${it['file']}",
                                    script:"tox -c tox.ini --installpkg=${it['file']} -e py -vv"
                                )
                            }
                            archiveArtifacts(artifacts: "dist/*.whl,dist/*.tar.gz,dist/*.zip", fingerprint: true)
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

//
// def test_msi_install(){
//
//     bat "if not exist logs mkdir logs"
//     script{
//
//         def docker_image_name = "test-image:${env.BRANCH_NAME}_${currentBuild.number}"
//         try {
//             def testImage = docker.build(docker_image_name, "-f ./ci/docker/test_installation/Dockerfile .")
//             testImage.inside{
//                 // Copy log files from c:\\logs in the docker container to workspace\\logs
//                 bat "cd ${WORKSPACE}\\logs && copy c:\\logs\\*.log"
//                 bat 'dir "%PROGRAMFILES%\\Speedwagon"'
//             }
//         } finally{
//             bat "docker image rm -f ${docker_image_name}"
//         }
//     }
// }
def build_standalone(){
    stage("Building Standalone"){
        bat "where cmake"
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
                cmakeArgs: """-DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=c:\\wheels
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

def runSonarScanner(propsFile){
    def props = readProperties(interpolate: true, file: propsFile)
    if (env.CHANGE_ID){
        sh(
            label: "Running Sonar Scanner",
            script:"""git fetch --all
                      sonar-scanner -Dsonar.projectVersion=${props.Version} -Dsonar.buildString=\"${env.BUILD_TAG}\" -Dsonar.pullrequest.key=${env.CHANGE_ID} -Dsonar.pullrequest.base=${env.CHANGE_TARGET}
                      """
            )
    } else {
        sh(
            label: "Running Sonar Scanner",
            script: "sonar-scanner -Dsonar.projectVersion=${props.Version} -Dsonar.buildString=\"${env.BUILD_TAG}\" -Dsonar.branch.name=${env.BRANCH_NAME}"
            )
    }
}

def testDevpiPackages(devpiUrl, metadataFile, selector, toxEnv, DEVPI_USR, DEVPI_PSW){
    script{
        def props = readProperties(interpolate: true, file: metadataFile)
        if(isUnix()){
            sh(label: "Running tests on packages stored on DevPi ",
               script: """devpi use ${devpiUrl} --clientdir certs
                           devpi login ${DEVPI_USR} --password ${DEVPI_PSW} --clientdir certs
                           devpi use ${env.BRANCH_NAME}_staging --clientdir certs
                           devpi test --index ${env.BRANCH_NAME}_staging ${props.Name}==${props.Version} -s ${selector} --clientdir certs\\ -e toxEnv -v
                           """
               )

        } else{
            bat(label: "Running tests on packages stored on DevPi ",
                script: """devpi use ${devpiUrl} --clientdir certs\\
                           devpi login ${DEVPI_USR} --password ${DEVPI_PSW} --clientdir certs\\
                           devpi use ${env.BRANCH_NAME}_staging --clientdir certs\\
                           devpi test --index ${env.BRANCH_NAME}_staging ${props.Name}==${props.Version} -s ${selector} --clientdir certs\\ -e ${CONFIGURATIONS[PYTHON_VERSION].tox_env} -v
                           """
                )
        }
    }
}

def testPythonPackagesWithTox(glob){
    script{
        findFiles(glob: glob).each{
            timeout(15){
                if(isUnix()){
                    sh(
                        script: "tox --installpkg=${it.path} -e py --recreate",
                        label: "Testing ${it.name}"
                    )
                } else{
                    bat(
                        script: "tox --installpkg=${it.path} -e py --recreate",
                        label: "Testing ${it.name}"
                    )
                }
            }
        }
    }
}

pipeline {
    agent none
    triggers {
       parameterizedCron '@daily % PACKAGE_WINDOWS_STANDALONE_MSI=true; DEPLOY_DEVPI=true; TEST_RUN_TOX=true'
    }

//     libraries {
//       lib('PythonHelpers')
//     }
    parameters {
        string(name: 'JIRA_ISSUE_VALUE', defaultValue: "PSR-83", description: 'Jira task to generate about updates.')
        booleanParam(name: "TEST_RUN_TOX", defaultValue: false, description: "Run Tox Tests")
        booleanParam(name: "USE_SONARQUBE", defaultValue: true, description: "Send data test data to SonarQube")

        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_MSI", defaultValue: false, description: "Create a standalone wix based .msi installer")

        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_NSIS", defaultValue: false, description: "Create a standalone NULLSOFT NSIS based .exe installer")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_ZIP", defaultValue: false, description: "Create a standalone portable package")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE_CHOLOCATEY", defaultValue: false, description: "Create package for the Chocolatey package manager")

        booleanParam(name: "DEPLOY_DEVPI", defaultValue: false, description: "Deploy to DevPi on https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: "DEPLOY_DEVPI_PRODUCTION", defaultValue: false, description: "Deploy to https://devpi.library.illinois.edu/production/release")
        booleanParam(name: "DEPLOY_ADD_TAG", defaultValue: false, description: "Tag commit to current version")
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
                                    filename 'ci/docker/python/linux/Dockerfile'
                                    label 'linux && docker'
                                    additionalBuildArgs '--build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
                                 }
                            }
                            steps{
                                sh "python setup.py dist_info"
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
                            filename 'ci/docker/python/linux/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs '--build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
                          }
                    }
                    steps {
                        sh '''mkdir -p logs
                              python setup.py build -b build
                              '''
                    }
                    post{
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
                stage("Build Sphinx Documentation"){
                    agent {
                        dockerfile {
                            filename 'ci/docker/makepdf/lite/Dockerfile'
                            label 'linux && docker'
                        }
                    }
                    steps {
                        sh(
                            label: "Building HTML docs on ${env.NODE_NAME}",
                            script: '''mkdir -p logs
                                       python setup.py build_ui
                                       python -m sphinx docs/source build/docs/html -d build/docs/.doctrees --no-color -w logs/build_sphinx.log
                                       '''
                            )
                            sh(label: "Building PDF docs on ${env.NODE_NAME}",
                               script: '''python -m sphinx docs/source build/docs/latex -b latex -d build/docs/.doctrees --no-color -w logs/build_sphinx_latex.log
                                          make -C build/docs/latex
                                          mkdir -p dist/docs
                                          mv build/docs/latex/*.pdf dist/docs/
                                          '''
                            )
                    }
                    post{
                        always{
                            recordIssues(tools: [sphinxBuild(pattern: 'logs/build_sphinx.log')])
                            stash includes: "dist/docs/*.pdf", name: 'SPEEDWAGON_DOC_PDF'
                        }
                        success{
                            unstash "DIST-INFO"
                            script{
                                def props = readProperties interpolate: true, file: 'speedwagon.dist-info/METADATA'
                                def DOC_ZIP_FILENAME = "${props.Name}-${props.Version}.doc.zip"
                                zip archive: true, dir: "build/docs/html", glob: '', zipFile: "dist/${DOC_ZIP_FILENAME}"
                                stash includes: "dist/${DOC_ZIP_FILENAME},build/docs/html/**", name: 'DOCS_ARCHIVE'
                            }
                            archiveArtifacts artifacts: 'dist/docs/*.pdf'
                        }
                        cleanup{
                            cleanWs(
                                notFailBuild: true,
                                deleteDirs: true,
                                patterns: [
                                    [pattern: "dist/", type: 'INCLUDE'],
                                    [pattern: 'build/', type: 'INCLUDE'],
                                    [pattern: "speedwagon.dist-info/", type: 'INCLUDE'],
                                ]
                            )
                        }
                    }
                }
            }
        }
        stage("Test") {
            agent {
                dockerfile {
                    filename 'ci/docker/python/linux/Dockerfile'
                    label 'linux && docker'
                    additionalBuildArgs '--build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
                  }
            }
            stages{
                stage("Run Tests"){
                    parallel {
                        stage("Run Behave BDD Tests") {
                            steps {
                                catchError(buildResult: "UNSTABLE", message: 'Did not pass all Behave BDD tests', stageResult: "UNSTABLE") {
                                    sh(
                                        script: """mkdir -p reports
                                                   coverage run --parallel-mode --source=speedwagon -m behave --junit --junit-directory reports/tests/behave"""
                                        )
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
                                catchError(buildResult: "UNSTABLE", message: 'Did not pass all pytest tests', stageResult: "UNSTABLE") {
                                    sh(
                                        script: '''mkdir -p logs
                                                   coverage run --parallel-mode --source=speedwagon -m pytest --junitxml=./reports/tests/pytest/pytest-junit.xml
                                                   '''
                                    )
                                }
                            }
                            post {
                                always {
                                    junit "reports/tests/pytest/pytest-junit.xml"
                                    stash includes: "reports/tests/pytest/*.xml", name: "PYTEST_UNIT_TEST_RESULTS"
                                }
                            }
                        }
                        stage("Run Doctest Tests"){
                            steps {
                                sh(
                                    label: "Running Doctest Tests",
                                    script: '''python setup.py build build_ui
                                               sphinx-build -b doctest docs/source build/docs -d build/docs/doctrees --no-color -w logs/doctest.txt
                                               '''
                                    )
                            }
                            post{
                                always {
                                    recordIssues(tools: [sphinxBuild(id: 'doctest', pattern: 'logs/doctest.txt')])
                                }
                            }
                        }
                        stage("Run MyPy Static Analysis") {
                            steps{
                                catchError(buildResult: "SUCCESS", message: 'MyPy found issues', stageResult: "UNSTABLE") {
                                    sh(label: 'Running MyPy',
                                        script: '''mkdir -p logs
                                                   mypy -p speedwagon --html-report reports/mypy/html | tee logs/mypy.log
                                                   '''
                                    )
                                }
                            }
                            post {
                                always {
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
                              PIP_TRUSTED_HOST = "devpi.library.illinois.edu"

                            }
                            steps {
                                sh "tox -e py -vv -i https://devpi.library.illinois.edu/production/release"
                            }
                            post{
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
                                    recordIssues(tools: [pyLint(pattern: 'reports/pylint.txt')])
                                }
                            }
                        }
                        stage("Run Flake8 Static Analysis") {
                            steps{
                                catchError(buildResult: "SUCCESS", message: 'Flake8 found issues', stageResult: "UNSTABLE") {
                                    sh script: '''mkdir -p logs
                                                  flake8 speedwagon --tee --output-file=logs/flake8.log
                                                  '''
                                }
                            }
                            post {
                                always {
                                      stash includes: 'logs/flake8.log', name: "FLAKE8_REPORT"
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
                            sh "coverage combine && coverage xml -o reports/coverage.xml && coverage html -d reports/coverage"
                            stash includes: "reports/coverage.xml", name: "COVERAGE_REPORT_DATA"
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
                            [pattern: 'logs/*', type: 'INCLUDE'],
                            [pattern: 'reports/coverage.xml', type: 'INCLUDE'],
                            [pattern: 'reports/coverage', type: 'INCLUDE'],
                            [pattern: '.coverage', type: 'INCLUDE']
                        ])
                }
            }
        }
        stage("Run Sonarqube Analysis"){
            agent {
              dockerfile {
                filename 'ci/docker/sonarcloud/Dockerfile'
                label 'linux && docker'
              }
            }
            options{
                lock("speedwagon-sonarscanner")
            }
            when{
                equals expected: true, actual: params.USE_SONARQUBE
                beforeAgent true
            }
            steps{
                checkout scm
                unstash "COVERAGE_REPORT_DATA"
                unstash "PYTEST_UNIT_TEST_RESULTS"
                unstash "PYLINT_REPORT"
                unstash "FLAKE8_REPORT"
                script{
                    withSonarQubeEnv(installationName:"sonarcloud", credentialsId: 'sonarcloud-speedwagon') {
                        unstash "DIST-INFO"
                        runSonarScanner("speedwagon.dist-info/METADATA")
                    }
                    def sonarqube_result = waitForQualityGate(abortPipeline: false)
                    if (sonarqube_result.status != 'OK') {
                        unstable "SonarQube quality gate: ${sonarqube_result.status}"
                    }
                    def outstandingIssues = get_sonarqube_unresolved_issues(".scannerwork/report-task.txt")
                    writeJSON file: 'reports/sonar-report.json', json: outstandingIssues
                }
            }
            post {
                always{
                    archiveArtifacts(
                        allowEmptyArchive: true,
                        artifacts: ".scannerwork/report-task.txt"
                    )
                    stash includes: "reports/sonar-report.json", name: 'SONAR_REPORT'
                    archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/sonar-report.json'
                    recordIssues(tools: [sonarQube(pattern: 'reports/sonar-report.json')])
                }
            }
        }
        stage("Packaging sdist and wheel"){
            agent {
                dockerfile {
                    filename 'ci/docker/python/linux/Dockerfile'
                    label 'linux && docker'
                    additionalBuildArgs '--build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
                  }
            }
            steps{
                timeout(5){
                    unstash "PYTHON_BUILD_FILES"
                    sh script: 'python setup.py build -b build sdist -d dist --format zip bdist_wheel -d dist'
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
        stage('Testing all Package') {
            matrix{
                agent {
                    dockerfile {
                        filename "ci/docker/python/${PLATFORM}/Dockerfile"
                        label "${PLATFORM} && docker"
                        additionalBuildArgs "--build-arg PYTHON_VERSION=${PYTHON_VERSION}"
                    }
                }
                axes{
                    axis {
                        name "PYTHON_VERSION"
                        values(
                            "3.7",
                            "3.8"
                        )
                    }
                    axis {
                        name "PLATFORM"
                        values(
                            'linux',
                            'windows'
                        )
                    }
                }
                stages{
                    stage("Testing sdist Package"){
                        steps{
                            unstash "PYTHON_PACKAGES"
                            testPythonPackagesWithTox("dist/${CONFIGURATIONS[PYTHON_VERSION].pkgRegex['sdist']}")
                        }
                    }
                    stage("Testing bdist_wheel Package"){
                        steps{
                            unstash "PYTHON_PACKAGES"
                            testPythonPackagesWithTox("dist/${CONFIGURATIONS[PYTHON_VERSION].pkgRegex['wheel']}")
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
                build_number = get_build_number()
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
                            additionalBuildArgs "${get_build_args()}"
                          }
                    }
                    steps {
                        build_standalone()
                    }
                    post {
                        success{
                            archiveArtifacts artifacts: "dist/*.msi,dist/*.exe,dist/*.zip", fingerprint: true
                        }
                        failure {
                            archiveArtifacts allowEmptyArchive: true, artifacts: "dist/**/wix.log,dist/**/*.wxs"
                        }
                        always{
                            stash includes: "dist/*.msi,dist/*.exe,dist/*.zip", name: "STANDALONE_INSTALLERS"
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
                        skipDefaultCheckout(true)
                    }
                    steps{
                        timeout(15){
                            unstash 'STANDALONE_INSTALLERS'
                            script{
                                def msi_file = findFiles(glob: "dist/*.msi")[0].path
                                powershell "New-Item -ItemType Directory -Force -Path logs; Write-Host \"Installing ${msi_file}\"; msiexec /i ${msi_file} /qn /norestart /L*v! logs\\msiexec.log"
                            }
                        }
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
                    when{
                        anyOf{
                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_CHOLOCATEY
                            equals expected: true, actual: params.DEPLOY_CHOLOCATEY
                        }
                        beforeAgent true
                    }
                    steps{
                        unstash 'STANDALONE_INSTALLERS'
                        timeout(15){
                            script{
                                make_chocolatey_distribution(
                                    findFiles(glob: "dist/*.msi")[0],
                                    get_package_version("DIST-INFO", "speedwagon.dist-info/METADATA"),
                                    "chocolatey_package"
                                    )
                            }
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
        stage("Deploy to Devpi"){
            when {
                allOf{
                    equals expected: true, actual: params.DEPLOY_DEVPI
                    anyOf {
                        equals expected: "master", actual: env.BRANCH_NAME
                        equals expected: "dev", actual: env.BRANCH_NAME
                    }
                }
                beforeAgent true
                beforeOptions true
            }
            agent none
            environment{
                DEVPI = credentials("DS_devpi")
            }
            options{
                lock("speedwagon-devpi")
            }
            stages{
                stage("Deploy to Devpi Staging") {
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/Dockerfile'
                            label 'linux&&docker'
                            additionalBuildArgs '--build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
                          }
                    }
                    steps {
                        unstash 'DOCS_ARCHIVE'
                        unstash 'PYTHON_PACKAGES'
                        sh(
                            label: "Connecting to DevPi Server",
                            script: """devpi use https://devpi.library.illinois.edu --clientdir ./devpi
                                       devpi login $DEVPI_USR --password $DEVPI_PSW --clientdir ./devpi
                                       devpi use /${env.DEVPI_USR}/${env.BRANCH_NAME}_staging --clientdir ./devpi
                                       devpi upload --from-dir dist --clientdir ./devpi
                                       """
                        )
                    }
                }
                stage("Test DevPi packages") {
                    matrix {
                        axes {
                            axis {
                                name 'PLATFORM'
                                values(
                                    'windows',
                                    "linux"
                                    )
                            }
                            axis {
                                name 'PYTHON_VERSION'
                                values '3.7', "3.8"
                            }
                        }
                        agent {
                          dockerfile {
                            additionalBuildArgs "--build-arg PYTHON_DOCKER_IMAGE_BASE=${CONFIGURATIONS[PYTHON_VERSION].test_docker_image}"
                            filename "ci/docker/python/${PLATFORM}/Dockerfile"
                            label "${PLATFORM} && docker"
                          }
                        }
                        stages{
                            stage("Testing DevPi Package"){
                                steps{
                                    timeout(10){
                                        unstash "DIST-INFO"
                                        testDevpiPackages("https://devpi.library.illinois.edu", "speedwagon.dist-info/METADATA", "zip", CONFIGURATIONS[PYTHON_VERSION].tox_env,  env.DEVPI_USR, env.DEVPI_PSW)
                                    }
                                }
                            }
                            stage("Testing DevPi Package wheel"){
                                steps{
                                    timeout(10){
                                        unstash "DIST-INFO"
                                        testDevpiPackages("https://devpi.library.illinois.edu", "speedwagon.dist-info/METADATA", "whl", CONFIGURATIONS[PYTHON_VERSION].tox_env, env.DEVPI_USR, env.DEVPI_PSW)
                                    }
                                }
                            }

                        }
                    }
                }
                stage("Deploy to DevPi Production") {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION
                            branch "master"
                        }
                        beforeAgent true
                        beforeInput true
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs '--build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
                          }
                    }
                    input {
                        message 'Release to DevPi Production?'
                    }
                    steps {
                        unstash "DIST-INFO"
                        script{
                            def props = readProperties interpolate: true, file: "speedwagon.dist-info/METADATA"
                            sh(label: "Pushing to production index",
                               script: """devpi use https://devpi.library.illinois.edu --clientdir ./devpi
                                          devpi login $DEVPI_USR --password $DEVPI_PSW --clientdir ./devpi
                                          devpi push --index DS_Jenkins/${env.BRANCH_NAME}_staging ${props.Name}==${props.Version} production/release --clientdir ./devpi
                                       """
                            )
                        }
                    }
                }
            }
            post{
                success{
                    node('linux && docker') {
                       script{
                            docker.build("speedwagon:devpi.${env.BUILD_ID}",'-f ./ci/docker/python/linux/Dockerfile --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .').inside{
                                unstash "DIST-INFO"
                                def props = readProperties interpolate: true, file: 'speedwagon.dist-info/METADATA'
                                sh(label: "Connecting to DevPi Server",
                                   script: """devpi use https://devpi.library.illinois.edu --clientdir ./devpi
                                              devpi login $DEVPI_USR --password $DEVPI_PSW --clientdir ./devpi
                                              devpi use /DS_Jenkins/${env.BRANCH_NAME}_staging --clientdir ./devpi
                                              devpi push ${props.Name}==${props.Version} DS_Jenkins/${env.BRANCH_NAME} --clientdir ./devpi
                                              """
                                )
                            }
                       }
                    }
                }
                cleanup{
                    node('linux && docker') {
                       script{
                            docker.build("speedwagon:devpi.${env.BUILD_ID}",'-f ./ci/docker/python/linux/Dockerfile --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .').inside{
                                unstash "DIST-INFO"
                                def props = readProperties interpolate: true, file: 'speedwagon.dist-info/METADATA'
                                sh(
                                    label: "Connecting to DevPi Server",
                                    script: """devpi use https://devpi.library.illinois.edu --clientdir ./devpi
                                               devpi login $DEVPI_USR --password $DEVPI_PSW --clientdir ./devpi
                                               devpi use /DS_Jenkins/${env.BRANCH_NAME}_staging --clientdir ./devpi
                                               devpi remove -y ${props.Name}==${props.Version} --clientdir ./devpi
                                               """
                                )
                            }
                       }
                    }
                }
            }
        }
        stage("Deploy"){
            parallel {
                stage("Tagging git Commit"){
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs '--build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)'
                        }
                    }
                    when{
                        allOf{
                            equals expected: true, actual: params.DEPLOY_ADD_TAG
                        }
                        beforeAgent true
                        beforeInput true
                    }
                    options{
                        timeout(time: 1, unit: 'DAYS')
                        retry(3)
                    }
                    input {
                          message 'Add a version tag to git commit?'
                          parameters {
                                credentials credentialType: 'com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl', defaultValue: 'github.com', description: '', name: 'gitCreds', required: true
                          }
                    }
                    steps{
                        unstash "DIST-INFO"
                        gitAddVersionTag("speedwagon.dist-info/METADATA")

                    }
                    post{
                        cleanup{
                            deleteDir()
                        }
                    }
                }
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
                        beforeAgent true
                        beforeInput true
                    }
                    agent any
                    input {
                        message 'Update project documentation?'
                    }
                    steps{
                        unstash "SPEEDWAGON_DOC_HTML"
                        dir("build/docs/html/"){
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
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: 'build/', type: 'INCLUDE']
                                ]
                            )
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
                        beforeAgent true
                        beforeInput true

                    }
                    input {
                        message 'Update standalone to Hathi Beta'
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
