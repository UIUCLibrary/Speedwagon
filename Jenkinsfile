#!groovy
@Library("ds-utils@v0.2.0") // Uses library from https://github.com/UIUCLibrary/Jenkins_utils
import org.ds.*
pipeline {
    agent {
        label "Windows && Python3"
    }
    
    triggers {
        cron('@daily')
    }

    options {
        disableConcurrentBuilds()  //each branch has 1 job running at a time
    }

    environment {
        mypy_args = "--junit-xml=mypy.xml"
        build_number = VersionNumber(projectStartDate: '2017-11-08', versionNumberString: '${BUILD_DATE_FORMATTED, "yy"}${BUILD_MONTH, XX}${BUILDS_THIS_MONTH, XXX}', versionPrefix: '', worstResultForIncrement: 'SUCCESS')
        // pytest_args = "--junitxml=reports/junit-{env:OS:UNKNOWN_OS}-{envname}.xml --junit-prefix={env:OS:UNKNOWN_OS}  --basetemp={envtmpdir}"
    }

    parameters {
        // string(name: "PROJECT_NAME", defaultValue: "Speedwagon", description: "Name given to the project")
        booleanParam(name: "UPDATE_JIRA_EPIC", defaultValue: false, description: "Write a Update information on JIRA board")
        string(name: 'JIRA_ISSUE', defaultValue: "PSR-83", description: 'Jira task to generate about updates.')   
        booleanParam(name: "BUILD_DOCS", defaultValue: true, description: "Build documentation")
        booleanParam(name: "TEST_RUN_PYTEST", defaultValue: true, description: "Run PyTest unit tests") 
        booleanParam(name: "TEST_RUN_BEHAVE", defaultValue: true, description: "Run Behave unit tests")
        booleanParam(name: "TEST_RUN_DOCTEST", defaultValue: true, description: "Test documentation")
        booleanParam(name: "TEST_RUN_FLAKE8", defaultValue: true, description: "Run Flake8 static analysis")
        booleanParam(name: "TEST_RUN_MYPY", defaultValue: true, description: "Run MyPy static analysis")
        booleanParam(name: "TEST_RUN_TOX", defaultValue: true, description: "Run Tox Tests")
        booleanParam(name: "PACKAGE_PYTHON_FORMATS", defaultValue: true, description: "Create native Python packages")
        booleanParam(name: "PACKAGE_WINDOWS_STANDALONE", defaultValue: true, description: "Windows Standalone")
        booleanParam(name: "DEPLOY_DEVPI", defaultValue: true, description: "Deploy to devpi on https://devpi.library.illinois.edu/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: "DEPLOY_SCCM", defaultValue: true, description: "Request deployment of MSI installer to SCCM")
        // choice(choices: 'None\nRelease_to_devpi_only\nRelease_to_devpi_and_sccm\n', description: "Release the build to production. Only available in the Master branch", name: 'RELEASE')
        booleanParam(name: "DEPLOY_DOCS", defaultValue: false, description: "Update online documentation")
        string(name: 'URL_SUBFOLDER', defaultValue: "speedwagon", description: 'The directory that the docs should be saved under')
    }
    
    stages {
        stage("Testing Jira epic"){
            agent any
            when {
                equals expected: true, actual: params.UPDATE_JIRA_EPIC
                // expression {params.UPDATE_JIRA_EPIC == true}
            }
            steps {
                echo "Finding Jira epic"
                script {
                    // def result = jiraSearch "issue = $params.JIRA_ISSUE"
                    // jiraComment body: 'Just a test', issueKey: 'PSR-83'
                    def result = jiraGetIssue idOrKey: 'PSR-83', site: 'https://bugs.library.illinois.edu'
                    echo "result = ${result}"
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
        }
        stage("Configure Environment"){
            steps {
                stash includes: 'deployment.yml', name: "Deployment"
                bat "${tool 'CPython-3.6'} -m venv venv"
                bat "venv\\Scripts\\pip.exe install -r requirements.txt"
                bat "venv\\Scripts\\pip.exe install -r requirements-dev.txt"
                bat 'venv\\Scripts\\pip.exe install "setuptools>=30.3.0"'
                bat "venv\\Scripts\\pip.exe install devpi-client"
                bat 'mkdir "reports/mypy/stdout"'
            }
        }
        stage('Build') {
            parallel {
                stage("Python Package"){
                    steps {
                        tee('build.log') {
                            bat "venv\\Scripts\\python.exe setup.py build"
                        }
                    }
                    post{
                        always{
                            warnings parserConfigurations: [[parserName: 'Pep8', pattern: 'build.log']]
                            archiveArtifacts artifacts: 'build.log'
                        }
                    }
                }
                stage("Sphinx documentation"){
                    when {
                        equals expected: true, actual: params.BUILD_DOCS
                    }
                    steps {
                        tee('build_sphinx.log') {
                            bat "venv\\Scripts\\python.exe setup.py build_sphinx"
                        }
                    }
                    post{
                        always {
                            warnings parserConfigurations: [[parserName: 'Pep8', pattern: 'build_sphinx.log']]
                        }
                        success{
                            publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'build/docs/html', reportFiles: 'index.html', reportName: 'Documentation', reportTitles: ''])
                            script{
                                // Multibranch jobs add the slash and add the branch to the job name. I need only the job name
                                def alljob = env.JOB_NAME.tokenize("/") as String[]
                                def project_name = alljob[0]
                                dir('build/docs/') {
                                    zip archive: true, dir: 'html', glob: '', zipFile: "${project_name}-${env.BRANCH_NAME}-docs-html-${env.GIT_COMMIT.substring(0,7)}.zip"
                                    dir("html"){
                                        stash includes: '**', name: "HTML Documentation"
                                    }
                                }
                            }
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
                        bat "venv\\Scripts\\behave.exe --junit --junit-directory reports/behave"
                    }
                    post {
                        always {
                            junit "reports/behave/*.xml"
                        }
                    }
                }
                stage("Run Pytest Unit Tests"){
                    when {
                       equals expected: true, actual: params.TEST_RUN_PYTEST
                    }
                    environment{
                        junit_filename = "junit-${env.NODE_NAME}-${env.GIT_COMMIT.substring(0,7)}-pytest.xml"
                    }
                    steps{
                        bat "venv\\Scripts\\py.test.exe --junitxml=reports/pytest/${junit_filename} --junit-prefix=${env.NODE_NAME}-pytest --cov-report html:reports/pytestcoverage/ --cov=speedwagon"
                    }
                    post {
                        always {
                            publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/pytestcoverage', reportFiles: 'index.html', reportName: 'Coverage', reportTitles: ''])
                            junit "reports/pytest/${junit_filename}"
                        }
                    }
                }
                stage("Run Doctest Tests"){
                    when {
                       equals expected: true, actual: params.TEST_RUN_FLAKE8
                    }
                    steps {
                        bat "venv\\Scripts\\sphinx-build.exe -b doctest -d build/docs/doctrees docs/source reports/doctest"
                    }
                    post{
                        always {
                            archiveArtifacts artifacts: 'reports/doctest/output.txt'
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
                                tee('mypy.log') {
                                    bat "venv\\Scripts\\mypy.exe -p speedwagon --html-report reports\\mypy\\html\\"
                                }
                            } catch (exc) {
                                echo "MyPy found some warnings"
                            }      
                        }
                    }
                    post {
                        always {
                            warnings parserConfigurations: [[parserName: 'MyPy', pattern: 'mypy.log']], unHealthy: ''
                            publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/mypy/html/', reportFiles: 'index.html', reportName: 'MyPy HTML Report', reportTitles: ''])
                        }
                    }
                }
                stage("Run Tox test") {
                    when{
                        equals expected: true, actual: params.TEST_RUN_TOX
                    }
                    agent{
                        label "Windows && DevPi"
                    }
                    steps {
                        bat "${tool 'CPython-3.6'} -m venv venv"
                        bat 'venv\\Scripts\\python.exe -m pip install -U setuptools'
                        bat 'venv\\Scripts\\python.exe -m pip install tox'
                        bat "venv\\Scripts\\tox.exe"
                    }
                }
                stage("Run Flake8 Static Analysis") {
                    when {
                        equals expected: true, actual: params.TEST_RUN_FLAKE8
                    }
                    steps{
                        script{
                            try{
                                tee('flake8.log') {
                                    bat "venv\\Scripts\\flake8.exe speedwagon --format=pylint"
                                }
                            } catch (exc) {
                                echo "flake8 found some warnings"
                            }
                        }
                    }
                    post {
                        always {
                            warnings parserConfigurations: [[parserName: 'PyLint', pattern: 'flake8.log']], unHealthy: ''
                        }
                    }
                }
            }
        }
        stage("Packaging") {
            parallel {
                stage("Source and Wheel formats"){
                    when {
                        equals expected: true, actual: params.PACKAGE_PYTHON_FORMATS
                    }
                    steps{
                        bat "venv\\Scripts\\python.exe setup.py bdist_wheel sdist"
                    }
                    post {
                        always {
                            dir("dist") {
                                archiveArtifacts artifacts: "*.whl", fingerprint: true
                                archiveArtifacts artifacts: "*.tar.gz", fingerprint: true
                                archiveArtifacts artifacts: "*.zip", fingerprint: true
                            }
                        }
                    }
                }
                stage("Windows Standalone"){
                    agent {
                        node {
                            label "Windows && VS2015 && DevPi"
                        }
                    }
                    // PACKAGE_WINDOWS_STANDALONE
                    when {
                        not { changeRequest()}
                        equals expected: true, actual: params.PACKAGE_WINDOWS_STANDALONE
                    }
                    steps {
                        tee('build_standalone.log') {
                            bat "call make.bat standalone"
                        }
                        warnings parserConfigurations: [[parserName: 'MSBuild', pattern: 'build_standalone.log']]
                        archiveArtifacts artifacts: 'build_standalone.log'
                        dir("dist") {
                            stash includes: "*.msi", name: "msi"
                        }
                    }
                    post {
                        success {
                            dir("dist") {
                                archiveArtifacts artifacts: "*.msi", fingerprint: true
                            }
                        }
                    }
                }
            }

        }

        stage("Deploy to Devpi Staging") {
            // when {
            //     expression { params.DEPLOY_DEVPI == true && (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "dev")}
            // }
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
                bat "venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu"
                withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                    bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                    bat "venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                    script {
                        bat "venv\\Scripts\\devpi.exe upload --from-dir dist"
                        try {
                            bat "venv\\Scripts\\devpi.exe upload --only-docs"
                        } catch (exc) {
                            echo "Unable to upload to devpi with docs."
                        }
                    }
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

            // when {
            //     expression { params.DEPLOY_DEVPI == true && (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "dev")}
            // }
            parallel {
                stage("Source Distribution: .tar.gz") {
                    steps {
                        script {
                            def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                            def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                            node("Windows") {
                                bat "${tool 'CPython-3.6'} -m venv venv"
                                bat "venv\\Scripts\\pip.exe install tox devpi-client"
                                bat "venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu"
                                withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                                    bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                                    bat "venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                                    echo "Testing Source package in devpi"
                                    bat "venv\\Scripts\\devpi.exe test --index https://devpi.library.illinois.edu/${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging ${name} -s tar.gz"
                                }
                            }
                        }
                    }
                }
                stage("Source Distribution: .zip") {
                    steps {
                        script {
                            def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                            def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                            node("Windows") {
                                bat "${tool 'CPython-3.6'} -m venv venv"
                                bat "venv\\Scripts\\pip.exe install tox devpi-client"
                                bat "venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu"
                                withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                                    bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                                    bat "venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                                    echo "Testing Source package in devpi"
                                    bat "venv\\Scripts\\devpi.exe test --index https://devpi.library.illinois.edu/${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging ${name} -s zip"
                                }
                            }
                        }
                    }
                }
                stage("Built Distribution: .whl") {
                    steps {
                        script {
                            def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                            def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                            node("Windows") {
                                bat "${tool 'CPython-3.6'} -m venv venv"
                                bat "venv\\Scripts\\pip.exe install tox devpi-client"
                                bat "venv\\Scripts\\devpi.exe use https://devpi.library.illinois.edu"
                                withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                                    bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                                    bat "venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                                    echo "Testing Whl package in devpi"
                                    bat "venv\\Scripts\\devpi.exe test --index https://devpi.library.illinois.edu/${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging ${name} -s whl"
                                }
                            }
                        }

                    }
                }
            }
            post {
                success {
                    echo "it Worked. Pushing file to ${env.BRANCH_NAME} index"
                    script {
                        def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                        def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                        withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                            bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                            bat "venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                            bat "venv\\Scripts\\devpi.exe push ${name}==${version} ${DEVPI_USERNAME}/${env.BRANCH_NAME}"
                        }

                    }
                }
            }
        }
        stage("Deploy"){
            when {
              branch "master"
            }
            parallel {
                stage("Deploy Online Documentation") {
                    when{
                        equals expected: true, actual: params.DEPLOY_DOCS
                    }
                    steps{
                        bat "venv\\Scripts\\python.exe setup.py build_sphinx"
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
                }
                stage("Deploy to DevPi Production") {
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION
                            branch "master"
                        }
                    }
                    steps {
                        script {
                            def name = bat(returnStdout: true, script: "@${tool 'Python3.6.3_Win64'} setup.py --name").trim()
                            def version = bat(returnStdout: true, script: "@${tool 'Python3.6.3_Win64'} setup.py --version").trim()
                            input "Release ${name} ${version} to DevPi Production?"
                            withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                                bat "${tool 'Python3.6.3_Win64'} -m devpi login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                                bat "${tool 'Python3.6.3_Win64'} -m devpi use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                                bat "${tool 'Python3.6.3_Win64'} -m devpi push ${name}==${version} production/release"
                            }
                        }
                    }
                }
                stage("Deploy to SCCM") {
                    when {
                        equals expected: true, actual: params.DEPLOY_SCCM
                        // expression { params.RELEASE == "Release_to_devpi_and_sccm"}
                    }

                    steps {
                        node("Linux"){
                            unstash "msi"
                            script{
                                def name = bat(returnStdout: true, script: "@${tool 'Python3.6.3_Win64'} setup.py --name").trim()
                                deployStash("msi", "${env.SCCM_STAGING_FOLDER}/${name}/")
                                input("Deploy to production?")
                                deployStash("msi", "${env.SCCM_UPLOAD_FOLDER}")
                            }
                        }
                    }
                    post {
                        success {
                            script{
                                def  deployment_request = requestDeploy this, "deployment.yml"
                                echo deployment_request
                                writeFile file: "deployment_request.txt", text: deployment_request
                                archiveArtifacts artifacts: "deployment_request.txt"
                            }
                        }
                    }
                }
            }
        }

    }
    post {
        cleanup {
            bat "venv\\Scripts\\python.exe setup.py clean --all"
        
            dir('dist') {
                deleteDir()
            }
            dir('build') {
                deleteDir()
            }
            script {
                if (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "dev"){
                    def name = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --name").trim()
                    def version = bat(returnStdout: true, script: "@${tool 'CPython-3.6'} setup.py --version").trim()
                    withCredentials([usernamePassword(credentialsId: 'DS_devpi', usernameVariable: 'DEVPI_USERNAME', passwordVariable: 'DEVPI_PASSWORD')]) {
                        bat "venv\\Scripts\\devpi.exe login ${DEVPI_USERNAME} --password ${DEVPI_PASSWORD}"
                        bat "venv\\Scripts\\devpi.exe use /${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                        try {
                            bat "venv\\Scripts\\devpi.exe remove -y ${name}==${version}"
                        } catch (Exception ex) {
                            echo "Failed to remove ${name}==${version} from ${DEVPI_USERNAME}/${env.BRANCH_NAME}_staging"
                        }
                        
                    }
                }
            }
        }
    }
}
