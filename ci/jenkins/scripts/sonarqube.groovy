// def runSonarScanner(args = [:]){
//     def projectVersion = args.projectVersion
//     def buildString = args.buildString
//     def isPullRequest = args['pullRequest'] ? true : false
//
//     if (isPullRequest == true){
//         def pullRequestKey = args.pullRequest.source
//         def pullRequestBase = args.pullRequest.destination
//         sh(
//             label: "Running Sonar Scanner",
//             script:"sonar-scanner -Dsonar.projectVersion=${projectVersion} -Dsonar.buildString=\"${buildString}\" -Dsonar.pullrequest.key=${pullRequestKey} -Dsonar.pullrequest.base=${pullRequestBase}"
//             )
//     } else {
//         def branchName =  args['branchName'] ? args['branchName']: env.BRANCH_NAME
//         sh(
//             label: "Running Sonar Scanner",
//             script: "sonar-scanner -Dsonar.projectVersion=${projectVersion} -Dsonar.buildString=\"${buildString}\" -Dsonar.branch.name=${branchName}"
//             )
//     }
// }

def get_sonarqube_unresolved_issues(report_task_file){
    script{

        def props = readProperties  file: '.scannerwork/report-task.txt'
        def response = httpRequest url : props['serverUrl'] + "/api/issues/search?componentKeys=" + props['projectKey'] + "&resolved=no"
        def outstandingIssues = readJSON text: response.content
        return outstandingIssues
    }
}


def submitToSonarcloud(args = [:]){
    def artifactStash = args['artifactStash']
    def isPullRequest = args['pullRequest'] ? true: false
    def buildString = args['buildString'] ? args['buildString']: env.BUILD_TAG
    def installationName = args.sonarqube.installationName
    def credentialsId = args.sonarqube.credentialsId
    script{
        try{
            withSonarQubeEnv(installationName: installationName, credentialsId: credentialsId) {
                def projectVersion = args.package.version

                if (isPullRequest == true){
                    def pullRequestKey = args.pullRequest.source
                    def pullRequestBase = args.pullRequest.destination
                    sh(
                        label: "Running Sonar Scanner",
                        script:"sonar-scanner -Dsonar.projectVersion=${projectVersion} -Dsonar.buildString=\"${buildString}\" -Dsonar.pullrequest.key=${pullRequestKey} -Dsonar.pullrequest.base=${pullRequestBase}"
                        )
                } else {
                    def branchName =  args['branchName'] ? args['branchName']: env.BRANCH_NAME
                    sh(
                        label: "Running Sonar Scanner",
                        script: "sonar-scanner -Dsonar.projectVersion=${projectVersion} -Dsonar.buildString=\"${buildString}\" -Dsonar.branch.name=${branchName}"
                        )
                }
            }

            timeout(60){
                def sonarqube_result = waitForQualityGate(abortPipeline: false)
                if (sonarqube_result.status != 'OK') {
                    unstable "SonarQube quality gate: ${sonarqube_result.status}"
                }
                def outstandingIssues = get_sonarqube_unresolved_issues(".scannerwork/report-task.txt")
                writeJSON( file: 'reports/sonar-report.json', json: outstandingIssues)
                if(artifactStash != null){
                    stash(includes: "reports/sonar-report.json", name: artifactStash)
                }
            }
        } finally {
            cleanWs(
                deleteDirs: true,
                patterns: [
                        [pattern: '.scannerwork/', type: 'INCLUDE']
                    ]
            )

        }
    }
}

return this
