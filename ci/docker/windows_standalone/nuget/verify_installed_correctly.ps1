function Verify-Installed {
    param (
            $FileName
        )

    if ((Get-Command $FileName -ErrorAction SilentlyContinue) -eq $null)
    {
       Write-Error "Unable to find $FileName in your PATH"
    }
    else {
        Write-Host "Found $FileName"
    }
}
Write-Host 'Locating expected commands on path'
Verify-Installed candle.exe
Verify-Installed light.exe
Verify-Installed lit.exe
Verify-Installed dark.exe
Verify-Installed heat.exe
Verify-Installed insignia.exe
Verify-Installed melt.exe
Verify-Installed torch.exe
Verify-Installed smoke.exe
Verify-Installed pyro.exe
Verify-Installed WixCop.exe
Verify-Installed retina.exe
Verify-Installed lux.exe
Verify-Installed nit.exe
Write-Host 'All Done'