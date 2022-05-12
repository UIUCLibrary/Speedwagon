

# Custom value: [[CustomValue]]
$ErrorActionPreference = 'Stop'; # stop on all errors

[[AutomaticPackageNotesInstaller]]
$packageName  = '[[PackageName]]'
$toolsDir     = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$installDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"

$fileLocation = Join-Path $toolsDir '[[InstallerFile]]'
$depDendenciesLocation = Join-Path $toolsDir dist\deps
$packageSourceUrl =  '[[PackageSourceUrl]]'
$PYTHON = "$(Join-Path $(Get-AppInstallLocation('python')) 'python.exe')"

Write-Host "Creating Python virtualenv at $installDir\venv"
& "$PYTHON" -m venv $installDir\venv
& "$installDir\venv\Scripts\python.exe" -m pip install pip --upgrade --no-compile
& "$installDir\venv\Scripts\python.exe" -m pip install  '$fileLocation`[QT`]' --find-link "$depDendenciesLocation"

$files = get-childitem $installDir -include *.exe -recurse
foreach ($file in $files) {
  #generate an ignore file
  New-Item "$file.ignore" -type file -force | Out-Null
}
Install-ChocolateyShortcut `
  -ShortcutFilePath "$Env:ProgramData\Microsoft\Windows\Start Menu\Programs\$packageName\$packageName.lnk" `
  -TargetPath "$installDir\venv\Scripts\$packageName.exe" `
  -WorkingDirectory "C:\" `
  -Description "This is the description"

Install-ChocolateyShortcut `
  -ShortcutFilePath "$Env:ProgramData\Microsoft\Windows\Start Menu\Programs\$packageName\Manual.lnk" `
  -TargetPath "$installDir\documentation\$packageName.pdf" `
  -WorkingDirectory "C:\" `
  -Description "This is the description"

Install-BinFile -Name $packageName -Path "$installDir\venv\Scripts\$packageName.exe"
