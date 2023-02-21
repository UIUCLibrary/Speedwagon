param (
    [Parameter(Mandatory=$true)] $PackageName,
    [Parameter(Mandatory=$true)] $PackageSummary,
    [Parameter(Mandatory=$true)] $PackageVersion,
    [Parameter(Mandatory=$true)] $PackageMaintainer,
    [Parameter(Mandatory=$true)] $Wheel,
    [Parameter(Mandatory=$true)] $DependenciesDir,
    [Parameter(Mandatory=$true)] $DocsDir,
    $OutputFolder='packages'
)

function SanitizeVersion {
    param (
        $Version
    )
    if (-Not $Version -match '(a|b|dev|post|rc[0-9]+)$'){
        return $Version
    }
    $REGEX = '(?:((\.)?))((?<postfix>b|a|dev|rc|post)(?<postVersionNumber>[0-9]+))$'
    if ($Version -match $REGEX) {
        $POSTFIX = switch($Matches.postfix) {
            b {'beta'; break}
            a {'alpha'; break}
            dev {'dev'; break}
            rc {'rc'; break}
            post {'post'; break}
            Default {
                'No match'
            }
        }
        $ENDING = '-' + $POSTFIX + $Matches.postVersionNumber
        $SANTIZED = $("$Version" -replace $REGEX, $ENDING)


    }
    else
    {
        Write-Error "$Version is an invalid version number"
        throw "invalid version number"
        $SANTIZED= $Version
    }
    return $SANTIZED
}

$ErrorActionPreference = 'Stop';

$PackageVersion = SanitizeVersion -Version $PackageVersion
$PackageFolder = Join-Path -Path $OutputFolder -ChildPath $PackageName
$DependenciesOutputFolder = Join-Path -Path $PackageFolder -ChildPath 'deps'
$DocsOutputFolder = Join-Path -Path $PackageFolder -ChildPath 'docs'
$NuspecFile = Join-Path -Path $PackageFolder -ChildPath "$($PackageName).nuspec"


Write-Host "Creating new Chocolatey package workspace"
choco new $PackageName packageversion=$PackageVersion PythonSummary="$PackageSummary" InstallerFile=$Wheel MaintainerName="$PackageMaintainer" -t pythonscript --outputdirectory packages

Get-Content -Path $NuspecFile

Write-Host "Adding data to Chocolatey package workspace"
New-Item -ItemType File -Path $(Join-Path -Path $PackageFolder -ChildPath $Wheel) -Force | Out-Null
Move-Item -Path "$Wheel"  -Destination $(Join-Path -Path $PackageFolder -ChildPath $Wheel)  -Force | Out-Null
Copy-Item -Path "$DependenciesDir"  -Destination $DependenciesOutputFolder -Force -Recurse

Write-Host "Vendoring the following package wheels"
Get-ChildItem $DependenciesOutputFolder | Format-Table -Property Name, Length

Copy-Item -Path "$DocsDir"  -Destination $DocsOutputFolder -Force -Recurse

Write-Host "Packaging Chocolatey package"
choco pack $NuspecFile --outputdirectory $OutputFolder

Write-Host "Checking chocolatey package metadata"
choco info --pre -s $OutputFolder $PackageName