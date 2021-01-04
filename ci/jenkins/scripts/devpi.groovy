def upload(args = [:]){
    def credentialsId = args['credentialsId']
    def clientDir = args['clientDir'] ? args['clientDir']: './devpi'
    def index = args['index']
    def devpiExec = args['devpiExec'] ? args['devpiExec']: "devpi"
    withEnv([
            "DEVPI_INDEX=${index}",
            "DEVPI_SERVER=${args['server']}",
            "CLIENT_DIR=${clientDir}",
            "DEVPI=${devpiExec}"
        ]) {
        withCredentials([usernamePassword(
                            credentialsId: credentialsId,
                            passwordVariable: 'DEVPI_PASSWORD',
                            usernameVariable: 'DEVPI_USERNAME'
                        )
                            ])
        {
            if(isUnix()){
                sh(label: "Logging into DevPi",
                   script: '''$DEVPI use $DEVPI_SERVER --clientdir $CLIENT_DIR
                              $DEVPI login $DEVPI_USERNAME --password=$DEVPI_PASSWORD --clientdir $CLIENT_DIR
                              '''
                   )
           } else {
               bat(label: "Logging into DevPi",
                   script: '''%DEVPI% use %DEVPI_SERVER% --clientdir %CLIENT_DIR%
                              %DEVPI% login %DEVPI_USERNAME% --password%$DEVPI_PASSWORD% --clientdir %CLIENT_DIR%
                              '''
                   )
           }
           if(isUnix()){
                sh(label: "Uploading to DevPi Staging",
                   script: '''$DEVPI use /$DEVPI_USERNAME/$DEVPI_INDEX --clientdir $CLIENT_DIR
                              $DEVPI upload --from-dir dist --clientdir $CLIENT_DIR
                              '''
                )
           } else {
               bat(label: "Uploading to DevPi Staging",
                   script: '''%DEVPI% use /%DEVPI_USERNAME%/%DEVPI_INDEX% --clientdir %CLIENT_DIR%
                              %DEVPI% upload --from-dir dist --clientdir %CLIENT_DIR%
                              '''
                   )
           }
       }
    }
}

def testDevpiPackage(args = [:]){
    def clientDir = args['clientDir'] ? args['clientDir']: './devpi'
    def devpiExec = args['devpiExec'] ? args['devpiExec']: "devpi"
    def devpiIndex  = args['devpiIndex']
    def pkgName  = args['pkgName']
    def pkgVersion = args['pkgVersion']
    def pkgSelector = args['pkgSelector']
    def toxEnv = args['toxEnv']
    withEnv([
            "DEVPI_INDEX=${devpiIndex}",
            "DEVPI_SERVER=${args['server']}",
            "CLIENT_DIR=${clientDir}",
            "DEVPI=${devpiExec}"
        ]) {
        withCredentials([usernamePassword(
                                credentialsId: args['credentialsId'],
                                passwordVariable: 'DEVPI_PASSWORD',
                                usernameVariable: 'DEVPI_USERNAME'
                            )
                        ])
            {
            if(isUnix()){
                sh(label: "Logging into DevPi",
                   script: '''$DEVPI use $DEVPI_SERVER --clientdir $CLIENT_DIR
                              $DEVPI login $DEVPI_USERNAME --password=$DEVPI_PASSWORD --clientdir $CLIENT_DIR
                              $DEVPI use $DEVPI_INDEX --clientdir $CLIENT_DIR
                              '''
                   )

            } else {
                bat(label: "Logging into DevPi Staging",
                   script: '''%DEVPI% use %DEVPI_SERVER% --clientdir %CLIENT_DIR%
                              %DEVPI% login %DEVPI_USERNAME% --password=%DEVPI_PASSWORD% --clientdir %CLIENT_DIR%
                              %DEVPI% use %DEVPI_INDEX% --clientdir %CLIENT_DIR%
                              '''
                   )

            }
        }
        if(isUnix()){
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

return this
