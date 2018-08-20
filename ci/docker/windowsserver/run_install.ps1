﻿$MSIFILES = Get-ChildItem -Path . -Filter *.msi
if($MSIFILES.Count -ne 1){
    Write-Host "Found more than one msi file. Quiting"
    foreach ($MSIFILE in $MSIFILES)
    {
        echo "Found $MSIFILE"
    }
    exit 1
}

foreach ($MSIFILE in $MSIFILES) {
    echo "$MSIFILE"
    msiexec /i $MSIFILE /q /lp dockerinstall.log
}

