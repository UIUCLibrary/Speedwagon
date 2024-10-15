library identifier: 'JenkinsPythonHelperLibrary@2024.1.2', retriever: modernSCM(
  [$class: 'GitSCMSource',
   remote: 'https://github.com/UIUCLibrary/JenkinsPythonHelperLibrary.git',
   ])

// Note:
// Python version 3.8 testing is not supported on mac because PySide 6.5.3 doesn't work on python 3.8.10 and that's
// the last version that was distributed with a mac installer. It does work with the latest version of python 3.8
// on MacOS if you compile it yourself or get it off of homebrew.
SUPPORTED_MAC_VERSIONS = ['3.9', '3.10', '3.11']
SUPPORTED_LINUX_VERSIONS = ['3.8', '3.9', '3.10', '3.11']
SUPPORTED_WINDOWS_VERSIONS = ['3.8', '3.9', '3.10', '3.11']
DOCKER_PLATFORM_BUILD_ARGS = [
    linux: '',
    windows: '--build-arg CHOCOLATEY_SOURCE'
]

def getPypiConfig() {
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'pypi_config', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['deployment']['indexes']
            }
        }
    }
}
def getChocolateyServers() {
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'deploymentStorageConfig', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['chocolatey']['sources']
            }
        }
    }
}

def getStandAloneStorageServers(){
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'deploymentStorageConfig', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['publicReleases']['urls']
            }
        }
    }
}


def deployStandalone(glob, url) {
    script{
        findFiles(glob: glob).each{
            try{
                def put_response = httpRequest authentication: NEXUS_CREDS, httpMode: 'PUT', uploadFile: it.path, url: "${url}/${it.name}", wrapAsMultipart: false
                echo "http request response: ${put_response.content}"
            } catch(Exception e){
                throw e;
            }
        }
    //                                    deploy_artifacts_to_url('dist/*.msi,dist/*.exe,dist/*.zip,dist/*.tar.gz,dist/docs/*.pdf,dist/docs/*.dng', "https://jenkins.library.illinois.edu/nexus/repository/prescon-beta/speedwagon/${props.version}/")
    }
}
def macAppleBundle() {

    stage('Create Build Environment'){
        unstash 'PYTHON_PACKAGES'
        sh(
            label: 'Creating build environment',
            script: '''python3 -m venv --upgrade-deps venv
                       . ./venv/bin/activate
                       pip install wheel
                       pip install -r requirements-freeze.txt
            '''
            )
        findFiles(glob: 'dist/speedwagon*.whl').each{ wheel ->
            sh(label: "Installing ${wheel.name}", script: "venv/bin/pip install ${wheel}")
        }
        sh('venv/bin/pip list')
    }
    stage('Building Apple Application Bundle'){
        sh(label: 'Running pyinstaller script', script: 'venv/bin/python packaging/create_osx_app_bundle.py')
        findFiles(glob: 'dist/*.dmg').each{

            echo "SHA256 value of ${it.path} = \"${sha256 (it.path)}\""
        }

    }

}

def run_pylint(){
    def MAX_TIME = 10
    withEnv(['PYLINTHOME=.']) {
        sh 'pylint --version'
        catchError(buildResult: 'SUCCESS', message: 'Pylint found issues', stageResult: 'UNSTABLE') {
            timeout(MAX_TIME){
                tee('reports/pylint_issues.txt'){
                    sh(
                        label: 'Running pylint',
                        script: 'pylint speedwagon -j 2 -r n --msg-template="{path}:{module}:{line}: [{msg_id}({symbol}), {obj}] {msg}"',
                    )
                }
            }
        }
        timeout(MAX_TIME){
            sh(
                label: 'Running pylint for sonarqube',
                script: 'pylint speedwagon -j 2 -d duplicate-code --output-format=parseable | tee reports/pylint.txt',
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
            return ''
        }
    }
}

def testSpeedwagonChocolateyPkg(version){
    script{
        def chocolatey = load('ci/jenkins/scripts/chocolatey.groovy')
        chocolatey.install_chocolatey_package(
            name: 'speedwagon',
            version: chocolatey.sanitize_chocolatey_version(version),
            source: './packages/;CHOCOLATEY_SOURCE;chocolatey',
            retries: 3
        )
    }
    powershell(
            label: 'Checking for Start Menu shortcut',
            script: 'Get-ChildItem "$Env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs" -Recurse -Include *.lnk'
        )
//    powershell('''
//        $proc = Start-Process "$Env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\speedwagon\\speedwagon.lnk" --PassThru
//        (Get-Process -Id $proc.Id).MainWindowHandle
//        Stop-Process -Id $proc.Id
//        '''
//    )
    bat 'speedwagon --help'
}

def testReinstallSpeedwagonChocolateyPkg(version){
    script{
        def chocolatey = load('ci/jenkins/scripts/chocolatey.groovy')
        chocolatey.reinstall_chocolatey_package(
            name: 'speedwagon',
            version: chocolatey.sanitize_chocolatey_version(version),
            source: './packages/;CHOCOLATEY_SOURCE;chocolatey',
            retries: 3
        )
    }
    powershell(
            label: 'Checking for Start Menu shortcut',
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
        'Enable Git Forensics': {
            node(){
                checkout scm
                mineRepository()
            }
        },
    ]
    )

}


def testPythonPackages(){
    script{
        def windowsTests = [:]
        SUPPORTED_WINDOWS_VERSIONS.each{ pythonVersion ->
            if(params.INCLUDE_WINDOWS_X86_64 == true){
                windowsTests["Windows - Python ${pythonVersion}-x86: sdist"] = {
                    testPythonPkg(
                        agent: [
                            dockerfile: [
                                label: 'windows && docker && x86',
                                filename: 'ci/docker/python/windows/tox/Dockerfile',
                                additionalBuildArgs:  '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg UV_EXTRA_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv',
                                args: '-v pipcache_speedwagon:c:/users/containeradministrator/appdata/local/pip -v uvcache_speedwagon:c:/users/containeradministrator/appdata/local/uv'
                            ]
                        ],
                        retries: 3,
                        testSetup: {
                             checkout scm
                             unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                             findFiles(glob: 'dist/*.tar.gz,dist/*.zip').each{
                                 powershell(label: 'Running Tox', script: "tox --installpkg ${it.path} --workdir \$env:TEMP\\tox  -e py${pythonVersion.replace('.', '')}-PySide6")
                             }

                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
                windowsTests["Windows - Python ${pythonVersion}-x86: wheel"] = {
                    testPythonPkg(
                        agent: [
                            dockerfile: [
                                label: 'windows && docker && x86',
                                filename: 'ci/docker/python/windows/tox/Dockerfile',
                                additionalBuildArgs:  '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg UV_EXTRA_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv',
                                args: '-v pipcache_speedwagon:c:/users/containeradministrator/appdata/local/pip -v uvcache_speedwagon:c:/users/containeradministrator/appdata/local/uv'
                            ]
                        ],
                        retries: 3,
                        testSetup: {
                             checkout scm
                             unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                             findFiles(glob: 'dist/*.whl').each{
                                 powershell(label: 'Running Tox', script: "tox --installpkg ${it.path} --workdir \$env:TEMP\\tox  -e py${pythonVersion.replace('.', '')}-PySide6")
                             }

                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
            }
        }
        def linuxTests = [:]
        SUPPORTED_LINUX_VERSIONS.each{ pythonVersion ->
            def architectures = []
            if(params.INCLUDE_LINUX_X86_64 == true){
                architectures.add('x86_64')
            }
            if(params.INCLUDE_LINUX_ARM == true){
                architectures.add('arm')
            }
            // As of 12/7/2023 there are no prebuilt binary wheel on ARM64 for
            // Python versions prior to 3.11 so there is no reason to run
            // tox tests that have a GUI.
            def linuxToxEnvironments = [
                "3.8": [
                    "x86_64": "py38-PySide6",
                    "arm": "py38"
                ],
                "3.9": [
                    "x86_64": "py39-PySide6",
                    "arm": "py39"
                ],
                "3.10": [
                    "x86_64": "py310-PySide6",
                    "arm": "py310"
                ],
                "3.11": [
                    "x86_64": "py311-PySide6",
                    "arm": "py311-PySide6"
                ],
            ]
            architectures.each{ processorArchitecture ->
                linuxTests["Linux-${processorArchitecture} - Python ${pythonVersion}: sdist"] = {
                    testPythonPkg(
                        agent: [
                            dockerfile: [
                                label: "linux && docker && ${processorArchitecture}",
                                filename: 'ci/docker/python/linux/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg PIP_DOWNLOAD_CACHE=/.cache/pip --build-arg UV_EXTRA_INDEX_URL --build-arg UV_CACHE_DIR=/.cache/uv',
                                args: '-v pipcache_speedwagon:/.cache/pip -v uvcache_speedwagon:/.cache/uv'
                            ]
                        ],
                        retries: 3,
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                            findFiles(glob: 'dist/*.tar.gz').each{
                                sh(
                                    label: 'Running Tox',
                                    script: "tox --installpkg ${it.path} --workdir /tmp/tox -e ${linuxToxEnvironments[pythonVersion][processorArchitecture]}"
                                    )
                            }
                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
                linuxTests["Linux-${processorArchitecture} - Python ${pythonVersion}: wheel"] = {
                    testPythonPkg(
                        agent: [
                            dockerfile: [
                                label: "linux && docker && ${processorArchitecture}",
                                filename: 'ci/docker/python/linux/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg PIP_DOWNLOAD_CACHE=/.cache/pip --build-arg UV_EXTRA_INDEX_URL --build-arg UV_CACHE_DIR=/.cache/uv',
                                args: '-v pipcache_speedwagon:/.cache/pip -v uvcache_speedwagon:/.cache/uv'
                            ]
                        ],
                        retries: 3,
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                            findFiles(glob: 'dist/*.whl').each{
                                sh(
                                    label: 'Running Tox',
                                    script: "tox --installpkg ${it.path} --workdir /tmp/tox -e ${linuxToxEnvironments[pythonVersion][processorArchitecture]}"
                                    )
                            }
                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
            }
        }
        def macTests = [:]

        SUPPORTED_MAC_VERSIONS.each{ pythonVersion ->
            def architectures = []
            if(params.INCLUDE_MACOS_X86_64 == true){
                architectures.add('x86_64')
            }
            if(params.INCLUDE_MACOS_ARM == true){
                architectures.add('m1')
            }
            architectures.each{ processorArchitecture ->
                macTests["Mac - ${processorArchitecture} - Python ${pythonVersion}: wheel"] = {
                    testPythonPkg(
                        agent: [
                            label: "mac && python${pythonVersion} && ${processorArchitecture}",
                        ],
                        retries: 3,
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                            findFiles(glob: 'dist/*.whl').each{
                                sh(label: 'Running Tox',
                                   script: """python${pythonVersion} -m venv venv
                                   . ./venv/bin/activate
                                   python -m pip install --upgrade pip uv
                                   UV_INDEX_STRATEGY=unsafe-best-match uv pip install -r requirements/requirements_tox.txt tox-uv
                                   UV_INDEX_STRATEGY=unsafe-best-match tox --installpkg ${it.path} -e py${pythonVersion.replace('.', '')}-PySide6"""
                                )
                            }

                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                            [pattern: '.tox/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
                macTests["Mac - ${processorArchitecture} - Python ${pythonVersion}: sdist"] = {
                    testPythonPkg(
                        agent: [
                            label: "mac && python${pythonVersion} && ${processorArchitecture}",
                        ],
                        retries: 3,
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                            findFiles(glob: 'dist/*.tar.gz').each{
                                sh(label: 'Running Tox',
                                   script: """python${pythonVersion} -m venv venv
                                              . ./venv/bin/activate
                                              python -m pip install --upgrade pip uv
                                              UV_INDEX_STRATEGY=unsafe-best-match uv pip install -r requirements/requirements_tox.txt tox-uv
                                              UV_INDEX_STRATEGY=unsafe-best-match tox --installpkg ${it.path} -e py${pythonVersion.replace('.', '')}-PySide6"""
                                )
                            }

                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                            [pattern: '.tox/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
            }
        }
        parallel(linuxTests + windowsTests + macTests)
    }
}
def buildPackages(){
    timeout(5){
        withEnv(['PIP_NO_CACHE_DIR=off']) {
            sh(label: 'Building Python Package',
               script: '''python -m venv venv --upgrade-deps
                          venv/bin/pip install build
                          venv/bin/python -m build .
                          '''
               )
       }
    }
}

def testChocolateyPackage(){
    stage('Install'){
        unstash 'CHOCOLATEY_PACKAGE'
        testSpeedwagonChocolateyPkg(props.version)
    }
    stage('Reinstall/Upgrade'){
        testReinstallSpeedwagonChocolateyPkg(props.version)
    }
    stage('Uninstall'){
        bat 'choco uninstall speedwagon --confirm'
    }
}

def buildSphinx(){
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

startup()

def get_props(){
    stage('Reading Package Metadata'){
        node('docker') {
            checkout scm
            docker.image('python').inside {
                def packageMetadata = readJSON(
                    text: {
                        if (isUnix()){
                            return sh(returnStdout: true, script: 'python -c \'import tomllib;print(tomllib.load(open("pyproject.toml", "rb"))["project"])\'').trim()    
                        } else {
                            return bat(returnStdout: true, script: '@python -c "import tomllib;print(tomllib.load(open(\'pyproject.toml\', \'rb\'))[\'project\'])').trim()
                        }
                        

                    }()
                    )
                echo """Metadata:

    Name      ${packageMetadata.name}
    Version   ${packageMetadata.version}
    """
                return packageMetadata
            }
        }
    }
}
def hasSonarCreds(credentialsId){
    try{
        withCredentials([string(credentialsId: credentialsId, variable: 'dddd')]) {
            echo 'Found credentials for sonarqube'
        }
    } catch(e){
        return false
    }
    return true
}
props = get_props()
pipeline {
    agent none
    parameters {
        booleanParam(name: 'RUN_CHECKS', defaultValue: true, description: 'Run checks on code')
        booleanParam(name: 'USE_SONARQUBE', defaultValue: true, description: 'Send data test data to SonarQube')
        credentials(name: 'SONARCLOUD_TOKEN', credentialType: 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl', defaultValue: 'sonarcloud_token', required: false)
        booleanParam(name: 'TEST_RUN_TOX', defaultValue: false, description: 'Run Tox Tests')
        booleanParam(name: 'BUILD_PACKAGES', defaultValue: false, description: 'Build Packages')
        booleanParam(name: 'TEST_STANDALONE_PACKAGE_DEPLOYMENT', defaultValue: true, description: 'Test deploying any packages that are designed to be installed without using Python directly')
        booleanParam(name: 'BUILD_CHOCOLATEY_PACKAGE', defaultValue: false, description: 'Build package for chocolatey package manager')
        booleanParam(name: 'INCLUDE_LINUX_ARM', defaultValue: false, description: 'Include ARM architecture for Linux')
        booleanParam(name: 'INCLUDE_LINUX_X86_64', defaultValue: true, description: 'Include x86_64 architecture for Linux')
        booleanParam(name: 'INCLUDE_MACOS_ARM', defaultValue: false, description: 'Include ARM(m1) architecture for Mac')
        booleanParam(name: 'INCLUDE_MACOS_X86_64', defaultValue: false, description: 'Include x86_64 architecture for Mac')
        booleanParam(name: 'INCLUDE_WINDOWS_X86_64', defaultValue: true, description: 'Include x86_64 architecture for Windows')
        booleanParam(name: 'TEST_PACKAGES', defaultValue: true, description: 'Test Python packages by installing them and running tests on the installed package')
        booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG', defaultValue: false, description: 'Create a Apple Application Bundle DMG')
        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_MSI', defaultValue: false, description: 'Create a standalone wix based .msi installer')
        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_NSIS', defaultValue: false, description: 'Create a standalone NULLSOFT NSIS based .exe installer')
        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_ZIP', defaultValue: false, description: 'Create a standalone portable package')
        booleanParam(name: 'DEPLOY_PYPI', defaultValue: false, description: 'Deploy to pypi')
        booleanParam(name: 'DEPLOY_CHOCOLATEY', defaultValue: false, description: 'Deploy to Chocolatey repository')
        booleanParam(name: 'DEPLOY_STANDALONE_PACKAGERS', defaultValue: false, description: 'Deploy standalone packages')
        booleanParam(name: 'DEPLOY_DOCS', defaultValue: false, description: 'Update online documentation')
    }
    stages {
        stage('Build Sphinx Documentation'){
            agent {
                dockerfile {
                    filename 'ci/docker/python/linux/jenkins/Dockerfile'
                    label 'linux && docker && x86'
                    additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                  }
            }
            options {
                retry(conditions: [agent()], count: 2)
            }
            steps {
                catchError(buildResult: 'UNSTABLE', message: 'Sphinx has warnings', stageResult: 'UNSTABLE') {
                    buildSphinx()
                }
            }
            post{
                always{
                    recordIssues(tools: [sphinxBuild(pattern: 'logs/build_sphinx_html.log')])
                }
                success{
                    stash includes: 'dist/docs/*.pdf', name: 'SPEEDWAGON_DOC_PDF'
                    zip archive: true, dir: 'build/docs/html', glob: '', zipFile: "dist/${props.name}-${props.version}.doc.zip"
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
                        ]
                    )
                }
            }
        }
        stage('Checks'){
            stages{
                stage('Code Quality'){
                    when{
                        equals expected: true, actual: params.RUN_CHECKS
                        beforeAgent true
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/python/linux/jenkins/Dockerfile'
                            label 'linux && docker && x86'
                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                            args '--mount source=sonar-cache-speedwagon,target=/opt/sonar/.sonar/cache'
                          }
                    }
                    options {
                        retry(conditions: [agent()], count: 2)
                    }
                    stages{
                        stage('Test') {
                            stages{
                                stage('Run Tests'){
                                    parallel {
                                        stage('Run PyTest Unit Tests'){
                                            steps{
                                                catchError(buildResult: 'UNSTABLE', message: 'Did not pass all pytest tests', stageResult: 'UNSTABLE') {
                                                    sh(
                                                        script: 'PYTHONFAULTHANDLER=1 coverage run --parallel-mode --source=speedwagon -m pytest --junitxml=./reports/tests/pytest/pytest-junit.xml --capture=no'
                                                    )
                                                }
                                            }
                                            post {
                                                always {
                                                    junit(allowEmptyResults: true, testResults: 'reports/tests/pytest/pytest-junit.xml')
                                                    stash(allowEmpty: true, includes: 'reports/tests/pytest/*.xml', name: 'PYTEST_UNIT_TEST_RESULTS')
                                                }
                                            }
                                        }
                                        stage('Task Scanner'){
                                            steps{
                                                recordIssues(tools: [taskScanner(highTags: 'FIXME', includePattern: 'speedwagon/**/*.py', normalTags: 'TODO')])
                                            }
                                        }
                                        stage('Audit Requirement Freeze File'){
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'pip-audit found issues', stageResult: 'UNSTABLE') {
                                                    sh 'pip-audit -r requirements/requirements-gui-freeze.txt --cache-dir=/tmp/pip-audit-cache'
                                                }
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
                                                catchError(buildResult: 'SUCCESS', message: 'MyPy found issues', stageResult: 'UNSTABLE') {
                                                    tee('logs/mypy.log'){
                                                        sh(label: 'Running MyPy',
                                                           script: 'mypy -p speedwagon --html-report reports/mypy/html'
                                                        )
                                                    }
                                                }
                                            }
                                            post {
                                                always {
                                                    recordIssues(tools: [myPy(pattern: 'logs/mypy.log')])
                                                    publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/mypy/html/', reportFiles: 'index.html', reportName: 'MyPy HTML Report', reportTitles: ''])
                                                }
                                            }
                                        }
                                        stage('Run Ruff Static Analysis') {
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'Ruff found issues', stageResult: 'UNSTABLE') {
                                                    sh( label: 'Running Ruff', script: 'mkdir -p reports && ruff check --config=pyproject.toml -o reports/ruffoutput.json --output-format json')
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
                                                catchError(buildResult: 'SUCCESS', message: 'Flake8 found issues', stageResult: 'UNSTABLE') {
                                                    sh script: 'flake8 speedwagon -j 1 --tee --output-file=logs/flake8.log'
                                                }
                                            }
                                            post {
                                                always {
                                                      stash includes: 'logs/flake8.log', name: 'FLAKE8_REPORT'
                                                      recordIssues(tools: [flake8(pattern: 'logs/flake8.log')])
                                                }
                                            }
                                        }
                                        stage('pyDocStyle'){
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'Did not pass all pyDocStyle tests', stageResult: 'UNSTABLE') {
                                                    sh(
                                                        label: 'Run pydocstyle',
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
                                            recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']])
                                        }
                                    }
                                }
                            }

                        }
                        stage('Run Sonarqube Analysis'){
                            options{
                                lock('speedwagon-sonarscanner')
                            }
                            when{
                                allOf{
                                    equals expected: true, actual: params.USE_SONARQUBE
                                    expression{
                                        return hasSonarCreds(params.SONARCLOUD_TOKEN)
                                    }
                                }
                            }
                            steps{
                                script{
                                    def sonarqube = load('ci/jenkins/scripts/sonarqube.groovy')
                                    def sonarqubeConfig = [
                                                installationName: 'sonarcloud',
                                                credentialsId: params.SONARCLOUD_TOKEN,
                                            ]
                                    milestone label: 'sonarcloud'
                                    if (env.CHANGE_ID){
                                        sonarqube.submitToSonarcloud(
                                            artifactStash: 'sonarqube artifacts',
                                            sonarqube: sonarqubeConfig,
                                            pullRequest: [
                                                source: env.CHANGE_ID,
                                                destination: env.BRANCH_NAME,
                                            ],
                                            package: [
                                                version: props.version,
                                                name: props.name
                                            ],
                                        )
                                    } else {
                                        sonarqube.submitToSonarcloud(
                                            artifactStash: 'sonarqube artifacts',
                                            sonarqube: sonarqubeConfig,
                                            package: [
                                                version: props.version,
                                                name: props.name
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
                    post{
                        cleanup{
                            cleanWs(patterns: [
                                    [pattern: 'logs/*', type: 'INCLUDE'],
                                    [pattern: 'reports/', type: 'INCLUDE'],
                                    [pattern: '.coverage', type: 'INCLUDE']
                                ])
                        }
                        failure{
                            sh 'pip list'
                        }
                    }
                }
                stage('Run Tox'){
                    when{
                        equals expected: true, actual: params.TEST_RUN_TOX
                    }
                    parallel{
                        stage('Linux'){
                            when{
                                expression {return nodesByLabel('linux && docker && x86').size() > 0}
                            }
                            steps{
                                script{
                                    parallel(
                                        getToxTestsParallel(
                                            envNamePrefix: 'Tox Linux',
                                            label: 'linux && docker && x86',
                                            dockerfile: 'ci/docker/python/linux/tox/Dockerfile',
                                            dockerArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg PIP_DOWNLOAD_CACHE=/.cache/pip --build-arg UV_EXTRA_INDEX_URL --build-arg UV_CACHE_DIR=/.cache/uv',
                                            dockerRunArgs: '-v pipcache_speedwagon:/.cache/pip -v uvcache_speedwagon:/.cache/uv',
                                            retry: 2
                                        )
                                    )
                                }
                            }
                        }
                        stage('Windows'){
                            when{
                                expression {return nodesByLabel('windows && docker && x86').size() > 0}
                            }
                            steps{
                                script{
                                    parallel(
                                        getToxTestsParallel(
                                                envNamePrefix: 'Tox Windows',
                                                label: 'windows && docker && x86',
                                                dockerfile: 'ci/docker/python/windows/tox/Dockerfile',
                                                dockerArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE',
                                                retry: 2
                                         )
                                    )
                                }
                            }
                        }
                    }
//                    steps {
//                        runTox()
//                    }
                }
            }
        }
        stage('Packaging'){
            when{
                anyOf{
                    equals expected: true, actual: params.BUILD_PACKAGES
                    equals expected: true, actual: params.BUILD_CHOCOLATEY_PACKAGE
                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                    equals expected: true, actual: params.DEPLOY_STANDALONE_PACKAGES
                    equals expected: true, actual: params.DEPLOY_CHOCOLATEY
                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                }
                beforeAgent true
            }
            stages{
                stage('Python Packages'){
                    stages{
                        stage('Packaging sdist and wheel'){
                            agent {
                                docker{
                                    image 'python'
                                    label 'linux && docker'
                                }
                            }
                            steps{
                                buildPackages()
                            }
                            post{
                                always{
                                    stash includes: 'dist/*.whl,dist/*.tar.gz,dist/*.zip', name: 'PYTHON_PACKAGES'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
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
                            }
                        }
                    }
                }
                stage('End-user packages'){
                    parallel{
                        stage('Mac Application Bundle x86_64'){
                            agent{
                                label 'mac && python3 && x86_64'
                            }
                            when{
                                allOf{
                                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                    expression {return nodesByLabel('mac && x86_64 && python3').size() > 0}
                                }
                                beforeInput true
                            }
                            steps{
                                script{
                                    macAppleBundle()
                                }
                            }
                            post{
                                success{
                                    archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                    stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_BUNDLE_X86_64'
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
                        stage('Mac Application Bundle M1'){
                            agent{
                                label 'mac && python3 && arm64'
                            }
                            when{
                                allOf{
                                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                    expression {return nodesByLabel('mac && arm64 && python3').size() > 0}
                                }
                                beforeInput true
                            }
                            steps{
                                script{
                                    macAppleBundle()
                                }
                            }
                            post{
                                success{
                                    archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                    stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_BUNDLE_M1'
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
                                stage('Building Python Vendored Wheels'){
                                    agent {
                                        dockerfile {
                                            filename 'ci/docker/python/windows/tox/Dockerfile'
                                            label 'windows && docker && x86'
                                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg UV_EXTRA_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv'
                                            args '-v pipcache_speedwagon:c:/users/containeradministrator/appdata/local/pip -v uvcache_speedwagon:c:/users/containeradministrator/appdata/local/uv'
                                          }
                                    }
                                    steps{
                                        withEnv(['PY_PYTHON=3.11']) {
                                            bat(
                                                label: 'Getting dependencies to vendor',
                                                script: '''
                                                    py -m pip install pip --upgrade
                                                    py -m pip install wheel
                                                    py -m pip wheel -r requirements-vendor.txt --no-deps -w .\\deps\\ -i %PIP_EXTRA_INDEX_URL%
                                                '''
                                            )
                                        }
                                        stash includes: 'deps/*.whl', name: 'VENDORED_WHEELS_FOR_CHOCOLATEY'
                                    }
                                }
                                stage('Package for Chocolatey'){
                                    agent {
                                        dockerfile {
                                            filename 'ci/docker/chocolatey_package/Dockerfile'
                                            label 'windows && docker && x86'
                                            additionalBuildArgs '--build-arg CHOCOLATEY_SOURCE'
                                          }
                                    }
                                    steps{
                                        checkout scm
                                        unstash 'PYTHON_PACKAGES'
                                        unstash 'VENDORED_WHEELS_FOR_CHOCOLATEY'
                                        script {
                                            findFiles(glob: 'dist/*.whl').each{
                                                unstash 'SPEEDWAGON_DOC_PDF'
                                                powershell(script: 'New-Item -Name "deps" -ItemType "directory"')
                                                powershell(
                                                    label: 'Creating new Chocolatey package',
                                                    script: """ci/jenkins/scripts/make_chocolatey.ps1 `
                                                                -PackageName speedwagon `
                                                                -PackageSummary \"${props.description}\" `
                                                                -PackageVersion ${props.version} `
                                                                -PackageMaintainer \"${props.maintainers[0].name}\" `
                                                                -Wheel ${it.path} `
                                                                -DependenciesDir '.\\deps' `
                                                                -Requirements '.\\requirements\\requirements-gui-freeze.txt' `
                                                                -DocsDir '.\\dist\\docs'
                                                            """
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
                                            label 'windows && docker && x86'
                                            additionalBuildArgs '--build-arg CHOCOLATEY_SOURCE'
                                          }
                                    }
                                    when{
                                        equals expected: true, actual: params.TEST_STANDALONE_PACKAGE_DEPLOYMENT
                                        beforeAgent true
                                    }
                                    options {
                                        timeout(time: 2, unit: 'HOURS')
                                    }
                                    steps{
                                        testChocolateyPackage()
                                    }
                                    post{
                                        failure{
                                            powershell(
                                                label: 'Gathering Chocolatey logs',
                                                script: '''
                                                        $Path = "${Env:WORKSPACE}\\logs\\chocolatey"
                                                        If(!(test-path -PathType container $Path))
                                                        {
                                                              New-Item -ItemType Directory -Path $Path
                                                        }
                                                        Copy-Item -Path C:\\ProgramData\\chocolatey\\logs -Destination $Path -Recurse
                                                        '''
                                                )
                                            archiveArtifacts( artifacts: 'logs/**')
                                        }
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
                                            label 'Windows && Docker && x86'
                                            args '-u ContainerAdministrator'
                                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE'
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
                                                    vendoredPythonRequirementsFile: 'requirements/requirements-gui-freeze.txt',
                                                    buildDir: 'build\\cmake_build',
                                                    venvPath: "${WORKSPACE}\\build\\standalone_venv",
                                                    package: [
                                                        version: props.version
                                                    ],
                                                    testing:[
                                                        ctestLogsFilePath: "${WORKSPACE}\\logs\\ctest.log"
                                                    ]
                                                )
                                            }
                                        }
                                        stash includes: 'dist/*.msi,dist/*.exe,dist/*.zip', name: 'STANDALONE_INSTALLERS'
                                    }
                                    post {
                                        success{
                                            archiveArtifacts artifacts: 'dist/*.msi,dist/*.exe,dist/*.zip', fingerprint: true
                                        }
                                        failure {
                                            archiveArtifacts allowEmptyArchive: true, artifacts: 'dist/**/wix.log,dist/**/*.wxs'
                                            archiveArtifacts allowEmptyArchive: true, artifacts: 'logs/**'
                                        }
                                        cleanup{
                                            cleanWs(
                                                patterns: [
                                                        [pattern: '*.egg-info/**', type: 'INCLUDE'],
                                                        [pattern: '.pytest_cache/**', type: 'INCLUDE'],
                                                        [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                                        [pattern: 'build/**', type: 'INCLUDE'],
                                                        [pattern: 'temp/**', type: 'INCLUDE'],
                                                        [pattern: 'dist/**', type: 'INCLUDE'],
                                                        [pattern: 'logs/**', type: 'INCLUDE'],
                                                    ],
                                                notFailBuild: true,
                                                deleteDirs: true
                                            )
                                        }
                                    }
                                }
                                stage('Testing MSI Install'){
                                    agent {
                                        docker {
                                            args '-u ContainerAdministrator'
                                            image 'mcr.microsoft.com/windows/servercore:ltsc2019'
                                            label 'Windows && Docker && x86'
                                        }
                                    }
                                    when{
                                        allOf{
                                            equals expected: true, actual: params.TEST_STANDALONE_PACKAGE_DEPLOYMENT
                                            equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                        }
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
                                choices: getPypiConfig(),
                                description: 'Url to the pypi index to upload python packages.',
                                name: 'SERVER_URL'
                            )
                        }
                    }
                    steps{
                        unstash 'PYTHON_PACKAGES'
                        pypiUpload(
                            credentialsId: 'jenkins-nexus',
                            repositoryUrl: SERVER_URL,
                            glob: 'dist/*'
                        )
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
                            label 'windows && docker && x86'
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
                                choices: getChocolateyServers(),
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
                stage('Deploy Standalone'){
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_STANDALONE_PACKAGERS
                            anyOf{
                                equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                                equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                            }
                        }
                        beforeAgent true
                        beforeInput true

                    }
                    agent any
                    input {
                        message 'Upload to Nexus server?'
                        parameters {
                            credentials credentialType: 'com.cloudbees.plugins.credentials.common.StandardCredentials', defaultValue: 'jenkins-nexus', name: 'NEXUS_CREDS', required: true
                            choice(
                                choices: getStandAloneStorageServers(),
                                description: 'Url to upload artifact.',
                                name: 'SERVER_URL'
                            )
                            string defaultValue: "speedwagon/${props.version}", description: 'subdirectory to store artifact', name: 'archiveFolder'
                        }
                    }
                    options {
                        skipDefaultCheckout(true)
                    }
                    stages{
                        stage('Include Mac Bundle Installer for Deployment'){
                            when{
                                equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                            }
                            steps {
                                unstash 'APPLE_APPLICATION_BUNDLE_X86_64'
                                unstash 'APPLE_APPLICATION_BUNDLE_M1'
                            }
                        }
                        stage('Include Windows Installer(s) for Deployment'){
                            when{
                                anyOf{
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_MSI
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_NSIS
                                    equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE_ZIP
                                }
                            }
                            steps {
                                unstash 'STANDALONE_INSTALLERS'
                            }
                        }
                        stage('Include PDF Documentation for Deployment'){
                            steps {
                                unstash 'SPEEDWAGON_DOC_PDF'
                            }
                        }
                        stage('Deploy'){
                            steps {
                                deployStandalone('dist/*.msi,dist/*.exe,dist/*.zip,dist/*.tar.gz,dist/docs/*.pdf,dist/*.dmg', "${SERVER_URL}/${archiveFolder}")
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
                    }
                }
            }
        }
    }
}
