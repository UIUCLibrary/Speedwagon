
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
//     def pythonExec = args['pythonExec'] ? args['pythonExec']: powershell(script: '(Get-Command python).path', returnStdout: true).trim()
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
            try{

                def cmakeArgs = "-DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=c:\\wheels -DSPEEDWAGON_VENV_PATH=${WORKSPACE}/standalone_venv -DSPEEDWAGON_DOC_PDF=${WORKSPACE}/dist/docs/speedwagon.pdf -Wdev"
                if(args['package']){
                    cmakeArgs = cmakeArgs + " -DSpeedwagon_VERSION:STRING=${args.package['version']}"
                    def packageVersion = args.package['version'] =~ /(?:a|b|rc|dev)?\d+/
                    def package_version  = args.package['version'].split("\\.")
                    if(package_version.size() >= 1){
                        cmakeArgs = cmakeArgs + " -DCMAKE_PROJECT_VERSION_MAJOR=${packageVersion[0]}"
                        cmakeArgs = cmakeArgs + " -DCPACK_PACKAGE_VERSION_MAJOR=${packageVersion[0]}"
                    }
                    if(package_version.size() >= 2){
                        cmakeArgs = cmakeArgs + " -DCMAKE_PROJECT_VERSION_MINOR=${packageVersion[1]}"
                        cmakeArgs = cmakeArgs + " -DCPACK_PACKAGE_VERSION_MINOR=${packageVersion[1]}"
                    }
                    if(package_version.size() >= 3){
                        cmakeArgs = cmakeArgs + " -DCMAKE_PROJECT_VERSION_PATCH=${packageVersion[2]}"
                        cmakeArgs = cmakeArgs + " -DCPACK_PACKAGE_VERSION_PATCH=${packageVersion[2]}"
                    }
                    if(package_version.size() >= 4){
                        cmakeArgs = cmakeArgs + " -DCMAKE_PROJECT_VERSION_TWEAK=${packageVersion[3]}"
                        cmakeArgs = cmakeArgs + " -DCPACK_PACKAGE_VERSION_TWEAK=${packageVersion[3]}"
                    }
                }
                bat(label: "Configuring CMake",
                    script: "cmake -S ${WORKSPACE} -B ${buildDir} -G Ninja ${cmakeArgs}"
                )
                bat(label: "Building with CMake",
                    script: "cmake --build ${buildDir}"
                )
            } catch(e){
                if(!isUnix()){
                    bat "tree ${buildDir} /A /F"
                }
                archiveArtifacts(allowEmptyArchive: true, artifacts: "${buildDir}/CMakeCache.txt")
                archiveArtifacts(allowEmptyArchive: true, artifacts: "${buildDir}/CMakeFiles/**")
//                 archiveArtifacts(artifacts: "${buildDir}/CMakeFiles/*.log")
                throw e
            }
        }
    }
    stage("Testing Standalone"){
        dir(buildDir){
            withEnv(['QT_QPA_PLATFORM=offscreen']) {
                bat "ctest --output-on-failure --no-compress-output -T test -C Release -j ${NUMBER_OF_PROCESSORS}"
            }
        }
    }
    stage("Packaging Standalone"){
        script{
            try{
                def cpack_generators = generate_cpack_arguments(packaging_msi, packaging_nsis, packaging_zip)
                bat "cpack -C Release -G ${cpack_generators} --config ${buildDir}\\CPackConfig.cmake -B ${WORKSPACE}/dist -V"
            } catch(e){
                findFiles(glob: "dist/_CPack_Packages/**/*.log").each{ logFile ->
                    echo(readFile(logFile.path))
                }
                archiveArtifacts( allowEmptyArchive: true, artifacts: "${buildDir}/**/*.wxs")
                throw e
            }
        }
    }
}

def testInstall(glob){
    def msi_file = findFiles(glob: glob)[0].path
    powershell(label:"Installing msi file",
               script: """New-Item -ItemType Directory -Force -Path logs
                          Write-Host \"Installing ${msi_file}\"
                          msiexec /i ${msi_file} /qn /norestart /L*v! logs\\msiexec.log
                          """
              )
}

return this
