def getNodeLabel(agent){
    def label
    if (agent.containsKey("dockerfile")){
        return agent.dockerfile.label
    }
    return label
}
def getToxEnv(args){
    try{
        def pythonVersion = args.pythonVersion.replace(".", "")
        return "py${pythonVersion}"
    } catch(e){
        return "py"
    }
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
        def nodeLabel = getNodeLabel(args.agent)
        return { inner ->
            node(nodeLabel){
                ws{
                    checkout scm
                    def dockerImage
                    def dockerImageName = "${currentBuild.fullProjectName}_${getToxEnv(args)}".replaceAll("-", "_").replaceAll('/', "_").replaceAll(' ', "").toLowerCase()
                    lock("docker build-${env.NODE_NAME}"){
                        dockerImage = docker.build(dockerImageName, "-f ${args.agent.dockerfile.filename} ${args.agent.dockerfile.additionalBuildArgs} .")
                    }
                    dockerImage.inside(){
                        inner()
                    }
                }
            }
        }
    }
    error('Invalid agent type, expect [dockerfile,label]')
}

def testPkg(args = [:]){
    def tox = args['toxExec'] ? args['toxExec']: "tox"
    def setup = args['testSetup'] ? args['testSetup']: {
        checkout scm
        unstash "${args.stash}"
    }
    def teardown =  args['testTeardown'] ? args['testTeardown']: {}

    def agentRunner = getAgent(args)
    agentRunner {
        setup()
        try{
            findFiles(glob: args.glob).each{
                def toxCommand = "${tox} --installpkg ${it.path} -e ${getToxEnv(args)}"
                if(isUnix()){
                    sh(label: "Testing tox version", script: "${tox} --version")
//                     toxCommand = toxCommand + " --workdir /tmp/tox"
                    sh(label: "Running Tox", script: toxCommand)
                } else{
                    bat(label: "Testing tox version", script: "${tox} --version")
                    toxCommand = toxCommand + " --workdir %TEMP%\\tox"
                    bat(label: "Running Tox", script: toxCommand)
                }
            }
        } finally{
            teardown()
        }
    }
}

return [
    testPkg: this.&testPkg
]