def buildSphinxDocumentation(args = [:]){
    def sourceDir = args.sourceDir
    def outputDir = args.outputDir
    def sphinxBuildCommand = "python -m sphinx -W --keep-going"

    if(args['builder'] != null){
        sphinxBuildCommand = sphinxBuildCommand + " -b ${args.builder}"
    }

    if(args['doctreeDir'] != null){
        sphinxBuildCommand = sphinxBuildCommand + " -d ${args.doctreeDir}"
    }

    if(args['writeWarningsToFile'] != null){
        sphinxBuildCommand = sphinxBuildCommand + " -w ${args.writeWarningsToFile}"
    }

    sphinxBuildCommand = sphinxBuildCommand + " ${sourceDir}"
    sphinxBuildCommand = sphinxBuildCommand + " ${outputDir}"
    if(isUnix()){
        sh(
            label: 'Building Documentation with Sphinx',
            script: sphinxBuildCommand
            )
    } else {
        bat(label: 'Building Documentation with Sphinx',
            script: sphinxBuildCommand
        )
    }
}

return this