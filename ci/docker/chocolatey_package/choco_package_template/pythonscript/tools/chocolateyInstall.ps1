

# Custom value: [[CustomValue]]
$ErrorActionPreference = 'Stop'; # stop on all errors

[[AutomaticPackageNotesInstaller]]
$packageName  = '[[PackageName]]'
$toolsDir     = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$installDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"

$fileLocation = Join-Path $toolsDir '[[InstallerFile]]'
$dependenciesLocation = Join-Path $toolsDir dist\deps
$packageSourceUrl =  '[[PackageSourceUrl]]'
$PYTHON = "C:\Python311\python.exe"
$requirementSpecifier = "$($fileLocation)`[QT`]"
Write-Host "Creating Python virtualenv at $installDir\venv"
& "$PYTHON" -m venv $installDir\venv
& "$installDir\venv\Scripts\python.exe" -m pip install pip --upgrade --no-compile
& "$installDir\venv\Scripts\python.exe" -m pip install  "$requirementSpecifier" --find-link "$dependenciesLocation"

$files = get-childitem $installDir -include *.exe -recurse
foreach ($file in $files) {
  #generate an ignore file
  New-Item "$file.ignore" -type file -force | Out-Null
}
Install-ChocolateyShortcut `
  -ShortcutFilePath "$Env:ProgramData\Microsoft\Windows\Start Menu\Programs\$packageName\$packageName.lnk" `
  -TargetPath "$installDir\venv\Scripts\$packageName.exe" `
  -WorkingDirectory "C:\" `
  -Description "Collection of tools and workflows for DS"

Install-ChocolateyShortcut `
  -ShortcutFilePath "$Env:ProgramData\Microsoft\Windows\Start Menu\Programs\$packageName\Manual.lnk" `
  -TargetPath "$installDir\documentation\$packageName.pdf" `
  -WorkingDirectory "C:\" `
  -Description "Speedwagon Manual"

Install-BinFile -Name $packageName -Path "$installDir\venv\Scripts\$packageName.exe"
