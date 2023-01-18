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
            ).trim().split('\r\n')
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
    def retries = args.containsKey('retry') ? args.retry : 1
    script{
        def envs
        def originalNodeLabel
        def dockerImageName = "${currentBuild.fullProjectName}:tox".replaceAll("-", "").replaceAll('/', "").replaceAll(' ', "").toLowerCase()
        retry(retries){
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
                        script: "docker image rm --no-prune ${dockerImageName}"
                    )
                } else {
                    bat(
                        label: "Removing Docker Image used to run tox",
                        script: """docker image rm --no-prune ${dockerImageName}
                                   """
                    )
                }
            }
        }
        echo "Found tox environments for ${envs.join(', ')}"
        def jobs = envs.collectEntries({ tox_env ->
            def tox_result
            def githubChecksName = "Tox: ${tox_env} ${envNamePrefix}"
            def jenkinsStageName = "${envNamePrefix} ${tox_env}"
            def nodesUsed = []
            [jenkinsStageName,{
                retry(retries){
                    node(label){
                        ws{
                            checkout scm
                            def dockerImageForTesting = docker.build(dockerImageName, "-f ${dockerfile} ${dockerArgs} . ")
                            try{
                                dockerImageForTesting.inside{
                                    if(isUnix()){
                                        sh(
                                            label: "Running Tox with ${tox_env} environment",
                                            script: "tox -v -e ${tox_env}"
                                        )
                                    } else {
                                        bat(
                                            label: "Running Tox with ${tox_env} environment",
                                            script: "tox -v -e ${tox_env}"
                                        )
                                    }
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: ".tox/", type: 'INCLUDE'],
                                        ]
                                    )
                                }
                            } finally {
                                if(isUnix()){
                                    def runningContainers = sh(
                                                               script: "docker ps --no-trunc --filter ancestor=${dockerImageName} --format {{.Names}}",
                                                               returnStdout: true,
                                                               )
                                    if (!runningContainers?.trim()) {
                                        sh(
                                            label: "Removing Docker Image used to run tox",
                                            script: "docker image rm --no-prune ${dockerImageName}",
                                            returnStatus: true
                                        )
                                    }
                                    sh(script: "docker ps --no-trunc --filter ancestor=${dockerImageName} --format {{.Names}}")
                                } else {
                                    def runningContainers = powershell(
                                                    returnStdout: true,
                                                    script: "docker ps --no-trunc --filter \"ancestor=${dockerImageName}\" --format \"{{.Names}}\""
                                                    )
                                    if (!runningContainers?.trim()) {
                                        powershell(
                                            label: "Removing Docker Image used to run tox",
                                            script: "docker image rm --no-prune ${dockerImageName}",
                                            returnStatus: true
                                        )
                                    }
                                    powershell(script: "docker ps --no-trunc --filter \"ancestor=${dockerImageName}\" --format \"{{.Names}}\"")
                                }
                            }
                        }
                    }
                }
            }]
        })
        return jobs
    }
}
return this
