def sanitize_chocolatey_version(version){
    script{
        def dot_to_slash_pattern = '(?<=\\d)\\.?(?=(dev|b|a|rc)(\\d)?)'

//        def rc_pattern = "(?<=\d(\.?))rc((?=\d)?)"
        def dashed_version = version.replaceFirst(dot_to_slash_pattern, "-")

        def beta_pattern = "(?<=\\d(\\.?))b((?=\\d)?)"
        if(dashed_version.matches(beta_pattern)){
            return dashed_version.replaceFirst(beta_pattern, "beta")
        }

        def alpha_pattern = "(?<=\\d(\\.?))a((?=\\d)?)"
        if(dashed_version.matches(alpha_pattern)){
            return dashed_version.replaceFirst(alpha_pattern, "alpha")
        }
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
    powershell(
        label: "Installing Chocolatey Package",
        script:"""\$process = start-process -NoNewWindow -PassThru -FilePath C:\\ProgramData\\chocolatey\\bin\\choco.exe -ArgumentList '${packageName} -y -dv  --version=${version} -s \'${source}]\' --no-progress', "-my" -Wait ;
                  if ( \$process.ExitCode -nq 0) { throw "Installing packages with Chocolatey - Failed with exit code (\$process.ExitCode)" }
                  """
    )
}

return this
