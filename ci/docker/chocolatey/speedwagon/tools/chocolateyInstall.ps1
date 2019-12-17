# Custom value: [[CustomValue]]
$ErrorActionPreference = 'Stop'; # stop on all errors

[[AutomaticPackageNotesInstaller]]
$packageName  = '[[PackageName]]'
$toolsDir     = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$fileLocation = Join-Path $toolsDir '[[InstallerFile]]'

$packageArgs = @{
  packageName   = $packageName
  file          = $fileLocation
  fileType      = '[[InstallerType]]' #only one of these: exe, msi, msu

  #MSI
  silentArgs    = "/qn /norestart /l*v `"$env:TEMP\chocolatey\$($packageName)\$($packageName).MsiInstall.log`""
  validExitCodes= @(0, 3010, 1641)
  #OTHERS
  #silentArgs   ='[[SilentArgs]]' # /s /S /q /Q /quiet /silent /SILENT /VERYSILENT -s - try any of these to get the silent installer
  #validExitCodes= @(0) #please insert other valid exit codes here
}

Install-ChocolateyInstallPackage @packageArgs
Install-BinFile -Name speedwagon -Path 'C:\Program Files\Speedwagon\bin\python.exe' -Command '"-m speedwagon"'