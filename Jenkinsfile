#!groovy
import static groovy.json.JsonOutput.* // For pretty printing json data

SUPPORTED_MAC_VERSIONS = ['3.8', '3.9', '3.10']
SUPPORTED_LINUX_VERSIONS = ['3.7', '3.8', '3.9', '3.10']
SUPPORTED_WINDOWS_VERSIONS = ['3.7', '3.8', '3.9', '3.10']
DOCKER_PLATFORM_BUILD_ARGS = [
    linux: '',
    windows: '--build-arg CHOCOLATEY_SOURCE'
]

PYPI_SERVERS = [
    'https://jenkins.library.illinois.edu/nexus/repository/uiuc_prescon_python_public/',
    'https://jenkins.library.illinois.edu/nexus/repository/uiuc_prescon_python_testing/'
    ]

NEXUS_SERVERS = [
    'https://jenkins.library.illinois.edu/nexus/repository/prescon-dist/',
    'https://jenkins.library.illinois.edu/nexus/repository/prescon-beta/'
    ]

def getDevPiStagingIndex(){

    if (env.TAG_NAME?.trim()){
        return 'tag_staging'
    } else{
        return "${env.BRANCH_NAME}_staging"
    }
}

DEVPI_CONFIG = [
    index: getDevPiStagingIndex(),
    server: 'https://devpi.library.illinois.edu',
    credentialsId: 'DS_devpi',
]


def run_pylint(){
    withEnv(['PYLINTHOME=.']) {
        sh 'pylint --version'
        catchError(buildResult: 'SUCCESS', message: 'Pylint found issues', stageResult: 'UNSTABLE') {
            tee('reports/pylint_issues.txt'){
                sh(
                    label: 'Running pylint',
                    script: 'pylint speedwagon -r n --msg-template="{path}:{module}:{line}: [{msg_id}({symbol}), {obj}] {msg}"',
                )
            }
        }
        tee('reports/pylint.txt'){
            sh(
                label: 'Running pylint for sonarqube',
                script: 'pylint speedwagon -d duplicate-code --output-format=parseable',
                returnStatus: true
            )
        }
    }
}


def get_build_number(){
    script{
        try{
            def versionPrefix = ''

            if(currentBuild.getBuildCauses()[0].shortDescription == 'Started by timer'){
                versionPrefix = 'Nightly'
            }
            return VersionNumber(projectStartDate: '2017-11-08', versionNumberString: '${BUILD_DATE_FORMATTED, "yy"}${BUILD_MONTH, XX}${BUILDS_THIS_MONTH, XXX}', versionPrefix: '', worstResultForIncrement: 'SUCCESS')
        } catch(e){
            return ""
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
            jiraComment body: jira_message, issueKey: jiraIssueKey
        }
    }
}
def runTox(){
    script{
        def tox
        node(){
            checkout scm
            tox = load('ci/jenkins/scripts/tox.groovy')
        }
        def windowsJobs = [:]
        def linuxJobs = [:]
        stage("Scanning Tox Environments"){
            parallel(
                'Linux':{
                    linuxJobs = tox.getToxTestsParallel(
                            envNamePrefix: 'Tox Linux',
                            label: 'linux && docker',
                            dockerfile: 'ci/docker/python/linux/tox/Dockerfile',
                            dockerArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                        )
                },
                'Windows':{
                    windowsJobs = tox.getToxTestsParallel(
                            envNamePrefix: 'Tox Windows',
                            label: 'windows && docker',
                            dockerfile: 'ci/docker/python/windows/tox/Dockerfile',
                            dockerArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE'
                     )
                },
                failFast: true
            )
        }
        parallel(windowsJobs + linuxJobs)
    }
}

def createNewChocolateyPackage(args=[:]){

    def chocoPackageName = args.name
    def packageSummery = args.summary
    def sanitizedPackageVersion
    def packageMaintainer = args.maintainer
    def applicationWheel = args.files.applicationWheel
    def dependenciesDir = args.files.dependenciesDir
    def docsDir = args.files.docsDir

    echo 'Creating new Chocolatey package'

    node(){
        checkout scm
        sanitizedPackageVersion = load('ci/jenkins/scripts/chocolatey.groovy').sanitize_chocolatey_version(args.version)
    }
    bat(
        label: 'Creating new Chocolatey package workspace',
        script: """
                choco new ${chocoPackageName} packageversion=${sanitizedPackageVersion} PythonSummary="${packageSummery}" InstallerFile=${applicationWheel} MaintainerName="${packageMaintainer}" -t pythonscript --outputdirectory packages
               """
        )


    powershell(
        label: 'Adding data to Chocolatey package workspace',
        script: """\$ErrorActionPreference = 'Stop'; # stop on all errors
               New-Item -ItemType File -Path ".\\packages\\${chocoPackageName}\\${applicationWheel}" -Force | Out-Null
               Move-Item -Path "${applicationWheel}"  -Destination "./packages/${chocoPackageName}/${applicationWheel}"  -Force | Out-Null
               Copy-Item -Path "${dependenciesDir}"  -Destination ".\\packages\\${chocoPackageName}\\deps\\" -Force -Recurse
               Copy-Item -Path "${docsDir}"  -Destination ".\\packages\\${chocoPackageName}\\docs\\" -Force -Recurse
               """
        )
    findFiles(glob: 'packages/**/*.nuspec').each{
        def nuspec = readFile(file: it.path)
        echo "nuspec = ${nuspec}"
    }

    bat(
        label: 'Packaging Chocolatey package',
        script: "choco pack .\\packages\\speedwagon\\speedwagon.nuspec --outputdirectory .\\packages"
    )

    bat(
        label: 'Checking chocolatey package metadata',
        script: 'choco info --pre -s .\\packages\\ speedwagon'
    )
}

def deploy_sscm(file_glob, pkgVersion, jiraIssueKey){
    script{
        def msi_files = findFiles glob: file_glob
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

        jiraComment body: "Version ${pkgVersion} sent to staging for user testing.", issueKey: jiraIssueKey
        input('Deploy to production?')
        writeFile file: 'logs/deployment_request.txt', text: deployment_request
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
def testSpeedwagonChocolateyPkg(version){
    echo 'Testing Chocolatey package'
    script{
        def chocolatey = load('ci/jenkins/scripts/chocolatey.groovy')
        chocolatey.install_chocolatey_package(
            name: 'speedwagon',
            version: chocolatey.sanitize_chocolatey_version(version),
            source: './packages/;CHOCOLATEY_SOURCE;chocolatey'
        )
    }
    powershell(
            label: "Checking for Start Menu shortcut",
            script: 'Get-ChildItem "$Env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs" -Recurse -Include *.lnk'
        )
    bat 'speedwagon --help'
}


def startup(){

    parallel(
    [
        failFast: true,
        'Loading Reference Build Information': {
            node(){
                checkout scm
                discoverGitReferenceBuild(latestBuildIfNotFound: true)
            }
        },
        'Getting Distribution Info': {
            node('linux && docker') {
                timeout(2){
                    ws{
                        checkout scm
                        try{
                            docker.image('python').inside {
                                withEnv(['PIP_NO_CACHE_DIR=off']) {
                                    sh(
                                       label: 'Running setup.py with dist_info',
                                       script: 'python setup.py dist_info'
                                    )
                                }
                                stash includes: '*.dist-info/**', name: 'DIST-INFO'
                                archiveArtifacts artifacts: '*.dist-info/**'
                            }
                        } finally{
                            deleteDir()
                        }
                    }
                }
            }
        }
    ]
    )

}


def create_wheels(){
    def wheelCreatorTasks = [:]
    ['3.7', '3.8', '3.9', '3.10'].each{ pythonVersion ->
        wheelCreatorTasks["Packaging wheels for ${pythonVersion}"] = {
            node('windows && docker') {
                ws{
                    checkout scm
                    try{
                        docker.build("speedwagon:wheelbuilder","-f ci/docker/python/windows/tox/Dockerfile --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE .").inside{
                            bat(label: "Getting dependencies to vendor", script:"py -${pythonVersion} -m pip wheel -r requirements-vendor.txt --no-deps -w .\\deps\\ -i https://devpi.library.illinois.edu/production/release")
                            stash includes: "deps/*.whl", name: "PYTHON_DEPS_${pythonVersion}"
                        }
                    } finally{
                        cleanWs(
                            deleteDirs: true,
                            patterns: [
                                [pattern: 'deps/', type: 'INCLUDE']
                                ]
                        )
                    }
                }
            }
        }
    }
    parallel(wheelCreatorTasks)
}

def testPythonPackages(){
    script{
        def packages
        node(){
            checkout scm
            packages = load 'ci/jenkins/scripts/packaging.groovy'
        }
        def windowsTests = [:]
        SUPPORTED_WINDOWS_VERSIONS.each{ pythonVersion ->
            windowsTests["Windows - Python ${pythonVersion}: sdist"] = {
                packages.testPkg(
                    agent: [
                        dockerfile: [
                            label: 'windows && docker',
                            filename: 'ci/docker/python/windows/tox/Dockerfile',
                            additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE'
                        ]
                    ],
                    glob: 'dist/*.tar.gz,dist/*.zip',
                    stash: 'PYTHON_PACKAGES',
                    pythonVersion: pythonVersion,
                    retry: 3,
                )
            }
            windowsTests["Windows - Python ${pythonVersion}: wheel"] = {
                packages.testPkg(
                    agent: [
                        dockerfile: [
                            label: 'windows && docker',
                            filename: 'ci/docker/python/windows/tox/Dockerfile',
                            additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE'
                        ]
                    ],
                    glob: 'dist/*.whl',
                    stash: 'PYTHON_PACKAGES',
                    pythonVersion: pythonVersion,
                    retry: 3,
                )
            }
        }
        def linuxTests = [:]
        SUPPORTED_LINUX_VERSIONS.each{ pythonVersion ->
            linuxTests["Linux - Python ${pythonVersion}: sdist"] = {
                packages.testPkg(
                    agent: [
                        dockerfile: [
                            label: 'linux && docker',
                            filename: 'ci/docker/python/linux/tox/Dockerfile',
                            additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                        ]
                    ],
                    glob: 'dist/*.tar.gz',
                    stash: 'PYTHON_PACKAGES',
                    pythonVersion: pythonVersion,
                    retry: 3,
                )
            }
            linuxTests["Linux - Python ${pythonVersion}: wheel"] = {
                packages.testPkg(
                    agent: [
                        dockerfile: [
                            label: 'linux && docker',
                            filename: 'ci/docker/python/linux/tox/Dockerfile',
                            additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                        ]
                    ],
                    glob: 'dist/*.whl',
                    stash: 'PYTHON_PACKAGES',
                    pythonVersion: pythonVersion,
                    retry: 3,
                )
            }
        }
        def tests = linuxTests + windowsTests
        def macTests = [:]

        SUPPORTED_MAC_VERSIONS.each{ pythonVersion ->
            macTests["Mac - Python ${pythonVersion}: sdist"] = {
                withEnv(['QT_QPA_PLATFORM=offscreen']) {
                    packages.testPkg(
                        agent: [
                            label: "mac && python${pythonVersion}",
                        ],
                        glob: 'dist/*.tar.gz,dist/*.zip',
                        stash: 'PYTHON_PACKAGES',
                        pythonVersion: pythonVersion,
                        toxExec: 'venv/bin/tox',
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                            sh(
                                label:'Install Tox',
                                script: '''python3 -m venv venv
                                           venv/bin/pip install pip --upgrade
                                           venv/bin/pip install tox
                                           '''
                            )
                        },
                        testTeardown: {
                            sh 'rm -r venv/'
                        },
                        retry: 3,
                    )
                }
            }
            macTests["Mac - Python ${pythonVersion}: wheel"] = {
                withEnv(['QT_QPA_PLATFORM=offscreen']) {
                    packages.testPkg(
                        agent: [
                            label: "mac && python${pythonVersion}",
                        ],
                        glob: 'dist/*.whl',
                        stash: 'PYTHON_PACKAGES',
                        pythonVersion: pythonVersion,
                        toxExec: 'venv/bin/tox',
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                            sh(
                                label:'Install Tox',
                                script: '''python3 -m venv venv
                                           venv/bin/pip install pip --upgrade
                                           venv/bin/pip install tox
                                           '''
                            )
                        },
                        testTeardown: {
                            sh 'rm -r venv/'
                        },
                        retry: 3,

                    )
                }
            }
        }
        if(params.TEST_PACKAGES_ON_MAC == true){
            tests = tests + macTests
        }
        parallel(tests)
    }
}

def buildSphinx(){
    withEnv(['QT_QPA_PLATFORM=offscreen']) {
        def sphinx  = load('ci/jenkins/scripts/sphinx.groovy')
        sh(script: '''mkdir -p logs
                      '''
          )

        sphinx.buildSphinxDocumentation(
            sourceDir: 'docs/source',
            outputDir: 'build/docs/html',
            doctreeDir: 'build/docs/.doctrees',
            builder: 'html',
            writeWarningsToFile: 'logs/build_sphinx_html.log'
            )
        sphinx.buildSphinxDocumentation(
            sourceDir: 'docs/source',
            outputDir: 'build/docs/latex',
            doctreeDir: 'build/docs/.doctrees',
            builder: 'latex'
            )

        sh(label: 'Building PDF docs',
           script: '''make -C build/docs/latex
                      mkdir -p dist/docs
                      mv build/docs/latex/*.pdf dist/docs/
                      '''
        )
    }
}

startup()
def get_props(){
    stage('Reading Package Metadata'){
        node(){
            unstash 'DIST-INFO'
            return readProperties(interpolate: true, file: 'speedwagon.dist-info/METADATA')
        }
    }
}
props = get_props()
pipeline {
    agent none
    parameters {
        string(name: 'JIRA_ISSUE_VALUE', defaultValue: 'PSR-83', description: 'Jira task to generate about updates.')
        booleanParam(name: 'USE_SONARQUBE', defaultValue: true, description: 'Send data test data to SonarQube')
        booleanParam(name: 'RUN_CHECKS', defaultValue: true, description: 'Run checks on code')
        booleanParam(name: 'TEST_RUN_TOX', defaultValue: false, description: 'Run Tox Tests')
        booleanParam(name: 'BUILD_PACKAGES', defaultValue: false, description: 'Build Packages')
        booleanParam(name: 'BUILD_CHOCOLATEY_PACKAGE', defaultValue: false, description: 'Build package for chocolatey package manager')
        booleanParam(name: "TEST_PACKAGES_ON_MAC", defaultValue: false, description: "Test Python packages on Mac")
        booleanParam(name: 'TEST_PACKAGES', defaultValue: true, description: 'Test Python packages by installing them and running tests on the installed package')
        booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG', defaultValue: false, description: 'Create a Apple Application Bundle DMG')
        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_MSI', defaultValue: false, description: 'Create a standalone wix based .msi installer')
        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_NSIS', defaultValue: false, description: 'Create a standalone NULLSOFT NSIS based .exe installer')
        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_ZIP', defaultValue: false, description: 'Create a standalone portable package')
        booleanParam(name: 'DEPLOY_DEVPI', defaultValue: false, description: "Deploy to DevPi on https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: 'DEPLOY_DEVPI_PRODUCTION', defaultValue: false, description: 'Deploy to https://devpi.library.illinois.edu/production/release')
        booleanParam(name: 'DEPLOY_PYPI', defaultValue: false, description: 'Deploy to pypi')
        booleanParam(name: 'DEPLOY_CHOCOLATEY', defaultValue: false, description: 'Deploy to Chocolatey repository')
        booleanParam(name: 'DEPLOY_DMG', defaultValue: false, description: 'Deploy MacOS standalone')
        booleanParam(name: 'DEPLOY_HATHI_TOOL_BETA', defaultValue: false, description: 'Deploy standalone to https://jenkins.library.illinois.edu/nexus/service/rest/repository/browse/prescon-beta/')
        booleanParam(name: 'DEPLOY_SCCM', defaultValue: false, description: 'Request deployment of MSI installer to SCCM')
        booleanParam(name: 'DEPLOY_DOCS', defaultValue: false, description: 'Update online documentation')
//         string(name: 'DEPLOY_DOCS_URL_SUBFOLDER', defaultValue: "speedwagon", description: 'The directory that the docs should be saved under')
    }
    stages {

//         stage("Testing Jira epic"){
//             agent any
//             options {
//                 skipDefaultCheckout(true)
//
//             }
//             steps {
//                 check_jira_project('PSR',, 'logs/jira_project_data.json')
//                 check_jira_issue("${params.JIRA_ISSUE_VALUE}", "logs/jira_issue_data.json")
//             }
//             post{
//                 cleanup{
//                     cleanWs(patterns: [[pattern: "logs/*.json", type: 'INCLUDE']])
//                 }
//             }
//         }
        stage('Build Sphinx Documentation'){
            agent {
                dockerfile {
                    filename 'ci/docker/python/linux/jenkins/Dockerfile'
                    label 'linux && docker'
                    additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                  }
            }
            steps {
                buildSphinx()
            }
            post{
                always{
                    recordIssues(tools: [sphinxBuild(pattern: 'logs/build_sphinx_html.log')])
                    stash includes: 'dist/docs/*.pdf', name: 'SPEEDWAGON_DOC_PDF'
                }
                success{
                    zip archive: true, dir: 'build/docs/html', glob: '', zipFile: "dist/${props.Name}-${props.Version}.doc.zip"
                    stash includes: 'dist/*.doc.zip,build/docs/html/**', name: 'DOCS_ARCHIVE'
                    archiveArtifacts artifacts: 'dist/docs/*.pdf'
                }
                cleanup{
                    cleanWs(
                        notFailBuild: true,
                        deleteDirs: true,
                        patterns: [
                            [pattern: 'dist/', type: 'INCLUDE'],
                            [pattern: 'build/', type: 'INCLUDE'],
                            [pattern: 'speedwagon.dist-info/', type: 'INCLUDE'],
                        ]
                    )
                }
            }
        }
        stage('Checks'){
            when{
                equals expected: true, actual: params.RUN_CHECKS
            }
            stages{
                stage('Code Quality'){
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/jenkins/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                            args '--mount source=sonar-cache-speedwagon,target=/opt/sonar/.sonar/cache'
                          }
                    }
                    stages{
                        stage('Test') {
                            stages{
                                stage('Run Tests'){
                                    parallel {
                                        stage('Run Behave BDD Tests') {
                                            steps {
                                                catchError(buildResult: 'UNSTABLE', message: 'Did not pass all Behave BDD tests', stageResult: "UNSTABLE") {
                                                    sh(
                                                        script: '''mkdir -p reports
                                                                   coverage run --parallel-mode --source=speedwagon -m behave --junit --junit-directory reports/tests/behave'''
                                                    )
                                                }
                                            }
                                            post {
                                                always {
                                                    junit 'reports/tests/behave/*.xml'
                                                }
                                            }
                                        }
                                        stage('Run PyTest Unit Tests'){
                                            steps{
                                                catchError(buildResult: 'UNSTABLE', message: 'Did not pass all pytest tests', stageResult: "UNSTABLE") {
                                                    sh(
                                                        script: 'coverage run --parallel-mode --source=speedwagon -m pytest --junitxml=./reports/tests/pytest/pytest-junit.xml'
                                                    )
                                                }
                                            }
                                            post {
                                                always {
                                                    junit 'reports/tests/pytest/pytest-junit.xml'
                                                    stash includes: 'reports/tests/pytest/*.xml', name: 'PYTEST_UNIT_TEST_RESULTS'
                                                }
                                            }
                                        }
                                        stage('Task Scanner'){
                                            steps{
                                                recordIssues(tools: [taskScanner(highTags: 'FIXME', includePattern: 'speedwagon/**/*.py', normalTags: 'TODO')])
                                            }
                                        }
                                        stage('Run Doctest Tests'){
                                            steps {
                                                sh(
                                                    label: 'Running Doctest Tests',
                                                    script: '''mkdir -p logs
                                                               coverage run --parallel-mode --source=speedwagon -m sphinx -b doctest docs/source build/docs -d build/docs/doctrees --no-color -w logs/doctest.txt
                                                               '''
                                                    )
                                            }
                                            post{
                                                always {
                                                    recordIssues(tools: [sphinxBuild(id: 'doctest', name: 'Doctest', pattern: 'logs/doctest.txt')])
                                                }
                                            }
                                        }
                                        stage('Run MyPy Static Analysis') {
                                            steps{
                                                sh 'mypy --version'
                                                catchError(buildResult: 'SUCCESS', message: 'MyPy found issues', stageResult: "UNSTABLE") {
                                                    tee('logs/mypy.log'){
                                                        sh(label: 'Running MyPy',
                                                           script: 'mypy -p speedwagon --exclude speedwagon/ui/ --html-report reports/mypy/html'
                                                        )
                                                    }
                                                }
                                            }
                                            post {
                                                always {
                                                    recordIssues(tools: [myPy(pattern: 'logs/mypy.log')])
                                                    publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/mypy/html/', reportFiles: 'index.html', reportName: 'MyPy HTML Report', reportTitles: ''])
                                                }
                                                cleanup{
                                                    cleanWs(patterns: [[pattern: 'logs/mypy.log', type: 'INCLUDE']])
                                                }
                                            }
                                        }

                                        stage('Run Pylint Static Analysis') {
                                            steps{
                                                run_pylint()
                                            }
                                            post{
                                                always{
                                                    stash includes: 'reports/pylint_issues.txt,reports/pylint.txt', name: 'PYLINT_REPORT'
                                                    recordIssues(tools: [pyLint(pattern: 'reports/pylint_issues.txt')])
                                                }
                                            }
                                        }
                                        stage('Run Flake8 Static Analysis') {
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'Flake8 found issues', stageResult: "UNSTABLE") {
                                                    sh script: 'flake8 speedwagon --tee --output-file=logs/flake8.log'
                                                }
                                            }
                                            post {
                                                always {
                                                      stash includes: 'logs/flake8.log', name: 'FLAKE8_REPORT'
                                                      recordIssues(tools: [flake8(pattern: 'logs/flake8.log')])
                                                }
                                            }
                                        }
                                        stage("pyDocStyle"){
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'Did not pass all pyDocStyle tests', stageResult: 'UNSTABLE') {
                                                    sh(
                                                        label: "Run pydocstyle",
                                                        script: '''mkdir -p reports
                                                                   pydocstyle speedwagon > reports/pydocstyle-report.txt
                                                                   '''
                                                    )
                                                }
                                            }
                                            post {
                                                always{
                                                    recordIssues(tools: [pyDocStyle(pattern: 'reports/pydocstyle-report.txt')])
                                                }
                                            }
                                        }
                                    }
                                    post{
                                        always{
                                            sh 'coverage combine && coverage xml -o reports/coverage.xml && coverage html -d reports/coverage'
                                            stash includes: 'reports/coverage.xml', name: 'COVERAGE_REPORT_DATA'
//                                             publishCoverage(
//                                                 adapters: [
//                                                         coberturaAdapter('reports/coverage.xml')
//                                                     ],
//                                                 calculateDiffForChangeRequests: true,
//                                                 sourceFileResolver: sourceFiles('STORE_ALL_BUILD')
//                                             )
                                        }
                                    }
                                }
                            }
                            post{
                                cleanup{
                                    cleanWs(patterns: [
                                            [pattern: 'logs/*', type: 'INCLUDE'],
                                            [pattern: 'reports/', type: 'INCLUDE'],
                                            [pattern: '.coverage', type: 'INCLUDE']
                                        ])
                                }
                            }
                        }
                        stage('Run Sonarqube Analysis'){
                            options{
                                lock('speedwagon-sonarscanner')
                            }
                            when{
                                equals expected: true, actual: params.USE_SONARQUBE
                                beforeAgent true
                                beforeOptions true
                            }
                            steps{
                                script{
                                    def sonarqube = load('ci/jenkins/scripts/sonarqube.groovy')
                                    def stashes = [
                                        'COVERAGE_REPORT_DATA',
                                        'PYTEST_UNIT_TEST_RESULTS',
                                        'PYLINT_REPORT',
                                        'FLAKE8_REPORT'
                                    ]
                                    stashes.each{
                                        unstash "$it"
                                    }
                                    def sonarqubeConfig = [
                                                installationName: 'sonarcloud',
                                                credentialsId: 'sonarcloud-speedwagon',
                                            ]
                                    def agent = [
                                                    dockerfile: [
                                                        filename: 'ci/docker/python/linux/jenkins/Dockerfile',
                                                        label: 'linux && docker',
                                                        additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL',
                                                        args: '--mount source=sonar-cache-speedwagon,target=/opt/sonar/.sonar/cache',
                                                    ]
                                                ]
                                    milestone label: 'sonarcloud'
                                    if (env.CHANGE_ID){
                                        sonarqube.submitToSonarcloud(
                                            agent: agent,
                                            reportStashes: stashes,
                                            artifactStash: 'sonarqube artifacts',
                                            sonarqube: sonarqubeConfig,
                                            pullRequest: [
                                                source: env.CHANGE_ID,
                                                destination: env.BRANCH_NAME,
                                            ],
                                            package: [
                                                version: props.Version,
                                                name: props.Name
                                            ],
                                        )
                                    } else {
                                        sonarqube.submitToSonarcloud(
                                            agent: agent,
                                            reportStashes: stashes,
                                            artifactStash: 'sonarqube artifacts',
                                            sonarqube: sonarqubeConfig,
                                            package: [
                                                version: props.Version,
                                                name: props.Name
                                            ]
                                        )
                                    }
                                }
                            }
                            post {
                                always{
                                    recordIssues(tools: [sonarQube(pattern: 'reports/sonar-report.json')])
                                }
                            }
                        }
                    }
                }
                stage('Run Tox'){
                    when{
                        equals expected: true, actual: params.TEST_RUN_TOX
                    }
                    steps {
                        runTox()
                    }
                }
            }
        }
        stage('Packaging'){
            when{
                anyOf{
                    equals expected: true, actual: params.BUILD_PACKAGES
                    equals expected: true, actual: params.BUILD_CHOCOLATEY_PACKAGE
                    equals expected: true, actual: params.DEPLOY_DEVPI
                    equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION
                    equals expected: true, actual: params.DEPLOY_CHOCOLATEY
                }
                beforeAgent true
            }
            stages{
                stage('Python Packages'){
                    stages{
                        stage('Packaging sdist and wheel'){
                            agent {
                                dockerfile {
                                    filename 'ci/docker/python/linux/jenkins/Dockerfile'
                                    label 'linux && docker'
                                    additionalBuildArgs ' --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                                  }
                            }
                            steps{
                                timeout(5){
                                    sh script: 'python -m build .'
                                }
                            }
                            post{
                                always{
                                    stash includes: 'dist/*.whl,dist/*.tar.gz,dist/*.zip', name: 'PYTHON_PACKAGES'
                                    stash includes: 'dist/*.whl', name: 'PYTHON_WHL_PACKAGE'
                                    stash includes: 'dist/*.tar.gz,dist/*.zip', name: 'PYTHON_SDIST_PACKAGE'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE']
                                            ]
                                        )
                                }
                            }
                        }
                        stage('Testing Python Package'){
                            when{
                                equals expected: true, actual: params.TEST_PACKAGES
                            }
                            steps{
                                testPythonPackages()
//                                 script{
//                                     def packages
//                                     node(){
//                                         checkout scm
//                                         packages = load 'ci/jenkins/scripts/packaging.groovy'
//                                     }
//                                     def windowsTests = [:]
//                                     SUPPORTED_WINDOWS_VERSIONS.each{ pythonVersion ->
//                                         windowsTests["Windows - Python ${pythonVersion}: sdist"] = {
//                                             packages.testPkg(
//                                                 agent: [
//                                                     dockerfile: [
//                                                         label: 'windows && docker',
//                                                         filename: 'ci/docker/python/windows/tox/Dockerfile',
//                                                         additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE'
//                                                     ]
//                                                 ],
//                                                 glob: 'dist/*.tar.gz,dist/*.zip',
//                                                 stash: 'PYTHON_PACKAGES',
//                                                 pythonVersion: pythonVersion,
//                                                 retry: 3,
//                                             )
//                                         }
//                                         windowsTests["Windows - Python ${pythonVersion}: wheel"] = {
//                                             packages.testPkg(
//                                                 agent: [
//                                                     dockerfile: [
//                                                         label: 'windows && docker',
//                                                         filename: 'ci/docker/python/windows/tox/Dockerfile',
//                                                         additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE'
//                                                     ]
//                                                 ],
//                                                 glob: 'dist/*.whl',
//                                                 stash: 'PYTHON_PACKAGES',
//                                                 pythonVersion: pythonVersion,
//                                                 retry: 3,
//                                             )
//                                         }
//                                     }
//                                     def linuxTests = [:]
//                                     SUPPORTED_LINUX_VERSIONS.each{ pythonVersion ->
//                                         linuxTests["Linux - Python ${pythonVersion}: sdist"] = {
//                                             packages.testPkg(
//                                                 agent: [
//                                                     dockerfile: [
//                                                         label: 'linux && docker',
//                                                         filename: 'ci/docker/python/linux/tox/Dockerfile',
//                                                         additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
//                                                     ]
//                                                 ],
//                                                 glob: 'dist/*.tar.gz',
//                                                 stash: 'PYTHON_PACKAGES',
//                                                 pythonVersion: pythonVersion,
//                                                 retry: 3,
//                                             )
//                                         }
//                                         linuxTests["Linux - Python ${pythonVersion}: wheel"] = {
//                                             packages.testPkg(
//                                                 agent: [
//                                                     dockerfile: [
//                                                         label: 'linux && docker',
//                                                         filename: 'ci/docker/python/linux/tox/Dockerfile',
//                                                         additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
//                                                     ]
//                                                 ],
//                                                 glob: 'dist/*.whl',
//                                                 stash: 'PYTHON_PACKAGES',
//                                                 pythonVersion: pythonVersion,
//                                                 retry: 3,
//                                             )
//                                         }
//                                     }
//                                     def tests = linuxTests + windowsTests
//                                     def macTests = [:]
//
//                                     SUPPORTED_MAC_VERSIONS.each{ pythonVersion ->
//                                         macTests["Mac - Python ${pythonVersion}: sdist"] = {
//                                             withEnv(['QT_QPA_PLATFORM=offscreen']) {
//                                                 packages.testPkg(
//                                                     agent: [
//                                                         label: "mac && python${pythonVersion}",
//                                                     ],
//                                                     glob: 'dist/*.tar.gz,dist/*.zip',
//                                                     stash: 'PYTHON_PACKAGES',
//                                                     pythonVersion: pythonVersion,
//                                                     toxExec: 'venv/bin/tox',
//                                                     testSetup: {
//                                                         checkout scm
//                                                         unstash 'PYTHON_PACKAGES'
//                                                         sh(
//                                                             label:'Install Tox',
//                                                             script: '''python3 -m venv venv
//                                                                        venv/bin/pip install pip --upgrade
//                                                                        venv/bin/pip install tox
//                                                                        '''
//                                                         )
//                                                     },
//                                                     testTeardown: {
//                                                         sh 'rm -r venv/'
//                                                     },
//                                                     retry: 3,
//                                                 )
//                                             }
//                                         }
//                                         macTests["Mac - Python ${pythonVersion}: wheel"] = {
//                                             withEnv(['QT_QPA_PLATFORM=offscreen']) {
//                                                 packages.testPkg(
//                                                     agent: [
//                                                         label: "mac && python${pythonVersion}",
//                                                     ],
//                                                     glob: 'dist/*.whl',
//                                                     stash: 'PYTHON_PACKAGES',
//                                                     pythonVersion: pythonVersion,
//                                                     toxExec: 'venv/bin/tox',
//                                                     testSetup: {
//                                                         checkout scm
//                                                         unstash 'PYTHON_PACKAGES'
//                                                         sh(
//                                                             label:'Install Tox',
//                                                             script: '''python3 -m venv venv
//                                                                        venv/bin/pip install pip --upgrade
//                                                                        venv/bin/pip install tox
//                                                                        '''
//                                                         )
//                                                     },
//                                                     testTeardown: {
//                                                         sh 'rm -r venv/'
//                                                     },
//                                                     retry: 3,
//
//                                                 )
//                                             }
//                                         }
//                                     }
//                                     if(params.TEST_PACKAGES_ON_MAC == true){
//                                         tests = tests + macTests
//                                     }
//                                     parallel(tests)
//                                 }
                            }
                        }
                    }
                }
                stage('End-user packages'){
                    parallel{
                        stage('Mac Application Bundle'){
                            agent{
                                label 'mac && python3'
                            }
                            when{
                                anyOf{
                                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                    equals expected: true, actual: params.DEPLOY_DMG
                                }
                            }
                            steps{
                                unstash 'PYTHON_PACKAGES'
                                sh(
                                    label: 'Creating build environment',
                                    script: '''python3 -m venv --upgrade-deps venv
                                                venv/bin/pip install pyinstaller
                                    '''
                                    )
                                script{
                                    findFiles(glob: 'dist/speedwagon*.whl').each{ wheel ->
                                        sh(label: "Installing ${wheel.name}", script: "venv/bin/pip install ${wheel}")
                                    }
                                }
                                sh(label: 'Running pyinstaller script', script: 'venv/bin/python packaging/create_osx_app_bundle.py')
                                sh(label: 'Packaging installer as .dmg file',
                                    script:"""
                                        mkdir -p build/appleBundle
                                        mv \$WORKSPACE/dist/*.app build/appleBundle/
                                        ln -s /Applications build/appleBundle/Applications
                                        hdiutil create build/tmp.dmg -ov -volname \"SpeedwagonInstall\" -fs HFS+ -srcfolder \"\$WORKSPACE/build/appleBundle/\"
                                        hdiutil convert build/tmp.dmg -format UDZO -o dist/Speedwagon-${props.Version}.dmg
                                        """
                                    )
                            }
                            post{
                                success{
                                    archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                    stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_BUNDLE'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'build/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                        ]
                                    )
                                }
                            }
                        }
                        stage('Chocolatey'){
                            when{
                                anyOf{
                                    equals expected: true, actual: params.DEPLOY_CHOCOLATEY
                                    equals expected: true, actual: params.BUILD_CHOCOLATEY_PACKAGE
                                }
                                beforeInput true
                            }
                            stages{
                                stage('Packaging python dependencies'){
                                    steps{
                                        create_wheels()
                                    }
                                }
                                stage('Package for Chocolatey'){
                                    agent {
                                        dockerfile {
                                            filename 'ci/docker/chocolatey_package/Dockerfile'
                                            label 'windows && docker'
                                            additionalBuildArgs '--build-arg CHOCOLATEY_SOURCE'
                                          }
                                    }
                                    steps{
                                        unstash 'PYTHON_PACKAGES'
                                        script {
                                            findFiles(glob: 'dist/*.whl').each{
                                                [
                                                    'PYTHON_DEPS_3.10',
                                                    'PYTHON_DEPS_3.9',
                                                    'PYTHON_DEPS_3.8',
                                                    'PYTHON_DEPS_3.7',
                                                    'SPEEDWAGON_DOC_PDF'
                                                ].each{ stashName ->
                                                    unstash stashName
                                                }
                                                createNewChocolateyPackage(
                                                    name: 'speedwagon',
                                                    version: props.Version,
                                                    summary: props.Summary,
                                                    maintainer: props.Maintainer,
                                                    files:[
                                                            applicationWheel: it.path,
                                                            dependenciesDir: '.\\deps',
                                                            docsDir: '.\\dist\\docs'
                                                        ]
                                                    )
                                            }
                                        }
                                    }
                                    post{
                                        always{
                                            archiveArtifacts artifacts: 'packages/**/*.nuspec,packages/*.nupkg'
                                            stash includes: 'packages/*.nupkg', name: 'CHOCOLATEY_PACKAGE'
                                        }
                                        cleanup{
                                            cleanWs(
                                                deleteDirs: true,
                                                patterns: [
                                                    [pattern: 'packages/', type: 'INCLUDE']
                                                    ]
                                                )
                                        }
                                    }
                                }
                                stage('Testing Chocolatey Package'){
                                    agent {
                                        dockerfile {
                                            filename 'ci/docker/chocolatey_package/Dockerfile'
                                            label 'windows && docker'
                                            additionalBuildArgs '--build-arg CHOCOLATEY_SOURCE'
                                          }
                                    }
                                    when{
                                        equals expected: true, actual: params.TEST_PACKAGES
                                        beforeAgent true
                                    }
                                    steps{
                                        unstash 'CHOCOLATEY_PACKAGE'
                                        testSpeedwagonChocolateyPkg(props.Version)
                                    }
                                }
                            }
                        }
                        stage('Windows Standalone'){
                            when{
                                anyOf{
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                                }
                                beforeAgent true
                            }
                            stages{
                                stage('CMake Build'){
                                    agent {
                                        dockerfile {
                                            filename 'ci/docker/windows_standalone/Dockerfile'
                                            label 'Windows&&Docker'
                                            args '-u ContainerAdministrator'
                                            additionalBuildArgs '--build-arg CHOCOLATEY_SOURCE'
                                          }
                                    }
                                    steps {
                                        unstash 'SPEEDWAGON_DOC_PDF'
                                        script{
                                            withEnv(["build_number=${get_build_number()}"]) {
                                                load('ci/jenkins/scripts/standalone.groovy').build_standalone(
                                                    packageFormat: [
                                                        msi: params.PACKAGE_WINDOWS_STANDALONE_MSI,
                                                        nsis: params.PACKAGE_WINDOWS_STANDALONE_NSIS,
                                                        zipFile: params.PACKAGE_WINDOWS_STANDALONE_ZIP,
                                                    ],
                                                    package: [
                                                        version: props.Version
                                                    ]
                                                )
                                            }
                                        }
                                    }
                                    post {
                                        success{
                                            archiveArtifacts artifacts: 'dist/*.msi,dist/*.exe,dist/*.zip', fingerprint: true
                                            stash includes: 'dist/*.msi,dist/*.exe,dist/*.zip', name: 'STANDALONE_INSTALLERS'
                                        }
                                        failure {
                                            archiveArtifacts allowEmptyArchive: true, artifacts: 'dist/**/wix.log,dist/**/*.wxs'
                                        }
                                        cleanup{
                                            cleanWs(
                                                deleteDirs: true,
                                                notFailBuild: true
                                            )
                                        }
                                    }
                                }
                                stage('Testing MSI Install'){
                                    agent {
                                      docker {
                                        args '-u ContainerAdministrator'
                                        image 'mcr.microsoft.com/windows/servercore:ltsc2019'
                                        label 'Windows && Docker'
                                      }
                                    }
                                    when{
                                        equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                        beforeAgent true
                                    }
                                    steps{
                                        timeout(15){
                                            unstash 'STANDALONE_INSTALLERS'
                                            script{
                                                def standalone = load('ci/jenkins/scripts/standalone.groovy')
                                                standalone.testInstall('dist/*.msi')
                                            }
                                        }
                                    }
                                    post {
                                        cleanup{
                                            cleanWs(
                                                deleteDirs: true,
                                                notFailBuild: true,
                                                patterns: [
                                                    [pattern: 'dist/', type: 'INCLUDE']
                                                ]
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        stage('Deploy to Devpi'){
            when {
                allOf{
                    equals expected: true, actual: params.DEPLOY_DEVPI
                    anyOf {
                        equals expected: 'master', actual: env.BRANCH_NAME
                        equals expected: 'dev', actual: env.BRANCH_NAME
                        tag '*'
                    }
                }
                beforeAgent true
                beforeOptions true
            }
            agent none
            options{
                lock('speedwagon-devpi')
            }
            stages{
                stage('Deploy to Devpi Staging') {
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/jenkins/Dockerfile'
                            label 'linux&&docker'
                            additionalBuildArgs ' --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                          }
                    }
                    steps {
                        unstash 'DOCS_ARCHIVE'
                        unstash 'PYTHON_PACKAGES'
                        script{
                            load('ci/jenkins/scripts/devpi.groovy').upload(
                                    server: 'https://devpi.library.illinois.edu',
                                    credentialsId: 'DS_devpi',
                                    index: getDevPiStagingIndex(),
                                    clientDir: './devpi'
                                )
                        }
                    }
                }
                stage("Test DevPi packages") {
                    steps{
                        script{
                            def devpi
                            node(){
                                devpi = load('ci/jenkins/scripts/devpi.groovy')
                            }
                             def macPackages = [:]
                            SUPPORTED_MAC_VERSIONS.each{pythonVersion ->
                                macPackages["Test Python ${pythonVersion}: wheel Mac"] = {
                                    withEnv(['QT_QPA_PLATFORM=offscreen']) {
                                        devpi.testDevpiPackage(
                                            agent: [
                                                label: "mac && python${pythonVersion}"
                                            ],
                                            devpi: [
                                                index: DEVPI_CONFIG.index,
                                                server: DEVPI_CONFIG.server,
                                                credentialsId: DEVPI_CONFIG.credentialsId,
                                                devpiExec: 'venv/bin/devpi'
                                            ],
                                            package:[
                                                name: props.Name,
                                                version: props.Version,
                                                selector: 'whl'
                                            ],
                                            test:[
                                                setup: {
                                                    sh(
                                                        label:'Installing Devpi client',
                                                        script: '''python3 -m venv venv
                                                                    venv/bin/python -m pip install pip --upgrade
                                                                    venv/bin/python -m pip install devpi_client
                                                                    '''
                                                    )
                                                },
                                                toxEnv: "py${pythonVersion}".replace('.',''),
                                                teardown: {
                                                    sh( label: 'Remove Devpi client', script: 'rm -r venv')
                                                }
                                            ]
                                        )
                                    }
                                }
                                macPackages["Test Python ${pythonVersion}: sdist Mac"] = {
                                    withEnv(['QT_QPA_PLATFORM=offscreen']) {
                                        devpi.testDevpiPackage(
                                            agent: [
                                                label: "mac && python${pythonVersion}"
                                            ],
                                            devpi: [
                                                index: DEVPI_CONFIG.index,
                                                server: DEVPI_CONFIG.server,
                                                credentialsId: DEVPI_CONFIG.credentialsId,
                                                devpiExec: 'venv/bin/devpi'
                                            ],
                                            package:[
                                                name: props.Name,
                                                version: props.Version,
                                                selector: 'tar.gz'
                                            ],
                                            test:[
                                                setup: {
                                                    checkout scm
                                                    sh(
                                                        label:'Installing Devpi client',
                                                        script: '''python3 -m venv venv
                                                                    venv/bin/python -m pip install pip --upgrade
                                                                    venv/bin/python -m pip install devpi_client
                                                                    '''
                                                    )
                                                },
                                                toxEnv: "py${pythonVersion}".replace('.',''),
                                                teardown: {
                                                    sh( label: 'Remove Devpi client', script: 'rm -r venv')
                                                }
                                            ]
                                        )
                                    }
                                }
                            }
                            windowsPackages = [:]
                            SUPPORTED_WINDOWS_VERSIONS.each{pythonVersion ->
                                windowsPackages["Test Python ${pythonVersion}: sdist Windows"] = {
                                    devpi.testDevpiPackage(
                                        agent: [
                                            dockerfile: [
                                                filename: 'ci/docker/python/windows/tox/Dockerfile',
                                                additionalBuildArgs: "--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE",
                                                label: 'windows && docker'
                                            ]
                                        ],
                                        devpi: DEVPI_CONFIG,
                                        package:[
                                            name: props.Name,
                                            version: props.Version,
                                            selector: 'tar.gz'
                                        ],
                                        test:[
                                            toxEnv: "py${pythonVersion}".replace('.',''),
                                        ]
                                    )
                                }
                                windowsPackages["Test Python ${pythonVersion}: wheel Windows"] = {
                                    devpi.testDevpiPackage(
                                        agent: [
                                            dockerfile: [
                                                filename: 'ci/docker/python/windows/tox/Dockerfile',
                                                additionalBuildArgs: "--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE",
                                                label: 'windows && docker'
                                            ]
                                        ],
                                        devpi: DEVPI_CONFIG,
                                        package:[
                                            name: props.Name,
                                            version: props.Version,
                                            selector: 'whl'
                                        ],
                                        test:[
                                            toxEnv: "py${pythonVersion}".replace('.',''),
                                        ]
                                    )
                                }
                            }
                            def linuxPackages = [:]
                            SUPPORTED_LINUX_VERSIONS.each{pythonVersion ->
                                linuxPackages["Test Python ${pythonVersion}: sdist Linux"] = {
                                    devpi.testDevpiPackage(
                                        agent: [
                                            dockerfile: [
                                                filename: 'ci/docker/python/linux/tox/Dockerfile',
                                                additionalBuildArgs: "--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL",
                                                label: 'linux && docker'
                                            ]
                                        ],
                                        devpi: DEVPI_CONFIG,
                                        package:[
                                            name: props.Name,
                                            version: props.Version,
                                            selector: 'tar.gz'
                                        ],
                                        test:[
                                            toxEnv: "py${pythonVersion}".replace('.',''),
                                        ]
                                    )
                                }
                                linuxPackages["Test Python ${pythonVersion}: wheel Linux"] = {
                                    devpi.testDevpiPackage(
                                        agent: [
                                            dockerfile: [
                                                filename: 'ci/docker/python/linux/tox/Dockerfile',
                                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL',
                                                label: 'linux && docker'
                                            ]
                                        ],
                                        devpi: DEVPI_CONFIG,
                                        package:[
                                            name: props.Name,
                                            version: props.Version,
                                            selector: 'whl'
                                        ],
                                        test:[
                                            toxEnv: "py${pythonVersion}".replace('.',''),
                                        ]
                                    )
                                }
                            }
                            parallel(linuxPackages + windowsPackages + macPackages)
                        }
                    }
                }
                stage('Deploy to DevPi Production') {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION
                     
                            anyOf {
                                equals expected: 'master', actual: env.BRANCH_NAME
                                tag '*'
                            }
                        }
                        beforeAgent true
                        beforeInput true
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/jenkins/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                          }
                    }
                    input {
                        message 'Release to DevPi Production?'
                    }
                    steps {
                        script{
                            load('ci/jenkins/scripts/devpi.groovy').pushPackageToIndex(
                                pkgName: props.Name,
                                pkgVersion: props.Version,
                                server: 'https://devpi.library.illinois.edu',
                                indexSource: "DS_Jenkins/${getDevPiStagingIndex()}",
                                indexDestination: 'production/release',
                                credentialsId: 'DS_devpi'
                            )
                        }
                    }
                }
            }
            post{
                success{
                    node('linux && docker') {
                       script{
                            if (!env.TAG_NAME?.trim()){
                                docker.build('speedwagon:devpi','-f ./ci/docker/python/linux/jenkins/Dockerfile --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL .').inside{
                                    checkout scm
                                    load('ci/jenkins/scripts/devpi.groovy').pushPackageToIndex(
                                        pkgName: props.Name,
                                        pkgVersion: props.Version,
                                        server: 'https://devpi.library.illinois.edu',
                                        indexSource: "DS_Jenkins/${getDevPiStagingIndex()}",
                                        indexDestination: "DS_Jenkins/${env.BRANCH_NAME}",
                                        credentialsId: 'DS_devpi'
                                    )
                            }
                           }
                       }
                    }
                }
                cleanup{
                    node('linux && docker') {
                       script{
                            docker.build('speedwagon:devpi','-f ./ci/docker/python/linux/jenkins/Dockerfile --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL .').inside{
                                checkout scm
                                load('ci/jenkins/scripts/devpi.groovy').removePackage(
                                    pkgName: props.Name,
                                    pkgVersion: props.Version,
                                    index: "DS_Jenkins/${getDevPiStagingIndex()}",
                                    server: 'https://devpi.library.illinois.edu',
                                    credentialsId: 'DS_devpi',

                                )
                            }
                       }
                    }
                }
            }
        }
        stage('Deploy'){
            parallel {
                stage('Deploy to pypi') {
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/jenkins/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                        }
                    }
                    when{
                        allOf{
                            equals expected: true, actual: params.DEPLOY_PYPI
                            equals expected: true, actual: params.BUILD_PACKAGES
                        }
                        beforeAgent true
                        beforeInput true
                    }
                    options{
                        retry(3)
                    }
                    input {
                        message 'Upload to pypi server?'
                        parameters {
                            choice(
                                choices: PYPI_SERVERS,
                                description: 'Url to the pypi index to upload python packages.',
                                name: 'SERVER_URL'
                            )
                        }
                    }
                    steps{
                        unstash 'PYTHON_PACKAGES'
                        script{
                            def pypi = fileLoader.fromGit(
                                    'pypi',
                                    'https://github.com/UIUCLibrary/jenkins_helper_scripts.git',
                                    '2',
                                    null,
                                    ''
                                )
                            pypi.pypiUpload(
                                credentialsId: 'jenkins-nexus',
                                repositoryUrl: SERVER_URL,
                                glob: 'dist/*'
                                )
                        }
                    }
                    post{
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                        [pattern: 'dist/', type: 'INCLUDE']
                                    ]
                            )
                        }
                    }
                }
                stage('Deploy to Chocolatey') {
                    when{
                        equals expected: true, actual: params.DEPLOY_CHOCOLATEY
                        beforeInput true
                        beforeAgent true
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/chocolatey_package/Dockerfile'
                            label 'windows && docker'
                            additionalBuildArgs '--build-arg CHOCOLATEY_SOURCE'
                          }
                    }
                    options{
                        timeout(time: 1, unit: 'DAYS')
                        retry(3)
                    }
                    input {
                        message 'Deploy to Chocolatey server'
                        id 'CHOCOLATEY_DEPLOYMENT'
                        parameters {
                            choice(
                                choices: [
                                    'https://jenkins.library.illinois.edu/nexus/repository/chocolatey-hosted-beta/',
                                    'https://jenkins.library.illinois.edu/nexus/repository/chocolatey-hosted-public/'
                                ],
                                description: 'Chocolatey Server to deploy to',
                                name: 'CHOCOLATEY_SERVER'
                            )
                        }
                    }
                    steps{
                        unstash 'CHOCOLATEY_PACKAGE'
                        script{
                            def chocolatey = load('ci/jenkins/scripts/chocolatey.groovy')
                            chocolatey.deploy_to_chocolatey(CHOCOLATEY_SERVER)
                        }

                    }
                }
                stage('Deploy Online Documentation') {
                    when{
                        equals expected: true, actual: params.DEPLOY_DOCS
                        beforeAgent true
                        beforeInput true
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/jenkins/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs ' --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                          }
                    }
                    options{
                        timeout(time: 1, unit: 'DAYS')
                    }
                    input {
                        message 'Update project documentation?'
                    }
                    steps{
                        unstash 'DOCS_ARCHIVE'
                        withCredentials([usernamePassword(credentialsId: 'dccdocs-server', passwordVariable: 'docsPassword', usernameVariable: 'docsUsername')]) {
                            sh 'python utils/upload_docs.py --username=$docsUsername --password=$docsPassword --subroute=speedwagon build/docs/html apache-ns.library.illinois.edu'
                        }
                    }
                    post{
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: 'build/', type: 'INCLUDE'],
                                    [pattern: 'dist/', type: 'INCLUDE'],
                                ]
                            )
                        }
                    }
                }
//                 stage('Deploy Online Documentation') {
//                     when{
//                         equals expected: true, actual: params.DEPLOY_DOCS
//                         beforeAgent true
//                         beforeInput true
//                     }
//                     agent any
//                     input {
//                         message 'Update project documentation?'
//                     }
//                     steps{
//                         unstash 'DOCS_ARCHIVE'
//                         dir('build/docs/html/'){
//                             sshPublisher(
//                                 publishers: [
//                                     sshPublisherDesc(
//                                         configName: 'apache-ns - lib-dccuser-updater',
//                                         sshLabel: [label: 'Linux'],
//                                         transfers: [sshTransfer(excludes: '',
//                                         execCommand: '',
//                                         execTimeout: 120000,
//                                         flatten: false,
//                                         makeEmptyDirs: false,
//                                         noDefaultExcludes: false,
//                                         patternSeparator: '[, ]+',
//                                         remoteDirectory: params.DEPLOY_DOCS_URL_SUBFOLDER,
//                                         remoteDirectorySDF: false,
//                                         removePrefix: '',
//                                         sourceFiles: '**')],
//                                     usePromotionTimestamp: false,
//                                     useWorkspaceInPromotion: false,
//                                     verbose: true
//                                     )
//                                 ]
//                             )
//                         }
//                     }
//                     post{
//                         success{
//                             jiraComment body: "Documentation updated. https://www.library.illinois.edu/dccdocs/${params.DEPLOY_DOCS_URL_SUBFOLDER}", issueKey: params.JIRA_ISSUE_VALUE
//                         }
//                         cleanup{
//                             cleanWs(
//                                 deleteDirs: true,
//                                 patterns: [
//                                     [pattern: 'build/', type: 'INCLUDE']
//                                 ]
//                             )
//                         }
//                     }
//                 }
                stage('Deploy MacOS DMG to Nexus'){
                    when{
                        equals expected: true, actual: params.DEPLOY_DMG
                        beforeAgent true
                        beforeInput true
                    }
                    agent any
                    input {
                        message 'Upload to Nexus server?'
                        parameters {
                            credentials credentialType: 'com.cloudbees.plugins.credentials.common.StandardCredentials', defaultValue: 'jenkins-nexus', name: 'NEXUS_CREDS', required: true
                            choice(
                                choices: NEXUS_SERVERS,
                                description: 'Url to upload artifact.',
                                name: 'SERVER_URL'
                            )
                            string defaultValue: 'speedwagon', description: 'subdirectory to store artifact', name: 'archiveFolder'
                        }
                    }
                    steps{
                        unstash 'APPLE_APPLICATION_BUNDLE'
                        script{
                            findFiles(glob: 'dist/*.dmg').each{
                                try{
                                    def put_response = httpRequest authentication: NEXUS_CREDS, httpMode: 'PUT', uploadFile: it.path, url: "${SERVER_URL}/${archiveFolder}/${it.name}", wrapAsMultipart: false
                                } catch(Exception e){
                                    echo "http request response: ${put_response.content}"
                                    throw e;
                                }
                            }
                        }
                    }
                    post{
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: 'dist/', type: 'INCLUDE']
                                ]
                            )
                        }
                    }
                }
                stage('Deploy standalone to Hathi tools Beta'){
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
                        label 'Windows'
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    steps {
                        unstash 'STANDALONE_INSTALLERS'
                        unstash 'SPEEDWAGON_DOC_PDF'
                        unstash 'DOCS_ARCHIVE'
                        script{
                            deploy_artifacts_to_url('dist/*.msi,dist/*.exe,dist/*.zip,dist/*.tar.gz,dist/docs/*.pdf', "https://jenkins.library.illinois.edu/nexus/repository/prescon-beta/speedwagon/${props.Version}/", params.JIRA_ISSUE_VALUE)
                        }
                    }
                    post{
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: 'dist.*', type: 'INCLUDE']
                                ]
                            )
                        }
                    }
                }
                stage('Deploy Standalone Build to SCCM') {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_SCCM
                            anyOf{
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                            }
                            branch 'master'
                        }
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    agent any
                    steps {
                        unstash 'STANDALONE_INSTALLERS'
                        dir('dist'){
                            deploy_sscm('*.msi', props.Version, params.JIRA_ISSUE_VALUE)
                        }
                    }
                    post {
                        success {
                            jiraComment body: "Deployment request was sent to SCCM for version ${PKG_VERSION}.", issueKey: params.JIRA_ISSUE_VALUE
                            archiveArtifacts artifacts: 'logs/deployment_request.txt'
                        }
                    }
                }
            }
        }
    }
}
