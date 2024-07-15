param (
    $packageRepo = "https://chocolatey.org/api/v2",
    [Parameter(Mandatory = $false)]
    [string]
    $ChocolateyVersion = $env:chocolateyVersion
)
if ($ChocolateyVersion) {
    $url = ($packageRepo.Trim('/'), "$ChocolateyVersion") -join '/'
    Write-Host "$url"
}
else
{
    $searchUrl = ($packageRepo.Trim('/'), 'Packages()?$filter=(Id%20eq%20%27chocolatey%27)%20and%20IsLatestVersion') -join '/'
    $downloader = new-object System.Net.WebClient
    $defaultCreds = [System.Net.CredentialCache]::DefaultCredentials
    $downloader.Credentials = $defaultCreds
    [xml]$results = $downloader.DownloadString($searchUrl)
    Write-Host $results.feed.entry.content.src
}
