vswhere.exe

$installationPath = & vswhere.exe -prerelease -latest -property installationPath
$project_folder = & Get-Location

echo "Visual Studio path = $installationPath"
echo "Project Folder     = $project_folder"

if ($installationPath -and (test-path "$installationPath\Common7\Tools\vsdevcmd.bat")) {
  & "${env:COMSPEC}" /s /c "`"$installationPath\Common7\Tools\vsdevcmd.bat`" -no_logo -host_arch=amd64 && set" | foreach-object {
    $name, $value = $_ -split '=', 2
    set-content env:\"$name" $value
  }
}
else
{
    echo "Unable to set Visual studio"
    Get-ChildItem Env: | Format-Table -Wrap

    EXIT 1
}
nuget install windows_build\packages.config -OutputDirectory build\nugetpackages

Start-Process -NoNewWindow -FilePath msbuild.exe -ArgumentList "windows_build\release.pyproj /nologo /t:msi /p:ProjectRoot=$project_folder" -Wait
