
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
    // Parse packageFormat args
    def cpack_generators_args = ''
    if (args.containsKey('packageFormat')){
        def packageFormat = args['packageFormat']

        def packaging_msi = false
        if(packageFormat.containsKey('msi')){
            packaging_msi = args.packageFormat['msi']
            packageFormat.remove('msi')
        }

        def packaging_nsis = false
        if(packageFormat.containsKey('nsis')){
            packaging_nsis = packageFormat['nsis']
            packageFormat.remove('nsis')
        }

        def packaging_zip = false
        if(packageFormat.containsKey('zipFile')){
            packaging_zip = packageFormat['zipFile']
            packageFormat.remove('zipFile')
        }
        cpack_generators_args = "-G ${generate_cpack_arguments(packaging_msi, packaging_nsis, packaging_zip)}"

        if(packageFormat.size() > 0){
            error "invalid arguments in packageFormat ${packageFormat.keySet()}"
        }
        args.remove('packageFormat')
    }

    // Parse testing args
    def ctestLogsFilePath = "${WORKSPACE}\\logs\\ctest.log"
    if (args.containsKey('testing')){
        def testingArgs = args['testing']
        if(testingArgs.containsKey('ctestLogsFilePath')){
            ctestLogsFilePath = testingArgs['ctestLogsFilePath']
            testingArgs.remove('ctestLogsFilePath')
        }
        if(testingArgs.size() > 0){
            error "invalid arguments in testing ${testingArgs.keySet()}"
        }
        args.remove('testing')
    }

    // Parse package args
    def pythonPackageVersion
    if (args.containsKey('package')){
        def packageArgs = args['package']
        if(packageArgs.containsKey('version')){
            pythonPackageVersion = packageArgs['version']
            packageArgs.remove('version')
        } else {
            error "Missing required argument in package: version"
        }
        if(packageArgs.size() > 0){
            error "invalid arguments in package ${packageArgs.keySet()}"
        }
        args.remove('package')
    } else {
        error "Missing required argument: package"
    }

    // Parse top level args
    def buildDir = "cmake_build"
    if (args['buildDir']) {
        buildDir = args['buildDir']
        args.remove('buildDir')
    }

    def venvPath = "${WORKSPACE}\\standalone_venv"
    if (args.containsKey('venvPath')){
        venvPath = args['venvPath']
        args.remove('venvPath')
    }

    def documentationPdf = "${WORKSPACE}/dist/docs/speedwagon.pdf"
    if (args.containsKey('documentationPdf')){
        documentationPdf = args['documentationPdf']
        args.remove('documentationPdf')
    }
    if(args.size() > 0){
        error "invalid arguments ${args.keySet()}"
    }

    stage("Building Standalone"){
        bat(label: "Creating expected directories",
            script: """if not exist "${buildDir}" mkdir ${buildDir}
                       if not exist "logs" mkdir logs
                       if not exist "logs\\ctest" mkdir logs\\ctest
                       if not exist "temp" mkdir temp
                       """
           )
        script{
            try{
                def cmakeArgs = "-DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=c:\\wheels -DSPEEDWAGON_VENV_PATH=${venvPath} -DSPEEDWAGON_DOC_PDF=${documentationPdf} -Wdev"
                if(args['package']){
                    cmakeArgs = cmakeArgs + " -DSpeedwagon_VERSION:STRING=${pythonPackageVersion}"
                    def packageVersion = pythonPackageVersion =~ /(?:a|b|rc|dev)?\d+/
                    def package_version  = pythonPackageVersion.split("\\.")
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
//                 archiveArtifacts(allowEmptyArchive: true, artifacts: "${buildDir}/CMakeFiles/**")
//                 archiveArtifacts(artifacts: "${buildDir}/CMakeFiles/*.log")
                throw e
            }
        }
    }
    stage('Testing Standalone'){
        try{
            dir(buildDir){
                withEnv(['QT_QPA_PLATFORM=offscreen']) {
                    bat "ctest --output-on-failure --no-compress-output -T test -C Release -j ${NUMBER_OF_PROCESSORS} --output-log ${ctestLogsFilePath}"
                }
            }
        }
        catch(e){
            bat "${venvPath}\\Scripts\\pip.exe list --verbose"
            throw e
        }
    }
    stage("Packaging Standalone"){
        script{
            try{
                bat "cpack -C Release ${cpack_generators_args} --config ${buildDir}\\CPackConfig.cmake -B ${WORKSPACE}/dist -V"
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
