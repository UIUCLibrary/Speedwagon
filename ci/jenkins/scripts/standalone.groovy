
def generate_cpack_arguments(BuildWix=true, BuildNSIS=true, BuildZip=true){
    script{
        def cpack_generators = []
        def item_selected = false
        def default_generator = "WIX"

        if(BuildWix){
            cpack_generators << "WIX"
            item_selected = true
        }

        if(BuildNSIS){
            cpack_generators << "NSIS"
            item_selected = true
        }
        if(BuildZip){
            cpack_generators << "ZIP"
            item_selected = true
        }
        if(item_selected == false){
            cpack_generators << default_generator
        }

        return "${cpack_generators.join(";")}"
    }

}


def build_standalone(args=[:]){
    def buildDir =   args['buildDir'] ? args['buildDir']: "cmake_build"
    def pythonExec = args['pythonExec'] ? args['pythonExec']: powershell(script: '(Get-Command python).path', returnStdout: true).trim()
    def packaging_msi  = args.packageFormat['msi'] ? args.packageFormat['msi']: false
    def packaging_nsis = args.packageFormat['nsis'] ? args.packageFormat['nsis']: false
    def packaging_zip  = args.packageFormat['zipFile'] ? args.packageFormat['zipFile']: false
    stage("Building Standalone"){
//         bat "where cmake"

        bat(label: "Creating expected directories",
            script: """if not exist "${buildDir}" mkdir ${buildDir}
                       if not exist "logs" mkdir logs
                       if not exist "logs\\ctest" mkdir logs\\ctest
                       if not exist "temp" mkdir temp
                       """
           )
        script{
            cmakeBuild(
                buildDir: buildDir,
                cmakeArgs: """-DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=c:\\wheels
                              -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv
                              -DSPEEDWAGON_DOC_PDF=${WORKSPACE}/dist/docs/speedwagon.pdf
                              """,
                generator: 'Ninja',
                installation: 'InSearchPath',
                steps: [
                    [withCmake: true]
                ]
            )
        }
    }
    stage("Testing standalone"){

        ctest(
            arguments: "-T test -C Release -j ${NUMBER_OF_PROCESSORS}",
            installation: 'InSearchPath',
            workingDir: buildDir
            )
    }
    stage("Packaging standalone"){
        script{
            def cpack_generators = generate_cpack_arguments(packaging_msi, packaging_nsis, packaging_zip)
            cpack(
                arguments: "-C Release -G ${cpack_generators} --config ${${buildDir}}/CPackConfig.cmake -B ${WORKSPACE}/dist -V",
                installation: 'InSearchPath'
            )
        }
    }
}
return this
