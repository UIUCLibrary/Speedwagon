def locateSonarReportTasksFile = { Map args = [:] ->
    def targetDirs = args?.targetDirs ?: ['.sonar', '.scannerwork']
    def fileName = args?.reportFileName ?: 'report-task.txt'

    def foundFiles = targetDirs.collectMany { dir ->
        findFiles(glob: "${dir}/${fileName}")
    }

    if (foundFiles.size() == 0) {
        error "${fileName} not found"
    }

    if (foundFiles.size() > 1) {
        error 'Found multiple report-task.txt files'
    }

    if (foundFiles.size() == 1) {
        def file = foundFiles[0]
        echo "Found ${file.path}"
        return file.path
    }
}

def getSonarqubeUnresolvedIssues = { Map args = [:] ->
    if (!args.containsKey('tasksReportFile')) {
        error "Missing required arguments! 'tasksReportFile' is required."
    }
    def tasksReportFile = args.tasksReportFile
    if(! fileExists(tasksReportFile)){
        error "Could not find ${tasksReportFile}"
    }

    def props = readProperties  file: tasksReportFile
    if(! props['serverUrl'] || ! props['projectKey']){
        error "Could not find serverUrl or projectKey in ${tasksReportFile}"
    }
    def response = httpRequest url : props['serverUrl'] + '/api/issues/search?componentKeys=' + props['projectKey'] + '&resolved=no'
    def outstandingIssues = readJSON text: response.content
    return outstandingIssues
}

def submitToSonarQubeServer = { Map args = [:] ->
    ['credentialsId', 'sonarInstallationName', 'sonarScannerExec'].each { k ->
        if (!args.containsKey(k)) {
            error "Missing required argument: '${k}'"
        }
    }
    def sonarArgs = args?.sonarArgs ?: ''
    def credentialsId = args.credentialsId
    def sonarInstallationName = args.sonarInstallationName
    def sonarScannerExec = args.sonarScannerExec
    withSonarQubeEnv(installationName: sonarInstallationName, credentialsId: credentialsId) {
       withCredentials([string(credentialsId: credentialsId, variable: 'token')]) {
           sh(
               label: 'Running Sonar Scanner',
               script: "${sonarScannerExec} -t \$token ${sonarArgs}"
           )
       }
    }
}

return [
    locateSonarReportTasksFile: locateSonarReportTasksFile,
    getSonarqubeUnresolvedIssues: getSonarqubeUnresolvedIssues,
    submitToSonarQubeServer: submitToSonarQubeServer
]