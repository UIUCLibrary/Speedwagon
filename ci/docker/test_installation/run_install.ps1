$MSIFILES = Get-ChildItem -Path c:\dist -Filter *.msi
# Only continue if one and only one msi file is located
try
{
    # If there are no files found, then there was a failure during the building of the docker image
    if($MSIFILES.Count -eq 0)
    {
        throw "No Files found in the docker image container."
    }

    # If there are more than one files found, then a the environment had multiple msi files during docker build
    # and needs to be properly cleaned up first
    if($MSIFILES.Count -ne 1){

        foreach ($MSIFILE in $MSIFILES)
        {
            Write-Host "Found  $MSIFILE"
        }

        throw "Found more than one msi file."
    }

}
catch
{
    Write-Host "Unable to install msi file. Quiting"
    exit 1
}

New-Item -ItemType Directory -Force -Path C:\logs | Out-Null
# At this point there should only be a single msi file to run
try{
    foreach ($MSIFILE in $MSIFILES) {
        $DataStamp = get-date -Format yyyyMMddTHHmmss
        $logFileShort = '{0}-{1}.log' -f $MSIFILE.Name, $DataStamp
        $MSIArguments = @(
            "/i"
            ('"{0}"' -f $MSIFILE.fullname)
            "/qn"
            "/norestart"
            "/L*v!"
            "c:/logs/$logFileShort"
        )

        Write-Host "Installing $MSIFILE to Docker container."

        $install_process = Start-Process "msiexec.exe" -ArgumentList $MSIArguments -Wait -WindowStyle Hidden -PassThru

        Write-Host "Done installing with exit code $($install_process.ExitCode). Complete install log can be found c:/logs/$logFileShort"
        if ($install_process.ExitCode -ne 0)
        {
            throw "Problem running msiexec."
        }
    }
}
catch
{
    Write-Host "Failed to install"
    exit 1
}



