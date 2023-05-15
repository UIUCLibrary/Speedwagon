def sanitize_chocolatey_version(version){
    script{
        def dot_to_slash_pattern = '(?<=\\d)\\.?(?=(dev|b|a|rc|post)(\\d)?)'

//        def rc_pattern = "(?<=\d(\.?))rc((?=\d)?)"
        def dashed_version = version.replaceFirst(dot_to_slash_pattern, "-")
        if ( version =~ /dev/ ) {
            return version.replace('.dev', "-dev")
        }
        dashed_version = version.replaceFirst('\\.post', ".")
        def dev_pattern = '(?<=\\d(\\.?))dev((?=\\d)?)'
        if(dashed_version.matches(dev_pattern)){
            echo "Discovered a development version"
            return dashed_version.replaceFirst(dev_pattern, "-dev")
        }

        if(version.matches('(([0-9]+(([.])?))+)b([0-9]+)')){
            echo 'Discovered a beta version'
            return dashed_version.replaceFirst('([.]?b)', "-beta")
        }

        def alpha_pattern = '(?<=\\d(\\.?))a((?=\\d)?)'
        if(dashed_version.matches(alpha_pattern)){
            echo "Discovered an Alpha version"
            return dashed_version.replaceFirst(alpha_pattern, "alpha")
        }
        echo "Discovered no special version info"
        return dashed_version
    }
}

def make_chocolatey_distribution(install_file, packageversion, dest){
    script{
        def maintainername = "Henry Borchers"
        def sanitized_packageversion=sanitize_chocolatey_version(packageversion)
        def packageSourceUrl="https://github.com/UIUCLibrary/Speedwagon"
        def installerType='msi'
        def installer = findFiles(glob: "${install_file}")[0]
        def install_file_name = installer.name
        def install_file_path = "${pwd()}\\${installer.path}"
        dir("${dest}"){
            powershell(
                label: "Making chocolatey Package Configuration",
                script: "choco new speedwagon packageversion=${sanitized_packageversion} maintainername='\"${maintainername}\"' packageSourceUrl='${packageSourceUrl}' InstallerType='${installerType}' InstallerFile='${install_file_name}'"
            )
            powershell(
                label: "Adding ${install_file} to package",
                script: "Copy-Item \"${install_file_path}\" -Destination speedwagon\\tools\\"
            )

            powershell(
                label: "Creating Package",
                script: "cd speedwagon; choco pack"
            )
        }
    }
}


def deploy_to_chocolatey(ChocolateyServer){
    script{
        def pkgs = []
        findFiles(glob: "packages/*.nupkg").each{
            pkgs << it.path
        }
        def deployment_options = input(
            message: 'Chocolatey server',
            parameters: [
                credentials(
                    credentialType: 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl',
                    defaultValue: 'NEXUS_NUGET_API_KEY',
                    description: 'Nuget API key for Chocolatey',
                    name: 'CHOCO_REPO_KEY',
                    required: true
                ),
                choice(
                    choices: pkgs,
                    description: 'Package to use',
                    name: 'NUPKG'
                ),
            ]
        )
        withCredentials([string(credentialsId: deployment_options['CHOCO_REPO_KEY'], variable: 'KEY')]) {
            bat(
                label: "Deploying ${deployment_options['NUPKG']} to Chocolatey",
                script: "choco push ${deployment_options['NUPKG']} -s ${ChocolateyServer} -k %KEY%"
            )
        }
    }
}
def install_chocolatey_package(args=[:]){
    def packageName = args['name']
    def version = args['version']
    def source = args['source']
    def retries = args['retries'] ? args['retries'] : 1
    retry(retries){
        try{
            powershell(
                label: "Installing Chocolatey Package",
                script: """\$ErrorActionPreference=\"Stop\"
                            try
                            {
                               \$process = start-process -NoNewWindow -PassThru -Wait -FilePath C:\\ProgramData\\chocolatey\\bin\\choco.exe -ArgumentList \"install ${packageName} -y -dv  --version=${version} -s \'${source}\' --no-progress\"
                               if ( \$process.ExitCode -ne 0){
                                    throw 'This is a failure message'
                               }
                            }
                            catch
                            {
                                Write-Error "Chocolatey Failed to install package: \$Error"
                                exit 1
                            }
                            """,
            )
        } catch(ex){
            sleep 5
            throw ex

        }
    }
}
def reinstall_chocolatey_package(args=[:]){
    def packageName = args['name']
    def version = args['version']
    def source = args['source']
    def retries = args['retries'] ? args['retries'] : 1
    retry(retries){
        try{
            powershell(
                label: "Installing Chocolatey Package",
                script: """\$ErrorActionPreference=\"Stop\"
                            try
                            {
                               \$process = start-process -NoNewWindow -PassThru -Wait -FilePath C:\\ProgramData\\chocolatey\\bin\\choco.exe -ArgumentList \"install ${packageName} -y -dv  --version=${version} -s \'${source}\' --no-progress --force\"
                               if ( \$process.ExitCode -ne 0){
                                    throw 'This is a failure message'
                               }
                            }
                            catch
                            {
                                Write-Error "Chocolatey Failed to install package: \$Error"
                                exit 1
                            }
                            """,
            )
        } catch(ex){
            sleep 5
            throw ex

        }
    }
}

return this
