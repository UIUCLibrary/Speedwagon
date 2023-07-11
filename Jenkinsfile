
SUPPORTED_MAC_VERSIONS = ['3.8', '3.9', '3.10', '3.11']
SUPPORTED_LINUX_VERSIONS = ['3.8', '3.9', '3.10', '3.11']
SUPPORTED_WINDOWS_VERSIONS = ['3.8', '3.9', '3.10', '3.11']
DOCKER_PLATFORM_BUILD_ARGS = [
    linux: '',
    windows: '--build-arg CHOCOLATEY_SOURCE'
]

def getPypiConfig() {
    node(){
        configFileProvider([configFile(fileId: 'pypi_config', variable: 'CONFIG_FILE')]) {
            def config = readJSON( file: CONFIG_FILE)
            return config['deployment']['indexes']
        }
    }
}
def getChocolateyServers() {
        node(){
            configFileProvider([configFile(fileId: 'deploymentStorageConfig', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['chocolatey']['sources']
            }
        }
}

def getStandAloneStorageServers(){
    node(){
        configFileProvider([configFile(fileId: 'deploymentStorageConfig', variable: 'CONFIG_FILE')]) {
            def config = readJSON( file: CONFIG_FILE)
            return config['publicReleases']['urls']
        }
    }
}


def getDevpiConfig() {
    node(){
        configFileProvider([configFile(fileId: 'devpi_config', variable: 'CONFIG_FILE')]) {
            def configProperties = readProperties(file: CONFIG_FILE)
            configProperties.stagingIndex = {
                if (env.TAG_NAME?.trim()){
                    return 'tag_staging'
                } else{
                    return "${env.BRANCH_NAME}_staging"
                }
            }()
            return configProperties
        }
    }
}
def DEVPI_CONFIG = getDevpiConfig()

def deployStandalone(glob, url) {
    script{
        findFiles(glob: glob).each{
            try{
                def put_response = httpRequest authentication: NEXUS_CREDS, httpMode: 'PUT', uploadFile: it.path, url: "${url}/${it.name}", wrapAsMultipart: false
            } catch(Exception e){
                echo "http request response: ${put_response.content}"
                throw e;
            }
        }
    //                                    deploy_artifacts_to_url('dist/*.msi,dist/*.exe,dist/*.zip,dist/*.tar.gz,dist/docs/*.pdf,dist/docs/*.dng', "https://jenkins.library.illinois.edu/nexus/repository/prescon-beta/speedwagon/${props.Version}/")
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
        unstash 'DIST-INFO'
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

def runTox(){
    script{
        def tox = fileLoader.fromGit(
            'tox',
            'https://github.com/UIUCLibrary/jenkins_helper_scripts.git',
            '8',
            null,
            ''
        )
        def windowsJobs = [:]
        def linuxJobs = [:]
        stage('Scanning Tox Environments'){
            parallel(
                'Linux':{
                    linuxJobs = tox.getToxTestsParallel(
                            envNamePrefix: 'Tox Linux',
                            label: 'linux && docker && x86',
                            dockerfile: 'ci/docker/python/linux/tox/Dockerfile',
                            dockerArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL',
                            dockerRunArgs: '-v pipcache_speedwagon:/.cache/pip',
                            retry: 2
                        )
                },
                'Windows':{
                    windowsJobs = tox.getToxTestsParallel(
                            envNamePrefix: 'Tox Windows',
                            label: 'windows && docker && x86',
                            dockerfile: 'ci/docker/python/windows/tox/Dockerfile',
                            dockerArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE',
                            dockerRunArgs: '-v pipcache_speedwagon:c:/users/containeradministrator/appdata/local/pip',
                            retry: 2
                     )
                },
                failFast: true
            )
        }
        parallel(windowsJobs + linuxJobs)
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

def getMacDevpiTestStages(packageName, packageVersion, pythonVersions, devpiServer, devpiCredentialsId, devpiIndex) {
    node(){
        checkout scm
        devpi = load('ci/jenkins/scripts/devpi.groovy')
    }
    def macPackageStages = [:]
    pythonVersions.each{pythonVersion ->
        def macArchitectures = []
        if(params.INCLUDE_MACOS_X86_64 == true){
            macArchitectures.add('x86_64')
        }
        if(params.INCLUDE_MACOS_ARM == true){
            macArchitectures.add('m1')
        }
        macArchitectures.each{ processorArchitecture ->
            macPackageStages["Test Python ${pythonVersion}: wheel Mac ${processorArchitecture}"] = {
                withEnv([
                    'QT_QPA_PLATFORM=offscreen',
                    'PATH+EXTRA=./venv/bin'
                    ]) {
                    devpi.testDevpiPackage(
                        agent: [
                            label: "mac && python${pythonVersion} && ${processorArchitecture} && devpi-access"
                        ],
                        devpi: [
                            index: devpiIndex,
                            server: devpiServer,
                            credentialsId: devpiCredentialsId,
                            devpiExec: 'venv/bin/devpi'
                        ],
                        package:[
                            name: packageName,
                            version: packageVersion,
                            selector: 'whl'
                        ],
                        test:[
                            setup: {
                                checkout scm
                                sh(
                                    label:'Installing Devpi client',
                                    script: '''python3 -m venv venv
                                                venv/bin/python -m pip install pip --upgrade
                                                venv/bin/python -m pip install devpi_client -r requirements/requirements_tox.txt
                                                '''
                                )
                            },
                            toxEnv: "py${pythonVersion}".replace('.',''),
                            teardown: {
                                sh( label: 'Remove Devpi client', script: 'rm -r venv')
                            }
                        ],
                        retries: 3
                    )
                }
            }
            macPackageStages["Test Python ${pythonVersion}: sdist Mac ${processorArchitecture}"] = {
                withEnv([
                    'QT_QPA_PLATFORM=offscreen',
                    'PATH+EXTRA=./venv/bin'
                    ]) {
                    devpi.testDevpiPackage(
                        agent: [
                            label: "mac && python${pythonVersion} && ${processorArchitecture} && devpi-access"
                        ],
                        devpi: [
                            index: devpiIndex,
                            server: devpiServer,
                            credentialsId: devpiCredentialsId,
                            devpiExec: 'venv/bin/devpi'
                        ],
                        package:[
                            name: packageName,
                            version: packageVersion,
                            selector: 'whl'
                        ],
                        test:[
                            setup: {
                                checkout scm
                                sh(
                                    label:'Installing Devpi client',
                                    script: '''python3 -m venv venv
                                                venv/bin/python -m pip install pip --upgrade
                                                venv/bin/python -m pip install devpi_client -r requirements/requirements_tox.txt
                                                '''
                                )
                            },
                            toxEnv: "py${pythonVersion}".replace('.',''),
                            teardown: {
                                sh( label: 'Remove Devpi client', script: 'rm -r venv')
                            }
                        ],
                        retries: 3
                    )
                }
            }
        }
    }
    return macPackageStages;
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


def testPythonPackages(){
    script{
        def packages
        node(){
            checkout scm
            packages = load 'ci/jenkins/scripts/packaging.groovy'
        }
        def windowsTests = [:]
        SUPPORTED_WINDOWS_VERSIONS.each{ pythonVersion ->
            if(params.INCLUDE_WINDOWS_X86_64 == true){
                windowsTests["Windows - Python ${pythonVersion}-x86: sdist"] = {
                    packages.testPkg2(
                        agent: [
                            dockerfile: [
                                label: 'windows && docker && x86',
                                filename: 'ci/docker/python/windows/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE',
                                args: '-v pipcache_speedwagon:c:/users/containeradministrator/appdata/local/pip'
                            ]
                        ],
                        glob: 'dist/*.tar.gz,dist/*.zip',
                        stash: 'PYTHON_PACKAGES',
                        toxEnv: "py${pythonVersion.replace('.', '')}-PySide6",
                        retry: 3,
                    )
                }
                windowsTests["Windows - Python ${pythonVersion}-x86: wheel"] = {
                    packages.testPkg2(
                        agent: [
                            dockerfile: [
                                label: 'windows && docker && x86',
                                filename: 'ci/docker/python/windows/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE',
                                args: '-v pipcache_speedwagon:c:/users/containeradministrator/appdata/local/pip'
                            ]
                        ],
                        glob: 'dist/*.whl',
                        stash: 'PYTHON_PACKAGES',
                        toxEnv: "py${pythonVersion.replace('.', '')}-PySide6",
                        retry: 3,
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
            architectures.each{ processorArchitecture ->
                linuxTests["Linux-${processorArchitecture} - Python ${pythonVersion}: sdist"] = {
                    packages.testPkg2(
                        agent: [
                            dockerfile: [
                                label: "linux && docker && ${processorArchitecture}",
                                filename: 'ci/docker/python/linux/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL',
                                args: '-v pipcache_speedwagon:/.cache/pip'
                            ]
                        ],
                        glob: 'dist/*.tar.gz',
                        stash: 'PYTHON_PACKAGES',
                        toxEnv: processorArchitecture=='arm' ? "py${pythonVersion.replace('.', '')}" : "py${pythonVersion.replace('.', '')}-PySide6",
                        retry: 3,
                    )
                }
                linuxTests["Linux-${processorArchitecture} - Python ${pythonVersion}: wheel"] = {
                    packages.testPkg2(
                        agent: [
                            dockerfile: [
                                label: "linux && docker && ${processorArchitecture}",
                                filename: 'ci/docker/python/linux/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL',
                                args: '-v pipcache_speedwagon:/.cache/pip'
                            ]
                        ],
                        glob: 'dist/*.whl',
                        stash: 'PYTHON_PACKAGES',
                        toxEnv: processorArchitecture=='arm' ? "py${pythonVersion.replace('.', '')}" : "py${pythonVersion.replace('.', '')}-PySide6",
                        retry: 3,
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
                    withEnv(['QT_QPA_PLATFORM=offscreen']) {
                        packages.testPkg2(
                            agent: [
                                label: "mac && python${pythonVersion} && ${processorArchitecture}",
                            ],
                            glob: 'dist/*.tar.gz,dist/*.zip',
                            stash: 'PYTHON_PACKAGES',
                            toxEnv: "py${pythonVersion.replace('.', '')}-PySide6",
                            toxExec: 'venv/bin/tox',
                            testSetup: {
                                checkout scm
                                unstash 'PYTHON_PACKAGES'
                                sh(
                                    label:'Install Tox',
                                    script: '''python3 -m venv venv
                                               venv/bin/pip install pip --upgrade
                                               venv/bin/pip install -r requirements/requirements_tox.txt
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
                macTests["Mac - ${processorArchitecture} - Python ${pythonVersion}: sdist"] = {
                    withEnv(['QT_QPA_PLATFORM=offscreen']) {
                        packages.testPkg2(
                            agent: [
                                label: "mac && python${pythonVersion} && ${processorArchitecture}",
                            ],
                            glob: 'dist/*.tar.gz,dist/*.zip',
                            stash: 'PYTHON_PACKAGES',
                            toxEnv: "py${pythonVersion.replace('.', '')}-PySide6",
                            toxExec: 'venv/bin/tox',
                            testSetup: {
                                checkout scm
                                unstash 'PYTHON_PACKAGES'
                                sh(
                                    label:'Install Tox',
                                    script: '''python3 -m venv venv
                                               venv/bin/pip install pip --upgrade
                                               venv/bin/pip install -r requirements/requirements_tox.txt
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
        }
        parallel(linuxTests + windowsTests + macTests)
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
        node() {
            try{
                unstash 'DIST-INFO'
                def metadataFile = findFiles(excludes: '', glob: '*.dist-info/METADATA')[0]
                def package_metadata = readProperties interpolate: true, file: metadataFile.path
                echo """Metadata:

    Name      ${package_metadata.Name}
    Version   ${package_metadata.Version}
    """
                return package_metadata
            } finally {
                cleanWs(
                    patterns: [
                            [pattern: '*.dist-info/**', type: 'INCLUDE'],
                        ],
                    notFailBuild: true,
                    deleteDirs: true
                )
            }
        }
    }
}

props = get_props()
pipeline {
    agent none
    parameters {
        booleanParam(name: 'USE_SONARQUBE', defaultValue: true, description: 'Send data test data to SonarQube')
        booleanParam(name: 'RUN_CHECKS', defaultValue: true, description: 'Run checks on code')
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
        booleanParam(name: 'DEPLOY_DEVPI', defaultValue: false, description: "Deploy to DevPi on ${DEVPI_CONFIG.server}/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: 'DEPLOY_DEVPI_PRODUCTION', defaultValue: false, description: "Deploy to ${DEVPI_CONFIG.server}/production/release")
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
                                            publishCoverage(
                                                adapters: [
                                                    coberturaAdapter('reports/coverage.xml')
                                                ],
                                                calculateDiffForChangeRequests: true,
                                                sourceFileResolver: sourceFiles('STORE_ALL_BUILD')
                                            )
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
                                equals expected: true, actual: params.USE_SONARQUBE
                                beforeAgent true
                                beforeOptions true
                            }
                            steps{
                                script{
                                    def sonarqube = load('ci/jenkins/scripts/sonarqube.groovy')
                                    def sonarqubeConfig = [
                                                installationName: 'sonarcloud',
                                                credentialsId: 'sonarcloud_token',
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
                                                version: props.Version,
                                                name: props.Name
                                            ],
                                        )
                                    } else {
                                        sonarqube.submitToSonarcloud(
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
                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                    equals expected: true, actual: params.DEPLOY_STANDALONE_PACKAGES
                    equals expected: true, actual: params.DEPLOY_DEVPI
                    equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION
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
                                label 'mac && python3 && x86'
                            }
                            when{
                                equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
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
                                label 'mac && python3 && m1'
                            }
                            when{
                                anyOf{
                                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
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
                                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE'
                                          }
                                    }
                                    steps{
                                        withEnv(['PY_PYTHON=3.11']) {
                                            bat(
                                                label: 'Getting dependencies to vendor',
                                                script: '''
                                                    py -m pip install pip --upgrade
                                                    py -m pip install wheel
                                                    py -m pip wheel -r requirements-vendor.txt --no-deps -w .\\deps\\ -i https://jenkins.library.illinois.edu/nexus/repository/uiuc_prescon_python/simple
                                                '''
                                            )
                                        }
                                    }
                                    post{
                                        success{
                                            stash includes: 'deps/*.whl', name: 'VENDORED_WHEELS_FOR_CHOCOLATEY'
                                        }
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
                                                powershell(
                                                    label: 'Creating new Chocolatey package',
                                                    script: """ci/jenkins/scripts/make_chocolatey.ps1 `
                                                                -PackageName speedwagon `
                                                                -PackageSummary \"${props.Summary}\" `
                                                                -PackageVersion ${props.Version} `
                                                                -PackageMaintainer \"${props.Maintainer}\" `
                                                                -Wheel ${it.path} `
                                                                -DependenciesDir '.\\deps' `
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
                                    stages{
                                        stage('Install'){
                                            steps{
                                                unstash 'CHOCOLATEY_PACKAGE'
                                                testSpeedwagonChocolateyPkg(props.Version)
                                            }
                                        }
                                        stage('Reinstall/Upgrade'){
                                            steps{
                                                testReinstallSpeedwagonChocolateyPkg(props.Version)
                                            }
                                        }
                                        stage('Uninstall'){
                                            steps{
                                                bat 'choco uninstall speedwagon --confirm'
                                            }
                                        }
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
                                                    buildDir: 'build\\cmake_build',
                                                    venvPath: "${WORKSPACE}\\build\\standalone_venv",
                                                    package: [
                                                        version: props.Version
                                                    ],
                                                    testing:[
                                                        ctestLogsFilePath: "${WORKSPACE}\\logs\\ctest.log"
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
                            label 'linux && docker && devpi-access'
                            additionalBuildArgs ' --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                          }
                    }
                    steps {
                        unstash 'DOCS_ARCHIVE'
                        unstash 'PYTHON_PACKAGES'
                        script{
                            load('ci/jenkins/scripts/devpi.groovy').upload(
                                    server: DEVPI_CONFIG.server,
                                    credentialsId: DEVPI_CONFIG.credentialsId,
                                    index: DEVPI_CONFIG.stagingIndex,
                                    clientDir: './devpi'
                                )
                        }
                    }
                }
                stage('Test DevPi packages') {
                    steps{
                        script{
                            def devpi
                            node(){
                                devpi = load('ci/jenkins/scripts/devpi.groovy')
                            }
                            def macPackages = getMacDevpiTestStages(props.Name, props.Version, SUPPORTED_MAC_VERSIONS, DEVPI_CONFIG.server, DEVPI_CONFIG.credentialsId, DEVPI_CONFIG.stagingIndex)
                            windowsPackages = [:]
                            SUPPORTED_WINDOWS_VERSIONS.each{pythonVersion ->
                                if(params.INCLUDE_WINDOWS_X86_64 == true){
                                    windowsPackages["Test Python ${pythonVersion}: sdist Windows"] = {
                                        devpi.testDevpiPackage(
                                            agent: [
                                                dockerfile: [
                                                    filename: 'ci/docker/python/windows/tox/Dockerfile',
                                                    additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE',
                                                    label: 'windows && docker && x86 && devpi-access'
                                                ]
                                            ],
                                            devpi: [
                                                index: DEVPI_CONFIG.stagingIndex,
                                                server: DEVPI_CONFIG.server,
                                                credentialsId: DEVPI_CONFIG.credentialsId,
                                            ],
                                            package:[
                                                name: props.Name,
                                                version: props.Version,
                                                selector: 'tar.gz'
                                            ],
                                            test:[
                                                toxEnv: "py${pythonVersion}".replace('.',''),
                                            ],
                                            retries: 3
                                        )
                                    }
                                    windowsPackages["Test Python ${pythonVersion}: wheel Windows"] = {
                                        devpi.testDevpiPackage(
                                            agent: [
                                                dockerfile: [
                                                    filename: 'ci/docker/python/windows/tox/Dockerfile',
                                                    additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE',
                                                    label: 'windows && docker && x86 && devpi-access'
                                                ]
                                            ],
                                            devpi: [
                                                index: DEVPI_CONFIG.stagingIndex,
                                                server: DEVPI_CONFIG.server,
                                                credentialsId: DEVPI_CONFIG.credentialsId,
                                            ],
                                            package:[
                                                name: props.Name,
                                                version: props.Version,
                                                selector: 'whl'
                                            ],
                                            test:[
                                                toxEnv: "py${pythonVersion}".replace('.',''),
                                            ],
                                            retries: 3
                                        )
                                    }
                                }
                            }
                            def linuxPackages = [:]
                            SUPPORTED_LINUX_VERSIONS.each{pythonVersion ->
                                if(params.INCLUDE_LINUX_X86_64 == true){
                                    linuxPackages["Test Python ${pythonVersion}: sdist Linux"] = {
                                        devpi.testDevpiPackage(
                                            agent: [
                                                dockerfile: [
                                                    filename: 'ci/docker/python/linux/tox/Dockerfile',
                                                    additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL',
                                                    label: 'linux && docker && x86 && devpi-access',
                                                    args: '-v pipcache_speedwagon:/.cache/pip'
                                                ]
                                            ],
                                            devpi: [
                                                index: DEVPI_CONFIG.stagingIndex,
                                                server: DEVPI_CONFIG.server,
                                                credentialsId: DEVPI_CONFIG.credentialsId,
                                            ],
                                            package:[
                                                name: props.Name,
                                                version: props.Version,
                                                selector: 'tar.gz'
                                            ],
                                            test:[
                                                toxEnv: "py${pythonVersion}".replace('.',''),
                                            ],
                                            retries: 3
                                        )
                                    }
                                    linuxPackages["Test Python ${pythonVersion}: wheel Linux"] = {
                                        devpi.testDevpiPackage(
                                            agent: [
                                                dockerfile: [
                                                    filename: 'ci/docker/python/linux/tox/Dockerfile',
                                                    additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL',
                                                    label: 'linux && docker && x86 && devpi-access',
                                                    args: '-v pipcache_speedwagon:/.cache/pip'
                                                ]
                                            ],
                                            devpi: [
                                                index: DEVPI_CONFIG.stagingIndex,
                                                server: DEVPI_CONFIG.server,
                                                credentialsId: DEVPI_CONFIG.credentialsId,
                                            ],
                                            package:[
                                                name: props.Name,
                                                version: props.Version,
                                                selector: 'whl'
                                            ],
                                            test:[
                                                toxEnv: "py${pythonVersion}".replace('.',''),
                                            ],
                                            retries: 3
                                        )
                                    }
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
                            label 'linux && docker && devpi-access'
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
                                server: DEVPI_CONFIG.server,
                                indexSource: DEVPI_CONFIG.stagingIndex,
                                indexDestination: 'production/release',
                                credentialsId: DEVPI_CONFIG.credentialsId
                            )
                        }
                    }
                }
            }
            post{
                success{
                    node('linux && docker && devpi-access') {
                       script{
                            if (!env.TAG_NAME?.trim()){
                                checkout scm
                                docker.build('speedwagon:devpi','-f ./ci/docker/python/linux/jenkins/Dockerfile --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL .').inside{
                                    load('ci/jenkins/scripts/devpi.groovy').pushPackageToIndex(
                                        pkgName: props.Name,
                                        pkgVersion: props.Version,
                                        server: DEVPI_CONFIG.server,
                                        indexSource: DEVPI_CONFIG.stagingIndex,
                                        indexDestination: "DS_Jenkins/${env.BRANCH_NAME}",
                                        credentialsId: DEVPI_CONFIG.credentialsId,
                                    )
                                }
                           }
                       }
                    }
                }
                cleanup{
                    node('linux && docker && x86 && devpi-access') {
                       script{
                            checkout scm
                            docker.build('speedwagon:devpi','-f ./ci/docker/python/linux/jenkins/Dockerfile --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL .').inside{
                                load('ci/jenkins/scripts/devpi.groovy').removePackage(
                                    pkgName: props.Name,
                                    pkgVersion: props.Version,
                                    index: DEVPI_CONFIG.stagingIndex,
                                    server: DEVPI_CONFIG.server,
                                    credentialsId: DEVPI_CONFIG.credentialsId,

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
                            label 'linux && docker && devpi-access'
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
                            string defaultValue: "speedwagon/${props.Version}", description: 'subdirectory to store artifact', name: 'archiveFolder'
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
