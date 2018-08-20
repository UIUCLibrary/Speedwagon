$MSIFILES = Get-ChildItem -Path . -Filter *.msi

# Only continue if one and only one msi file is located

# If there are no files found, then there was a failure during the building of the docker image
if($MSIFILES.Count -eq 0)
{
    Write-Host "No Files found in the docker image container. Quiting"
    exit 1
}

# If there are more than one files found, then a the environment had multiple msi files during docker build
# and needs to be properly cleaned up first
if($MSIFILES.Count -ne 1){
    Write-Host "Found more than one msi file. Quiting"
    foreach ($MSIFILE in $MSIFILES)
    {
        Write-Host "  $MSIFILE"
    }
    Write-Host "Quiting"
    exit 1
}

# At this point there should only be a single msi file to run
foreach ($MSIFILE in $MSIFILES) {
    echo "Running msiexec on $MSIFILE"
    & msiexec /i $MSIFILE /q /lp dockerinstall.log
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Exit code is $LASTEXITCODE."
        exit $Write-Host
    }
}

