def getVersion(){
    node(){
        checkout scm
        def props = readTOML( file: 'pyproject.toml')['project']
        return props.version
    }
}

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


def run_pylint(){
    def MAX_TIME = 10
    withEnv(['PYLINTHOME=.']) {
        sh '''. ./venv/bin/activate
              pylint --version
           '''
        catchError(buildResult: 'SUCCESS', message: 'Pylint found issues', stageResult: 'UNSTABLE') {
            timeout(MAX_TIME){
                tee('reports/pylint_issues.txt'){
                    sh(
                        label: 'Running pylint',
                        script: '''. ./venv/bin/activate
                                   pylint speedwagon -j 2 -r n --msg-template="{path}:{module}:{line}: [{msg_id}({symbol}), {obj}] {msg}"
                                ''',
                    )
                }
            }
        }
        timeout(MAX_TIME){
            sh(
                label: 'Running pylint for sonarqube',
                script: '''. ./venv/bin/activate
                           pylint speedwagon -j 2 -d duplicate-code --output-format=parseable | tee reports/pylint.txt
                        ''',
                returnStatus: true
            )
        }
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

def installMSVCRuntime(cacheLocation){
    def cachedFile = "${cacheLocation}\\vc_redist.x64.exe".replaceAll(/\\\\+/, '\\\\')
    withEnv(
        [
            "CACHED_FILE=${cachedFile}",
            "RUNTIME_DOWNLOAD_URL=https://aka.ms/vs/17/release/vc_redist.x64.exe"
        ]
    ){
        lock("${cachedFile}-${env.NODE_NAME}"){
            powershell(
                label: 'Ensuring vc_redist runtime installer is available',
                script: '''if ([System.IO.File]::Exists("$Env:CACHED_FILE"))
                           {
                                Write-Host 'Found installer'
                           } else {
                                Write-Host 'No installer found'
                                Write-Host 'Downloading runtime'
                                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;Invoke-WebRequest "$Env:RUNTIME_DOWNLOAD_URL" -OutFile "$Env:CACHED_FILE"
                           }
                        '''
            )
        }
        powershell(label: 'Install VC Runtime', script: 'Start-Process -filepath "$Env:CACHED_FILE" -ArgumentList "/install", "/passive", "/norestart" -Passthru | Wait-Process;')
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
def call(){
    library(
        identifier: 'JenkinsPythonHelperLibrary@2024.12.0',
        retriever: modernSCM(
            [
                $class: 'GitSCMSource',
                remote: 'https://github.com/UIUCLibrary/JenkinsPythonHelperLibrary.git'
            ]
        )
    )
    pipeline {
        agent none
        parameters {
            booleanParam(name: 'RUN_CHECKS', defaultValue: true, description: 'Run checks on code')
            booleanParam(name: 'USE_SONARQUBE', defaultValue: true, description: 'Send data test data to SonarQube')
            credentials(name: 'SONARCLOUD_TOKEN', credentialType: 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl', defaultValue: 'sonarcloud_token', required: false)
            booleanParam(name: 'TEST_RUN_TOX', defaultValue: false, description: 'Run Tox Tests')
            booleanParam(name: 'BUILD_PACKAGES', defaultValue: false, description: 'Build Packages')
            booleanParam(name: 'INCLUDE_LINUX-ARM64', defaultValue: false, description: 'Include ARM architecture for Linux')
            booleanParam(name: 'INCLUDE_LINUX-X86_64', defaultValue: true, description: 'Include x86_64 architecture for Linux')
            booleanParam(name: 'INCLUDE_MACOS-ARM64', defaultValue: false, description: 'Include ARM(m1) architecture for Mac')
            booleanParam(name: 'INCLUDE_MACOS-X86_64', defaultValue: false, description: 'Include x86_64 architecture for Mac')
            booleanParam(name: 'INCLUDE_WINDOWS-X86_64', defaultValue: true, description: 'Include x86_64 architecture for Windows')
            booleanParam(name: 'TEST_PACKAGES', defaultValue: true, description: 'Test Python packages by installing them and running tests on the installed package')
            booleanParam(name: 'DEPLOY_PYPI', defaultValue: false, description: 'Deploy to pypi')
            booleanParam(name: 'DEPLOY_DOCS', defaultValue: false, description: 'Update online documentation')
        }
        stages {
            stage('Build Sphinx Documentation'){
                agent {
                        docker{
                            image 'sphinxdoc/sphinx-latexpdf'
                            label 'linux && docker && x86'
                            args '--mount source=python-tmp-speedwagon,target=/tmp'
                        }
                }
                options {
                    retry(conditions: [agent()], count: 2)
                }
                environment{
                    PIP_CACHE_DIR = '/tmp/pipcache'
                    UV_INDEX_STRATEGY = 'unsafe-best-match'
                    UV_TOOL_DIR = '/tmp/uvtools'
                    UV_PYTHON_INSTALL_DIR = '/tmp/uvpython'
                    UV_CACHE_DIR = '/tmp/uvcache'
                    UV_PYTHON = '3.11'
                }
                steps {
                    catchError(buildResult: 'UNSTABLE', message: 'Sphinx has warnings', stageResult: 'UNSTABLE') {
                        sh(label: 'Build docs in html and Latex formats',
                           script:'''python3 -m venv venv
                              trap "rm -rf venv" EXIT
                              . ./venv/bin/activate
                              pip install --disable-pip-version-check uv
                              uvx --constraint=requirements-dev.txt --from sphinx --with sphinx-argparse --with-editable . sphinx-build -W --keep-going -b html -d build/docs/.doctrees -w logs/build_sphinx_html.log docs/source build/docs/html
                              uvx --constraint=requirements-dev.txt --from sphinx --with sphinx-argparse --with-editable . sphinx-build -W --keep-going -b latex -d build/docs/.doctrees docs/source build/docs/latex
                              ''')
                        sh(label: 'Building PDF docs',
                           script: '''make -C build/docs/latex
                                        mkdir -p dist/docs
                                        mv build/docs/latex/*.pdf dist/docs/
                                        '''
                        )
                    }
                }
                post{
                    always{
                        recordIssues(tools: [sphinxBuild(pattern: 'logs/build_sphinx_html.log')])
                    }
                    success{
                        stash includes: 'dist/docs/*.pdf', name: 'SPEEDWAGON_DOC_PDF'
                        script{
                            def props = readTOML( file: 'pyproject.toml')['project']
                            zip archive: true, dir: 'build/docs/html', glob: '', zipFile: "dist/${props.name}-${props.version}.doc.zip"
                        }
                        stash includes: 'dist/*.doc.zip,build/docs/html/**', name: 'DOCS_ARCHIVE'
                        archiveArtifacts artifacts: 'dist/docs/*.pdf'
                    }
                    cleanup{
                        cleanWs(
                            notFailBuild: true,
                            deleteDirs: true,
                            patterns: [
                                [pattern: 'logs/', type: 'INCLUDE'],
                                [pattern: 'venv/', type: 'INCLUDE'],
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
                                args '--mount source=python-tmp-speedwagon,target=/tmp'
                            }
                        }
                        environment{
                            PIP_CACHE_DIR='/tmp/pipcache'
                            UV_INDEX_STRATEGY='unsafe-best-match'
                            UV_TOOL_DIR='/tmp/uvtools'
                            UV_PYTHON_INSTALL_DIR='/tmp/uvpython'
                            UV_CACHE_DIR='/tmp/uvcache'
                            UV_PYTHON='3.11'
                            QT_QPA_PLATFORM='offscreen'
                        }
                        options {
                            retry(conditions: [agent()], count: 2)
                        }
                        stages{
                            stage('Test') {
                                stages{
                                    stage('Configuring Testing Environment'){
                                        steps{
                                            discoverGitReferenceBuild(latestBuildIfNotFound: true)
                                            mineRepository()
                                            retry(3){
                                                script{
                                                    try{
                                                        sh(
                                                            label: 'Create virtual environment',
                                                            script: '''python3 -m venv bootstrap_uv
                                                                       bootstrap_uv/bin/pip install --disable-pip-version-check uv
                                                                       bootstrap_uv/bin/uv venv venv
                                                                       . ./venv/bin/activate
                                                                       bootstrap_uv/bin/uv pip install uv
                                                                       rm -rf bootstrap_uv
                                                                       uv pip install -r requirements-dev.txt
                                                                       '''
                                                                   )
                                                        sh(
                                                            label: 'Install package in development mode',
                                                            script: '''. ./venv/bin/activate
                                                                       uv pip install -e .
                                                                    '''
                                                            )
                                                    } catch (e) {
                                                        cleanWs(
                                                            patterns: [
                                                                [pattern: 'venv', type: 'INCLUDE'],
                                                                [pattern: 'bootstrap_uv', type: 'INCLUDE'],
                                                            ]
                                                        )
                                                        throw e
                                                    }
                                                }
                                            }
                                            sh(
                                                label: 'Creating logging and report directories',
                                                script: '''mkdir -p logs
                                                           mkdir -p reports
                                                        '''
                                            )
                                        }
                                    }
                                    stage('Run Tests'){
                                        parallel {
                                            stage('Run PyTest Unit Tests'){
                                                steps{
                                                    catchError(buildResult: 'UNSTABLE', message: 'Did not pass all pytest tests', stageResult: 'UNSTABLE') {
                                                        sh(
                                                            script: '''. ./venv/bin/activate
                                                                       PYTHONFAULTHANDLER=1 coverage run --parallel-mode --source=speedwagon -m pytest --junitxml=./reports/tests/pytest/pytest-junit.xml --capture=no
                                                                   '''
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
                                                        sh './venv/bin/uvx --python-preference=only-managed --with-requirements requirements-gui.txt pip-audit --cache-dir=/tmp/pip-audit-cache --local'

                                                    }
                                                }
                                            }
                                            stage('Run Doctest Tests'){
                                                steps {
                                                    sh(
                                                        label: 'Running Doctest Tests',
                                                        script: '''. ./venv/bin/activate
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
                                            stage('Run Docs linkcheck'){
                                                steps {
                                                    catchError(buildResult: 'SUCCESS', message: 'Sphinx docs linkcheck', stageResult: 'UNSTABLE') {
                                                        sh(
                                                            label: 'Running Sphinx docs linkcheck',
                                                            script: '''. ./venv/bin/activate
                                                                       python -m sphinx -b doctest docs/source build/docs -d build/docs/doctrees --no-color --builder=linkcheck --fail-on-warning
                                                                       '''
                                                            )
                                                    }
                                                }
                                            }
                                            stage('Run MyPy Static Analysis') {
                                                steps{
                                                    catchError(buildResult: 'SUCCESS', message: 'MyPy found issues', stageResult: 'UNSTABLE') {
                                                        tee('logs/mypy.log'){
                                                            sh(label: 'Running MyPy',
                                                               script: '''. ./venv/bin/activate
                                                                          mypy -p speedwagon --html-report reports/mypy/html
                                                                       '''
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
                                                        sh(label: 'Running Ruff',
                                                           script: '''. ./venv/bin/activate
                                                                       mkdir -p reports && ruff check --config=pyproject.toml -o reports/ruffoutput.json --output-format json
                                                                    '''
                                                        )
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
                                                        sh script: '''. ./venv/bin/activate
                                                                      flake8 speedwagon -j 1 --tee --output-file=logs/flake8.log
                                                                   '''
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
                                                            script: '''. ./venv/bin/activate
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
                                                sh '''. ./venv/bin/activate
                                                      coverage combine && coverage xml -o reports/coverage.xml && coverage html -d reports/coverage
                                                   '''
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
                                environment{
                                    VERSION="${readTOML( file: 'pyproject.toml')['project'].version}"
                                    SONAR_USER_HOME='/tmp/sonar'
                                }
                                steps{
                                    script{
                                        milestone label: 'sonarcloud'
                                        withSonarQubeEnv(installationName:'sonarcloud', credentialsId: params.SONARCLOUD_TOKEN) {
                                           def sourceInstruction
                                           if (env.CHANGE_ID){
                                               sourceInstruction = '-Dsonar.pullrequest.key=$CHANGE_ID -Dsonar.pullrequest.base=$BRANCH_NAME'
                                           } else{
                                               sourceInstruction = '-Dsonar.branch.name=$BRANCH_NAME'
                                           }
                                           sh(
                                               label: 'Running Sonar Scanner',
                                               script: """. ./venv/bin/activate
                                                           uv tool run pysonar-scanner -Dsonar.projectVersion=$VERSION -Dsonar.buildString=\"$BUILD_TAG\" ${sourceInstruction}
                                                       """
                                           )
                                        }
                                        timeout(time: 1, unit: 'HOURS') {
                                            def sonarqube_result = waitForQualityGate(abortPipeline: false)
                                            if (sonarqube_result.status != 'OK') {
                                                unstable "SonarQube quality gate: ${sonarqube_result.status}"
                                            }
                                            if(env.BRANCH_IS_PRIMARY){
                                                def outstandingIssues = get_sonarqube_unresolved_issues('.scannerwork/report-task.txt')
                                                writeJSON file: 'reports/sonar-report.json', json: outstandingIssues
                                                recordIssues(tools: [sonarQube(pattern: 'reports/sonar-report.json')])
                                           }
                                        }
                                   }
                                }
                            }
                        }
                        post{
                            cleanup{
                                cleanWs(patterns: [
                                        [pattern: 'venv/', type: 'INCLUDE'],
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
                            stage('Linux') {
                                when{
                                    expression {return nodesByLabel('linux && docker').size() > 0}
                                }
                                environment{
                                    PIP_CACHE_DIR='/tmp/pipcache'
                                    UV_INDEX_STRATEGY='unsafe-best-match'
                                    UV_TOOL_DIR='/tmp/uvtools'
                                    UV_PYTHON_INSTALL_DIR='/tmp/uvpython'
                                    UV_CACHE_DIR='/tmp/uvcache'
                                }
                                steps{
                                    script{
                                        def envs = []
                                        node('docker && linux'){
                                            docker.image('python').inside('--mount source=python-tmp-speedwagon,target=/tmp'){
                                                try{
                                                    checkout scm
                                                    sh(script: 'python3 -m venv venv && venv/bin/pip install --disable-pip-version-check uv')
                                                    envs = sh(
                                                        label: 'Get tox environments',
                                                        script: './venv/bin/uvx --constraint=requirements-dev.txt --quiet --with tox-uv tox list -d --no-desc',
                                                        returnStdout: true,
                                                    ).trim().split('\n')
                                                } finally{
                                                    cleanWs(
                                                        patterns: [
                                                            [pattern: 'venv/', type: 'INCLUDE'],
                                                            [pattern: '.tox', type: 'INCLUDE'],
                                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                                        ]
                                                    )
                                                }
                                            }
                                        }
                                        parallel(
                                            envs.collectEntries{toxEnv ->
                                                def version = toxEnv.replaceAll(/py(\d)(\d+).*/, '$1.$2')
                                                [
                                                    "Tox Environment: ${toxEnv}",
                                                    {
                                                        node('docker && linux && x86_64'){
                                                            checkout scm
                                                            retry(3){
                                                                def image = docker.build(UUID.randomUUID().toString(), '-f ci/docker/python/linux/jenkins/Dockerfile .')
                                                                try{
                                                                    image.inside('--mount source=python-tmp-speedwagon,target=/tmp'){
                                                                        sh( label: 'Running Tox',
                                                                            script: """python3 -m venv venv && venv/bin/pip install --disable-pip-version-check uv
                                                                                       trap "rm -rf venv" EXIT
                                                                                       . ./venv/bin/activate
                                                                                       uv python install cpython-${version}
                                                                                       trap "rm -rf ./venv ./.tox" EXIT
                                                                                       uvx -p ${version} --constraint=requirements-dev.txt --with tox-uv tox run -e ${toxEnv}
                                                                                    """
                                                                            )
                                                                    }
                                                                } finally {
                                                                    sh "docker image rm --force ${image.imageName()}"
                                                                    sh "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                                    cleanWs(
                                                                        patterns: [
                                                                            [pattern: 'venv/', type: 'INCLUDE'],
                                                                            [pattern: '.tox/', type: 'INCLUDE'],
                                                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                                                        ]
                                                                    )
                                                                }
                                                            }
                                                        }
                                                    }
                                                ]
                                            }
                                        )
                                    }
                                 }
                            }
                            stage('Windows') {
                                when{
                                    expression {return nodesByLabel('windows && docker && x86').size() > 0}
                                }
                                environment{
                                     UV_INDEX_STRATEGY='unsafe-best-match'
                                     PIP_CACHE_DIR='C:\\Users\\ContainerUser\\Documents\\pipcache'
                                     UV_TOOL_DIR='C:\\Users\\ContainerUser\\Documents\\uvtools'
                                     UV_PYTHON_INSTALL_DIR='C:\\Users\\ContainerUser\\Documents\\uvpython'
                                     UV_CACHE_DIR='C:\\Users\\ContainerUser\\Documents\\uvcache'
                                     VC_RUNTIME_INSTALLER_LOCATION='c:\\msvc_runtime\\'
                                }
                                steps{
                                    script{
                                        def envs = []
                                        node('docker && windows'){
                                            try{
                                                docker.image(env.DEFAULT_PYTHON_DOCKER_IMAGE ? env.DEFAULT_PYTHON_DOCKER_IMAGE: 'python').inside("--mount source=uv_python_install_dir,target=${env.UV_PYTHON_INSTALL_DIR}"){
                                                    checkout scm
                                                    bat(script: 'python -m venv venv && venv\\Scripts\\pip install --disable-pip-version-check uv')
                                                    envs = bat(
                                                        label: 'Get tox environments',
                                                        script: '@.\\venv\\Scripts\\uvx --quiet --constraint=requirements-dev.txt --with tox-uv tox list -d --no-desc',
                                                        returnStdout: true,
                                                    ).trim().split('\r\n')
                                                }
                                            } finally{
                                                cleanWs(
                                                    patterns: [
                                                        [pattern: 'venv/', type: 'INCLUDE'],
                                                        [pattern: '.tox/', type: 'INCLUDE'],
                                                        [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                                    ]
                                                )
                                                bat "${tool(name: 'Default', type: 'git')} clean -dfx"
                                            }
                                        }
                                        parallel(
                                            envs.collectEntries{toxEnv ->
                                                def version = toxEnv.replaceAll(/py(\d)(\d+).*/, '$1.$2')
                                                [
                                                    "Tox Environment: ${toxEnv}",
                                                    {
                                                        node('docker && windows'){
                                                            try{
                                                                docker.image(env.DEFAULT_PYTHON_DOCKER_IMAGE ? env.DEFAULT_PYTHON_DOCKER_IMAGE: 'python').inside(
                                                                "--mount type=volume,source=uv_python_install_dir,target=${env.UV_PYTHON_INSTALL_DIR}"
                                                                + " --mount type=volume,source=pipcache,target=${env.PIP_CACHE_DIR}"
                                                                + " --mount type=volume,source=uv_cache_dir,target=${env.UV_CACHE_DIR}"
                                                                ){
                                                                    checkout scm
                                                                    retry(3){
                                                                        bat(label: 'Running Tox',
                                                                            script: """python -m venv venv && venv\\Scripts\\pip install --disable-pip-version-check uv
                                                                                       venv\\Scripts\\uv python install cpython-${version}
                                                                                       venv\\Scripts\\uvx -p ${version} --constraint=requirements-dev.txt --with tox-uv tox run -e ${toxEnv}
                                                                                    """
                                                                        )
                                                                    }
                                                                }
                                                            } finally{
                                                                retry(3){
                                                                    try{
                                                                        bat "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                                    } catch(e) {
                                                                        echo 'failed to run git clean, sleeping for one second before moving forward to see if any processes are still running'
                                                                        sleep 1
                                                                        throw e
                                                                    } finally{
                                                                        cleanWs(
                                                                            patterns: [
                                                                                [pattern: 'venv/', type: 'INCLUDE'],
                                                                                [pattern: '.tox', type: 'INCLUDE'],
                                                                                [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                                                            ]
                                                                        )
                                                                        bat "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                ]
                                            }
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
            stage('Packaging'){
                when{
                    equals expected: true, actual: params.BUILD_PACKAGES
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
                                        args '--mount source=python-tmp-speedwagon,target=/tmp'
                                      }
                                }
                                environment{
                                    PIP_CACHE_DIR='/tmp/pipcache'
                                    UV_INDEX_STRATEGY='unsafe-best-match'
                                    UV_CACHE_DIR='/tmp/uvcache'
                                }
                                options {
                                    retry(2)
                                }
                                steps{
                                    timeout(5){
                                        sh(
                                            label: 'Package',
                                            script: '''python3 -m venv venv && venv/bin/pip install --disable-pip-version-check uv
                                                       trap "rm -rf venv" EXIT
                                                       . ./venv/bin/activate
                                                       uv build
                                                    '''
                                        )
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
                            stage('Testing Packages'){
                                when{
                                    equals expected: true, actual: params.TEST_PACKAGES
                                }
                                environment{
                                    UV_INDEX_STRATEGY='unsafe-best-match'
                                }
                                stages{
                                    stage('Twine Check'){
                                        agent{
                                            docker{
                                                image 'python'
                                                label 'linux && docker'
                                                args '--mount source=python-tmp-speedwagon,target=/tmp'
                                            }
                                        }
                                        environment{
                                            UV_TOOL_DIR='/tmp/uvtools'
                                            UV_CACHE_DIR='/tmp/uvcache'
                                        }
                                        steps{
                                            catchError(buildResult: 'UNSTABLE', message: 'twine check found issues', stageResult: 'UNSTABLE') {
                                                unstash 'PYTHON_PACKAGES'
                                                sh(
                                                    label: 'Checking with twine check',
                                                    script: '''python3 -m venv venv && venv/bin/pip install --disable-pip-version-check uv
                                                               trap "rm -rf venv" EXIT
                                                               . ./venv/bin/activate
                                                               uvx --constraint requirements-dev.txt twine check --strict  dist/*
                                                            '''
                                                )
                                            }
                                        }
                                    }
                                    stage('Packages Test Matrix'){
                                        steps{
                                            customMatrix(
                                                axes: [
                                                    [
                                                        name: 'PYTHON_VERSION',
                                                        values: ['3.10', '3.11', '3.12', '3.13']
                                                    ],
                                                    [
                                                        name: 'OS',
                                                        values: ['linux','macos', 'windows']
                                                    ],
                                                    [
                                                        name: 'ARCHITECTURE',
                                                        values: ['x86_64', 'arm64']
                                                    ],
                                                    [
                                                        name: 'PACKAGE_TYPE',
                                                        values: ['wheel', 'sdist'],
                                                    ]
                                                ],
                                                excludes: [
                                                    [
                                                        [
                                                            name: 'OS',
                                                            values: 'windows'
                                                        ],
                                                        [
                                                            name: 'ARCHITECTURE',
                                                            values: 'arm64',
                                                        ]
                                                    ]
                                                ],
                                                when: {entry -> "INCLUDE_${entry.OS}-${entry.ARCHITECTURE}".toUpperCase() && params["INCLUDE_${entry.OS}-${entry.ARCHITECTURE}".toUpperCase()]},
                                                stages: [
                                                    { entry ->
                                                        stage('Test Package') {
                                                            node("${entry.OS} && ${entry.ARCHITECTURE} ${['linux', 'windows'].contains(entry.OS) ? '&& docker': ''}"){
                                                                try{
                                                                    checkout scm
                                                                    unstash 'PYTHON_PACKAGES'
                                                                    if(['linux', 'windows'].contains(entry.OS) && params.containsKey("INCLUDE_${entry.OS}-${entry.ARCHITECTURE}".toUpperCase()) && params["INCLUDE_${entry.OS}-${entry.ARCHITECTURE}".toUpperCase()]){
                                                                        docker.image(env.DEFAULT_PYTHON_DOCKER_IMAGE ? env.DEFAULT_PYTHON_DOCKER_IMAGE: 'python').inside(
                                                                            isUnix() ?
                                                                                '--mount source=python-tmp-speedwagon,target=/tmp'
                                                                            :
                                                                                '--mount type=volume,source=uv_python_install_dir,target=c:\\Users\\ContainerUser\\Documents\\cache\\uvpython'
                                                                                + ' --mount type=volume,source=msvc-runtime,target=c:\\msvc_runtime'
                                                                                + ' --mount type=volume,source=pipcache,target=c:\\Users\\ContainerUser\\Documents\\cache\\pipcache'
                                                                                + ' --mount type=volume,source=uv_cache_dir,target=c:\\Users\\ContainerUser\\Documents\\cache\\uvcache'
                                                                            ){
                                                                             if(isUnix()){
                                                                                withEnv([
                                                                                    'PIP_CACHE_DIR=/tmp/pipcache',
                                                                                    'UV_TOOL_DIR=/tmp/uvtools',
                                                                                    'UV_PYTHON_INSTALL_DIR=/tmp/uvpython',
                                                                                    'UV_CACHE_DIR=/tmp/uvcache',
                                                                                ]){
                                                                                     sh(
                                                                                        label: 'Testing with tox',
                                                                                        script: """python3 -m venv venv
                                                                                                   ./venv/bin/pip install --disable-pip-version-check uv
                                                                                                   ./venv/bin/uv python install cpython-${entry.PYTHON_VERSION}
                                                                                                   ./venv/bin/uvx --constraint=requirements-dev.txt --with tox-uv tox --installpkg ${findFiles(glob: entry.PACKAGE_TYPE == 'wheel' ? 'dist/*.whl' : 'dist/*.tar.gz')[0].path} -e py${entry.PYTHON_VERSION.replace('.', '')}
                                                                                                """
                                                                                    )
                                                                                }
                                                                             } else {
                                                                                withEnv([
                                                                                    'PIP_CACHE_DIR=c:\\Users\\ContainerUser\\Documents\\cache\\pipcache',
                                                                                    'UV_TOOL_DIR=c:\\Users\\ContainerUser\\Documents\\uvtools',
                                                                                    'UV_PYTHON_INSTALL_DIR=c:\\Users\\ContainerUser\\Documents\\cache\\uvpython',
                                                                                    'UV_CACHE_DIR=c:\\Users\\ContainerUser\\Documents\\cache\\uvcache',
                                                                                    'UV_LINK_MODE=copy'
                                                                                ]){
                                                                                    installMSVCRuntime('c:\\msvc_runtime\\')
                                                                                    bat(
                                                                                        label: 'Testing with tox',
                                                                                        script: """python -m venv venv
                                                                                                   .\\venv\\Scripts\\pip install --disable-pip-version-check uv
                                                                                                   .\\venv\\Scripts\\uv python install cpython-${entry.PYTHON_VERSION}
                                                                                                   .\\venv\\Scripts\\uvx --constraint=requirements-dev.txt --with tox-uv tox --installpkg ${findFiles(glob: entry.PACKAGE_TYPE == 'wheel' ? 'dist/*.whl' : 'dist/*.tar.gz')[0].path} -e py${entry.PYTHON_VERSION.replace('.', '')}
                                                                                                """
                                                                                    )
                                                                                }
                                                                             }
                                                                        }
                                                                    } else {
                                                                        if(isUnix()){
                                                                            sh(
                                                                                label: 'Testing with tox',
                                                                                script: """python3 -m venv venv
                                                                                           ./venv/bin/pip install --disable-pip-version-check uv
                                                                                           ./venv/bin/uvx --constraint=requirements-dev.txt --with tox-uv tox --installpkg ${findFiles(glob: entry.PACKAGE_TYPE == 'wheel' ? 'dist/*.whl' : 'dist/*.tar.gz')[0].path} -e py${entry.PYTHON_VERSION.replace('.', '')}
                                                                                        """
                                                                            )
                                                                        } else {
                                                                            bat(
                                                                                label: 'Testing with tox',
                                                                                script: """python -m venv venv
                                                                                           .\\venv\\Scripts\\pip install --disable-pip-version-check uv
                                                                                           .\\venv\\Scripts\\uv python install cpython-${entry.PYTHON_VERSION}
                                                                                           .\\venv\\Scripts\\uvx --constraint=requirements-dev.txt --with tox-uv tox --installpkg ${findFiles(glob: entry.PACKAGE_TYPE == 'wheel' ? 'dist/*.whl' : 'dist/*.tar.gz')[0].path} -e py${entry.PYTHON_VERSION.replace('.', '')}
                                                                                        """
                                                                            )
                                                                        }
                                                                    }
                                                                } finally{
                                                                    if(isUnix()){
                                                                        sh "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                                    } else {
                                                                        bat "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
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
            stage('Deploy'){
                parallel {
                    stage('Deploy to pypi') {
                        environment{
                            PIP_CACHE_DIR='/tmp/pipcache'
                            UV_INDEX_STRATEGY='unsafe-best-match'
                            UV_TOOL_DIR='/tmp/uvtools'
                            UV_PYTHON_INSTALL_DIR='/tmp/uvpython'
                            UV_CACHE_DIR='/tmp/uvcache'
                        }
                        agent {
                            docker{
                                image 'python'
                                label 'docker && linux'
                                args '--mount source=python-tmp-speedwagon,target=/tmp'
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
                            withEnv(
                                [
                                    "TWINE_REPOSITORY_URL=${SERVER_URL}",
                                    'UV_INDEX_STRATEGY=unsafe-best-match'
                                ]
                            ){
                                withCredentials(
                                    [
                                        usernamePassword(
                                            credentialsId: 'jenkins-nexus',
                                            passwordVariable: 'TWINE_PASSWORD',
                                            usernameVariable: 'TWINE_USERNAME'
                                        )
                                    ]
                                ){
                                    sh(
                                        label: 'Uploading to pypi',
                                        script: '''python3 -m venv venv
                                                   trap "rm -rf venv" EXIT
                                                   . ./venv/bin/activate
                                                   pip install --disable-pip-version-check uv
                                                   uvx --constraint=requirements-dev.txt twine upload --disable-progress-bar --non-interactive dist/*
                                                '''
                                    )
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
                }
            }
        }
    }
}