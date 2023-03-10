def upload(args = [:]){
    def credentialsId = args['credentialsId']
    def clientDir = args['clientDir'] ? args['clientDir']: './devpi'
    def index = args['index']
    def devpiExec = args['devpiExec'] ? args['devpiExec']: "devpi"
    withCredentials([usernamePassword(
                        credentialsId: credentialsId,
                        passwordVariable: 'DEVPI_PASSWORD',
                        usernameVariable: 'DEVPI_USERNAME'
                    )
                        ])
    {
        withEnv([
                "DEVPI_SERVER=${args['server']}",
                "CLIENT_DIR=${clientDir}",
                "DEVPI=${devpiExec}"
            ]) {
            withEnv([
                "INDEX=${args['server']}/${DEVPI_USERNAME}/${index}",
            ]) {
                if(isUnix()){
                    sh(label: 'Logging into DevPi',
                       script: '''$DEVPI use $DEVPI_SERVER --clientdir $CLIENT_DIR
                                  $DEVPI login $DEVPI_USERNAME --password=$DEVPI_PASSWORD --clientdir $CLIENT_DIR
                                  '''
                       )
               } else {
                   bat(label: 'Logging into DevPi',
                       script: '''%DEVPI% use %DEVPI_SERVER% --clientdir %CLIENT_DIR%
                                  %DEVPI% login %DEVPI_USERNAME% --password %DEVPI_PASSWORD% --clientdir %CLIENT_DIR%
                                  '''
                       )
               }
           }
           withEnv(["INDEX=/${DEVPI_USERNAME}/${index}"]){
               if(isUnix()){
                    sh(label: 'Uploading to DevPi Staging',
                       script: '''$DEVPI use --clientdir $CLIENT_DIR --debug
                                  $DEVPI upload --from-dir dist --clientdir $CLIENT_DIR --debug --index $INDEX
                                  '''
                    )
               } else {
                   bat(label: 'Uploading to DevPi Staging',
                       script: '''%DEVPI% use %INDEX% --clientdir %CLIENT_DIR%
                                  %DEVPI% upload --from-dir dist --clientdir %CLIENT_DIR%
                                  '''
                       )
               }
           }
       }
    }
}

def pushPackageToIndex(args = [:]){
    def sourceIndex = args['indexSource']
    def destinationIndex = args['indexDestination']
    def pkgName = args['pkgName']
    def pkgVersion = args['pkgVersion']
    def clientDir = args['clientDir'] ? args['clientDir']: './devpi'
    def devpi = args['devpiExec'] ? args['devpiExec']: "devpi"
    def server = args['server']

    withCredentials(
            [usernamePassword(
                credentialsId: args['credentialsId'],
                passwordVariable: 'DEVPI_PASSWORD',
                usernameVariable: 'DEVPI_USERNAME'
            )])
        {
        withEnv([
            "DEVPI_SERVER=${server}",
            "CLIENT_DIR=${clientDir}",
            "DEVPI=${devpi}"
            ]){
            if(isUnix()){
                sh(label: "Logging into DevPi",
                   script: '''$DEVPI use $DEVPI_SERVER --clientdir $CLIENT_DIR
                              $DEVPI login $DEVPI_USERNAME --password=$DEVPI_PASSWORD --clientdir $CLIENT_DIR
                              '''
                   )

            } else {
                bat(label: "Logging into DevPi Staging",
                   script: '''%DEVPI% use %DEVPI_SERVER% --clientdir %CLIENT_DIR%
                              %DEVPI% login %DEVPI_USERNAME% --password=%DEVPI_PASSWORD% --clientdir %CLIENT_DIR%
                              '''
                   )

            }
        }
    }
    if(isUnix()){
        sh(
            label: "Pushing DevPi package from ${sourceIndex} to ${destinationIndex}",
            script: "${devpi} push --index ${sourceIndex} ${pkgName}==${pkgVersion} ${destinationIndex} --clientdir ${clientDir}"
        )
    }
}

def removePackage(args = [:]){
    def clientDir = args['clientDir'] ? args['clientDir']: './devpi'
    def devpi = args['devpiExec'] ? args['devpiExec']: "devpi"
    def server = args['server']
    def pkgName = args['pkgName']
    def pkgVersion = args['pkgVersion']
    def index = args['index']
    withEnv([
        "DEVPI=${devpi}",
        "DEVPI_SERVER=${server}",
        "CLIENT_DIR=${clientDir}"
        ]){
        withCredentials(
                [usernamePassword(
                    credentialsId: args['credentialsId'],
                    passwordVariable: 'DEVPI_PASSWORD',
                    usernameVariable: 'DEVPI_USERNAME'
            )]){
            if(isUnix()){
                sh(label: "Logging into DevPi",
                   script: '''$DEVPI use $DEVPI_SERVER --clientdir $CLIENT_DIR
                              $DEVPI login $DEVPI_USERNAME --password=$DEVPI_PASSWORD --clientdir $CLIENT_DIR
                              '''
                   )

            } else {
                bat(label: "Logging into DevPi Staging",
                   script: '''%DEVPI% use %DEVPI_SERVER% --clientdir %CLIENT_DIR%
                              %DEVPI% login %DEVPI_USERNAME% --password=%DEVPI_PASSWORD% --clientdir %CLIENT_DIR%
                              '''
                   )

            }
        }
    }
    if(isUnix()){
        sh(label: "Removing Package from DevPi ${index} index",
           script: """${devpi} use ${index} --clientdir ${clientDir}
                      ${devpi} remove -y --index ${index} ${pkgName}==${pkgVersion} --clientdir ${clientDir}
                      """
           )
    } else{
       bat(label: "Removing Package from DevPi ${index} index",
           script: """${devpi} use ${index}--clientdir ${clientDir}
                      ${devpi} remove -y --index ${index} ${pkgName}==${pkgVersion} --clientdir ${clientDir}
                      """
           )

    }
}

def getNodeLabel(agent){
    def label
    if (agent.containsKey("dockerfile")){
        return agent.dockerfile.label
    }
    return label
}

def getAgent(args){
    if (args.agent.containsKey("label")){
        return { inner ->
            node(args.agent.label){
                ws{
                    inner()
                }
            }
        }

    }
    if (args.agent.containsKey("dockerfile")){
        def runArgs = args.agent.dockerfile.containsKey('args') ? args.agent.dockerfile['args']: ''
        return { inner ->
            node(args.agent.dockerfile.label){
                ws{
                    checkout scm
                    def dockerImage
                    def dockerImageName = "${currentBuild.fullProjectName}_devpi".replaceAll("-", "_").replaceAll('/', "_").replaceAll(' ', "").toLowerCase()
                    lock("docker build-${env.NODE_NAME}"){
                        dockerImage = docker.build(dockerImageName, "-f ${args.agent.dockerfile.filename} ${args.agent.dockerfile.additionalBuildArgs} .")
                    }
                    dockerImage.inside(runArgs){
                        inner()
                    }
                }
            }
        }
    }
    error('Invalid agent type, expect [dockerfile,label]')
}

def logIntoDevpiServer(devpiExec, serverUrl, credentialsId, clientDir){
    withEnv([
        "DEVPI=${devpiExec}",
        "DEVPI_SERVER=${serverUrl}",
        "CLIENT_DIR=${clientDir}"
        ]){
        withCredentials(
                [usernamePassword(
                    credentialsId: credentialsId,
                    passwordVariable: 'DEVPI_PASSWORD',
                    usernameVariable: 'DEVPI_USERNAME'
            )]){
            if(isUnix()){
                sh(label: "Logging into DevPi",
                   script: '''$DEVPI use $DEVPI_SERVER --clientdir $CLIENT_DIR
                              $DEVPI login $DEVPI_USERNAME --password=$DEVPI_PASSWORD --clientdir $CLIENT_DIR
                              '''
                   )

            } else {
                bat(label: "Logging into DevPi Staging",
                   script: '''%DEVPI% use %DEVPI_SERVER% --clientdir %CLIENT_DIR%
                              %DEVPI% login %DEVPI_USERNAME% --password=%DEVPI_PASSWORD% --clientdir %CLIENT_DIR%
                              '''
                   )

            }
        }
    }
}

def runDevpiTest(devpiExec, devpiIndex, pkgName, pkgVersion, pkgSelector, clientDir, toxEnv){
    if(isUnix()){
        sh('pip config list')
        sh(
            label: "Running tests on Packages on DevPi",
            script: "${devpiExec} test --index ${devpiIndex} ${pkgName}==${pkgVersion} -s ${pkgSelector} --clientdir ${clientDir} -e ${toxEnv} -v"
        )
    } else{
        bat(
            label: "Running tests on Packages on DevPi",
            script: "${devpiExec} test --index ${devpiIndex} ${pkgName}==${pkgVersion} -s ${pkgSelector}  --clientdir ${clientDir} -e ${toxEnv} -v"
        )
    }
}

def getToxEnvName(args){
    try{
        def pythonVersion = args.pythonVersion.replace(".", "")
        return "py${pythonVersion}"
    } catch(e){
        return "py"
    }
}

def testDevpiPackage2(args=[:]){
    def agent = getAgent(args)
    def devpiExec = args.devpi['devpiExec'] ? args.devpi['devpiExec'] : "devpi"
    def devpiIndex = args.devpi.index
    def devpiServerUrl = args.devpi.server
    def credentialsId = args.devpi.credentialsId
    def clientDir = args['clientDir'] ? args['clientDir']: './devpi'
    def pkgName = args.package.name
    def pkgVersion = args.package.version
    def pkgSelector = args.package.selector
    def toxEnv = args.test.toxEnv
    def testSetup = args.test['setup'] ? args.test['setup'] : {}
    def testTeardown = args.test['teardown'] ? args.test['teardown'] : {}

    agent{
        testSetup()
        try{
            logIntoDevpiServer(devpiExec, devpiServerUrl, credentialsId, clientDir)
            runDevpiTest(devpiExec, devpiIndex, pkgName, pkgVersion, pkgSelector, clientDir, toxEnv)
        } catch(Exception e){
            echo 'Waiting 5 seconds'
            sleep 5;
            throw e;
        }finally {
            testTeardown()
        }
    }
}
return [
    testDevpiPackage: this.&testDevpiPackage2,
    removePackage: this.&removePackage,
    pushPackageToIndex: this.&pushPackageToIndex,
    upload: this.&upload
]