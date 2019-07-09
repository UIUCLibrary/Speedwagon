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


# At this point there should only be a single msi file to run
try{
    foreach ($MSIFILE in $MSIFILES) {
        $InstallBlock = {
            param
            (
                [string]$currentLocation,
                [string]$msiFile,
                [string]$logFileShortName

            )

            $MSIArguments = @(
            "/i"
            ('"{0}"' -f $msiFile)
            "/qn"
            "/norestart"
            "/L*v!"
            "$currentLocation/$logFileShortName"
            )

            New-Item  "$currentLocation/$logFileShortName"

            $install_process = Start-Process "msiexec.exe" -ArgumentList $MSIArguments -Wait -WindowStyle Hidden -PassThru

            Write-Host "Done installing with exit code $($install_process.ExitCode). Complete install log can be found at $logFileShortName"
            if ($install_process.ExitCode -ne 0)
            {
                throw "Problem running msiexec."
            }
        }
        $DataStamp = get-date -Format yyyyMMddTHHmmss
        $logFileShort = '{0}-{1}.log' -f $MSIFILE.Name, $DataStamp

        $InstallMSIArgs = @(
            "$PWD",
            "$($msiFile.fullname)",
            "$logFileShort"
        )

        $job = Start-Job -ScriptBlock $InstallBlock -ArgumentList $InstallMSIArgs  -Name "Running msiexec"

        while(Get-Job -State "Running")
        {
            if(Test-Path $logFileShort)
            {
                Get-Content "$logFileShort" -Tail 1
            }
            Start-Sleep 10
        }
        Get-Job | Receive-Job

        if(Test-Path c:\logs){
            dir c:\logs
            Move-Item -Path $logFileShort -Destination c:\logs
        }

    }
}
catch
{
    Write-Host "Failed to install"
    exit 1
}



