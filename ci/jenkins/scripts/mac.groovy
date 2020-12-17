def build_mac_package(args = [:]){
    def pythonPath =  args['pythonPath'] ? args['pythonPath']: "python3"
    def outPath = "dist"

    node(args['label']){
        checkout scm
        try{
            sh(
                label: "Building wheel",
                script: "${pythonPath} -m pip wheel . --no-deps -w ${outPath}"
            )
            stash includes: args['stash']['includes'], name: args['stash']['name']
        } finally{
            cleanWs(
                deleteDirs: true,
                patterns: [
                    [pattern: '**/__pycache__/', type: 'INCLUDE'],
                    [pattern: outPath, type: 'INCLUDE'],
                ]
            )
        }

    }
}
def test_mac_package(args = [:]){
    def pythonPath =  args['pythonPath'] ? args['pythonPath']: "python3"
    def glob = args['glob']
    node(args['label']){
        try{
            checkout scm
            unstash args['stash']
            sh(
                label:"Installing tox",
                script: """${pythonPath} -m venv venv
                           venv/bin/python -m pip install pip --upgrade
                           venv/bin/python -m pip install wheel
                           venv/bin/python -m pip install tox
                           """
            )
            files = findFiles(glob: glob)
            if( files.size() == 0){
                error "No files located in ${glob}"
            }
            files.each{
                sh(
                    label: "Testing ${it}",
                    script: "venv/bin/tox --installpkg=${it.path} -e py -vv --recreate"
                )
            }
        } finally {
            cleanWs(
                deleteDirs: true,
                patterns: [
                    [pattern: '**/__pycache__/', type: 'INCLUDE'],
                    [pattern: '.tox/', type: 'INCLUDE'],
                    [pattern: '*.egg-info/', type: 'INCLUDE'],
                    [pattern: 'venv/', type: 'INCLUDE'],
                ]
            )
        }
    }
}

return this

