def getToxEnvs(){
    def envs
    if(isUnix()){
        envs = sh(
                label: "Getting Tox Environments",
                returnStdout: true,
                script: "tox -l"
            ).trim().split('\n')
    } else{
        envs = bat(
                label: "Getting Tox Environments",
                returnStdout: true,
                script: "@tox -l"
            ).trim().split('\n')
    }
    envs.collect{
        it.trim()
    }
    return envs
}

def getToxEnvs2(tox){
    def envs
    if(isUnix()){
        envs = sh(
                label: "Getting Tox Environments",
                returnStdout: true,
                script: "${tox} -l"
            ).trim().split('\n')
    } else{
        envs = bat(
                label: "Getting Tox Environments",
                returnStdout: true,
                script: "@${tox} -l"
            ).trim().split('\n')
    }
    envs.collect{
        it.trim()
    }
    return envs
}

def generateToxPackageReport(testEnv){

        def packageReport = "\n**Installed Packages:**"
        testEnv['installed_packages'].each{
            packageReport =  packageReport + "\n ${it}"
        }

        return packageReport
}

def getBasicToxMetadataReport(toxResultFile){
    def tox_result = readJSON(file: toxResultFile)
    def testingEnvReport = """# Testing Environment

**Tox Version:** ${tox_result['toxversion']}
**Platform:**   ${tox_result['platform']}
"""
    return testingEnvReport
}
def getPackageToxMetadataReport(tox_env, toxResultFile){
    def tox_result = readJSON(file: toxResultFile)

    if(! tox_result['testenvs'].containsKey(tox_env)){
        def w = tox_result['testenvs']
        tox_result['testenvs'].each{key, test_env->
            test_env.each{
                echo "${it}"
            }
        }
        error "No test env for ${tox_env} found in ${toxResultFile}"
    }
    def tox_test_env = tox_result['testenvs'][tox_env]
    def packageReport = generateToxPackageReport(tox_test_env)
    return packageReport
}
def getErrorToxMetadataReport(tox_env, toxResultFile){
    def tox_result = readJSON(file: toxResultFile)
    def testEnv = tox_result['testenvs'][tox_env]
    def errorMessages = []
    if (testEnv == null){
        return tox_result['testenvs']
    }
    testEnv["test"].each{
        if (it['retcode'] != 0){
            echo "Found error ${it}"
            def errorOutput =  it['output']
            def failedCommand = it['command']
            errorMessages += "**${failedCommand}**\n${errorOutput}"
        }
    }
    def resultsReport = "# Results"
    if (errorMessages.size() > 0){
         return resultsReport + "\n" + errorMessages.join("\n")
    }
    return ""
}

def generateToxReport(tox_env, toxResultFile){
    if(!fileExists(toxResultFile)){
        error "No file found for ${toxResultFile}"
    }
    def reportSections = []

    try{
        reportSections += getBasicToxMetadataReport(toxResultFile)
        try{
            reportSections += getPackageToxMetadataReport(tox_env, toxResultFile)
        }catch(e){
            echo "Unable to parse installed packages info"

        }
        reportSections += getErrorToxMetadataReport(tox_env, toxResultFile)
    } catch (e){
        echo "Unable to parse json file, Falling back to reading the file as text. \nReason: ${e}"
        def data =  readFile(toxResultFile)
        reportSections += "``` json\n${data}\n```"
    }
    return reportSections.join("\n")
}

def getToxTestsParallel(args = [:]){
    def envNamePrefix = args['envNamePrefix']
    def label = args['label']
    def dockerfile = args['dockerfile']
    def dockerArgs = args['dockerArgs']
    script{
        def TOX_RESULT_FILE_NAME = "tox_result.json"
        def envs
        def originalNodeLabel
        def dockerImageName = "${currentBuild.fullProjectName}:tox".replaceAll("-", "").replaceAll('/', "").replaceAll(' ', "").toLowerCase()
        node(label){
            originalNodeLabel = env.NODE_NAME
            checkout scm
            def dockerImage = docker.build(dockerImageName, "-f ${dockerfile} ${dockerArgs} .")
            dockerImage.inside{
                envs = getToxEnvs()
            }
            if(isUnix()){
                sh(
                    label: "Removing Docker Image used to run tox",
                    script: "docker image ls ${dockerImageName}"
                )
            } else {
                bat(
                    label: "Removing Docker Image used to run tox",
                    script: """docker image ls ${dockerImageName}
                               """
                )
            }
        }
        echo "Found tox environments for ${envs.join(', ')}"
        def dockerImageForTesting
        node(originalNodeLabel){
            checkout scm
            dockerImageForTesting = docker.build(dockerImageName, "-f ${dockerfile} ${dockerArgs} . ")

        }
        echo "Adding jobs to ${originalNodeLabel}"
        def jobs = envs.collectEntries({ tox_env ->
            def tox_result
            def githubChecksName = "Tox: ${tox_env} ${envNamePrefix}"
            def jenkinsStageName = "${envNamePrefix} ${tox_env}"

            [jenkinsStageName,{
                node(originalNodeLabel){
                    ws{
                        checkout scm
                        dockerImageForTesting.inside{
                            try{
                                publishChecks(
                                    conclusion: 'NONE',
                                    name: githubChecksName,
                                    status: 'IN_PROGRESS',
                                    summary: 'Use Tox to test installed package',
                                    title: 'Running Tox'
                                )
                                if(isUnix()){
                                    sh(
                                        label: "Running Tox with ${tox_env} environment",
                                        script: "tox  -vv --parallel--safe-build --result-json=${TOX_RESULT_FILE_NAME} --workdir=/tmp -e $tox_env"
                                    )
                                } else {
                                    bat(
                                        label: "Running Tox with ${tox_env} environment",
                                        script: "tox  -vv --parallel--safe-build --result-json=${TOX_RESULT_FILE_NAME} --workdir=%TEMP% -e $tox_env "
                                    )
                                }
                            } catch (e){
                                def text
                                try{
                                    text = generateToxReport(tox_env, 'tox_result.json')
                                }
                                catch (ex){
                                    text = "No details given. Unable to read tox_result.json"
                                }
                                publishChecks(
                                    name: githubChecksName,
                                    summary: 'Use Tox to test installed package',
                                    text: text,
                                    conclusion: 'FAILURE',
                                    title: 'Failed'
                                )
                                throw e
                            }
                            def checksReportText = generateToxReport(tox_env, 'tox_result.json')
                            publishChecks(
                                    name: githubChecksName,
                                    summary: 'Use Tox to test installed package',
                                    text: "${checksReportText}",
                                    title: 'Passed'
                                )
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: TOX_RESULT_FILE_NAME, type: 'INCLUDE'],
                                    [pattern: ".tox/", type: 'INCLUDE'],
                                ]
                            )
                        }
                    }
                }
            }]
        })
        return jobs
    }
}
return this
