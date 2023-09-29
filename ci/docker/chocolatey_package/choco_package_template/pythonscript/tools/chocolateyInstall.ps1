

# Custom value: [[CustomValue]]
$ErrorActionPreference = 'Stop'; # stop on all errors

[[AutomaticPackageNotesInstaller]]
$packageName  = '[[PackageName]]'
$toolsDir     = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$installDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$venvDir      = "$installDir\venv"
$requirements = "$toolsDir\dist\requirements.txt"

$fileLocation = Join-Path $toolsDir '[[InstallerFile]]'
$dependenciesLocation = Join-Path $toolsDir dist\deps
$requirementsLocation = Join-Path $toolsDir dist\requirements
$packageSourceUrl =  '[[PackageSourceUrl]]'
#$PYTHON = "C:\Windows\py.exe -3.11"
$requirementSpecifier = "$($fileLocation)`[QT`]"
If(test-path -PathType container $venvDir){
  Write-Host "Removing existing Python virtual environment"
  Remove-Tree $venvDir
}

Write-Host "Creating Python virtualenv at $venvDir"
& "C:\Windows\py.exe" -3.11 -m venv $venvDir --upgrade-deps

Write-Host "Installing Speedwagon"
& "$venvDir\Scripts\python.exe" -m pip install --no-deps --no-cache-dir --find-link $dependenciesLocation $requirementSpecifier -r $requirements

$files = get-childitem $installDir -include *.exe -recurse
foreach ($file in $files) {
  #generate an ignore file
  New-Item "$file.ignore" -type file -force | Out-Null
}
Install-ChocolateyShortcut `
  -ShortcutFilePath "$Env:ProgramData\Microsoft\Windows\Start Menu\Programs\$packageName\$packageName.lnk" `
  -TargetPath "$installDir\venv\Scripts\$packageName.exe" `
  -WorkingDirectory "C:\" `
  -IconLocation "$installDir\venv\Lib\site-packages\speedwagon\favicon.ico" `
  -Description "Collection of tools and workflows for DS"

Install-ChocolateyShortcut `
  -ShortcutFilePath "$Env:ProgramData\Microsoft\Windows\Start Menu\Programs\$packageName\Manual.lnk" `
  -TargetPath "$installDir\documentation\$packageName.pdf" `
  -WorkingDirectory "C:\" `
  -Description "Speedwagon Manual"

Install-BinFile -Name $packageName -Path "$installDir\venv\Scripts\$packageName.exe"
