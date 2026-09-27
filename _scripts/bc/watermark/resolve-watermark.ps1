[CmdletBinding()]
param(
    [string]$RepositoryPath = ".",
    [switch]$Canonical
)

$ErrorActionPreference = "Stop"

function Invoke-GhText([string[]]$Arguments) {
    $output = & gh @Arguments 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
        throw "GitHub CLI command failed: gh $($Arguments -join ' ')"
    }
    return $output.Trim()
}

function Get-GitHubRemote([string]$Path) {
    $remote = (& git -C $Path config --get remote.origin.url 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($remote)) {
        throw "No origin remote found in: $Path"
    }

    if ($remote -match 'github\.com[:/]([^/]+)/([^/#]+?)(?:\.git)?$') {
        return [PSCustomObject]@{ Owner = $Matches[1]; Repository = $Matches[2] }
    }

    throw "origin is not a GitHub repository: $remote"
}

function Get-OrganizationDisplayName([string]$Owner, [string]$RepositoryRoot) {
    $configPath = Join-Path $RepositoryRoot ".blockconnect-watermark.json"
    if (Test-Path -LiteralPath $configPath) {
        $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        if (-not [string]::IsNullOrWhiteSpace($config.organizationDisplayName)) {
            return $config.organizationDisplayName.Trim()
        }
    }

    $githubName = Invoke-GhText @("api", "orgs/$Owner", "--jq", ".name")
    # Keep the stable GitHub owner spelling unless the organization publishes a
    # genuinely different brand, such as NDBlockConnect -> BlockConnect.
    $normalizedOwner = ($Owner -replace '[^A-Za-z0-9]', '').ToLowerInvariant()
    $normalizedName = ($githubName -replace '[^A-Za-z0-9]', '').ToLowerInvariant()
    if ($normalizedName -eq $normalizedOwner) {
        return $Owner
    }
    return $githubName
}

function Add-RandomSpacing([string]$Value) {
    $builder = [System.Text.StringBuilder]::new()
    $random = [System.Random]::new()
    $insertedSpacing = $false

    for ($index = 0; $index -lt $Value.Length; $index++) {
        $character = $Value[$index]
        [void]$builder.Append($character)

        # Keep canonical separator whitespace readable. Elsewhere, randomly
        # inject 1-3 ASCII spaces after roughly one third of characters.
        $next = if ($index + 1 -lt $Value.Length) { $Value[$index + 1] } else { [char]0 }
        if ($character -ne ' ' -and $next -ne ' ' -and $next -ne [char]0 -and $random.Next(0, 3) -eq 0) {
            [void]$builder.Append(' ' * $random.Next(1, 4))
            $insertedSpacing = $true
        }
    }

    if (-not $insertedSpacing -and $Value.Length -gt 1) {
        $splitAt = $random.Next(1, $Value.Length)
        return $Value.Insert($splitAt, ' ' * $random.Next(1, 4))
    }

    return $builder.ToString()
}

$root = (Resolve-Path -LiteralPath $RepositoryPath).Path
$remote = Get-GitHubRemote $root
$ownerType = Invoke-GhText @("api", "repos/$($remote.Owner)/$($remote.Repository)", "--jq", ".owner.type")

if ($ownerType -eq "Organization") {
    $login = Invoke-GhText @("api", "user", "--jq", ".login")
    $displayName = Get-OrganizationDisplayName $remote.Owner $root
    $watermark = "GitHub@$($remote.Owner) | $displayName@$login"
} elseif ($ownerType -eq "User") {
    $watermark = "GitHub@$($remote.Owner)"
} else {
    throw "Unsupported GitHub owner type: $ownerType"
}

if ($Canonical) {
    $watermark
} else {
    Add-RandomSpacing $watermark
}
