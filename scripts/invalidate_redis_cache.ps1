[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Catalog", "QuestionBank", "CourseManifest", "SelectorSnapshots", "AdaptiveSnapshots", "ExactKey", "Pattern")]
    [string]$Scope,

    [string]$BotId,

    [ValidateSet("faculties", "programs", "levels", "semesters", "courses")]
    [string]$CatalogBucket,

    [string[]]$CatalogParts = @(),

    [string]$CourseCode,
    [string]$UserId,
    [string]$ExactKey,
    [string]$Pattern,

    [string]$Namespace = "adarkwa-study-bot",
    [string]$PodTarget = "deployment/adarkwa-bot-webhook",

    [string]$SshUser = $(if ($env:ADARKWA_VPS_SSH_USER) { $env:ADARKWA_VPS_SSH_USER } else { "williamsjohnson25200109" }),
    [string]$SshHost = $(if ($env:ADARKWA_VPS_SSH_HOST) { $env:ADARKWA_VPS_SSH_HOST } else { "34.2.60.203" }),
    [string]$KeyPath = $(if ($env:ADARKWA_VPS_SSH_KEY_PATH) { $env:ADARKWA_VPS_SSH_KEY_PATH } else { "C:\Users\Kevin\.ssh\id_ed25519" }),

    [switch]$AllowBroadDelete,
    [switch]$ListOnly,
    [switch]$RestartDeployments,

    [string[]]$Deployments = @(
        "adarkwa-bot-webhook",
        "adarkwa-bot-worker",
        "adarkwa-bot-admin"
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Value {
    param(
        [string]$Name,
        [object]$Value
    )

    if ($null -eq $Value) {
        throw "Missing required parameter: $Name"
    }

    if ($Value -is [string] -and [string]::IsNullOrWhiteSpace($Value)) {
        throw "Missing required parameter: $Name"
    }

    if ($Value -isnot [string] -and $Value -is [System.Collections.IEnumerable]) {
        if (@($Value).Count -eq 0) {
            throw "Missing required parameter: $Name"
        }
    }
}

function Assert-SafeShellValue {
    param(
        [string]$Name,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "$Name must not be empty."
    }

    if ($Value -notmatch '^[A-Za-z0-9._:/=@+-]+$') {
        throw "$Name contains unsafe shell characters: $Value"
    }
}

function Add-KeySpec {
    param(
        [System.Collections.ArrayList]$Specs,
        [string]$Mode,
        [string]$Value
    )

    [void]$Specs.Add([ordered]@{
        mode  = $Mode
        value = $Value
    })
}

function New-WildcardKey {
    param(
        [string[]]$Parts
    )

    return ($Parts -join ":")
}

$specs = New-Object System.Collections.ArrayList

switch ($Scope) {
    "Catalog" {
        Require-Value "BotId" $BotId
        Require-Value "CatalogBucket" $CatalogBucket

        $expectedPartsByBucket = @{
            faculties = 0
            programs  = 1
            levels    = 1
            semesters = 2
            courses   = 4
        }

        $expectedParts = $expectedPartsByBucket[$CatalogBucket]
        $providedParts = @($CatalogParts)

        if ($providedParts.Count -gt $expectedParts) {
            throw "Catalog bucket '$CatalogBucket' accepts at most $expectedParts parts."
        }

        $catalogBase = New-WildcardKey -Parts @("catalog", "v2", $BotId, $CatalogBucket)
        $catalogProvidedSuffix = if ($providedParts.Count -gt 0) {
            ":" + ($providedParts -join ":")
        }
        else {
            ""
        }

        if ($providedParts.Count -eq $expectedParts) {
            Add-KeySpec -Specs $specs -Mode "key" -Value ($catalogBase + $catalogProvidedSuffix)
            break
        }

        $catalogWildcardSuffix = if (($expectedParts - $providedParts.Count) -gt 0) {
            ":" + ((1..($expectedParts - $providedParts.Count) | ForEach-Object { "*" }) -join ":")
        }
        else {
            ""
        }

        Add-KeySpec -Specs $specs -Mode "pattern" -Value ($catalogBase + $catalogProvidedSuffix + $catalogWildcardSuffix)
    }
    "QuestionBank" {
        if ($CourseCode) {
            Add-KeySpec -Specs $specs -Mode "key" -Value "question-bank:$CourseCode"
        }
        else {
            Add-KeySpec -Specs $specs -Mode "pattern" -Value "question-bank:*"
        }
    }
    "CourseManifest" {
        $botPart = if ($BotId) { $BotId } else { "*" }
        $coursePart = if ($CourseCode) { $CourseCode } else { "*" }
        $value = "course-question-manifest:${botPart}:${coursePart}"
        $mode = if ($botPart -eq "*" -or $coursePart -eq "*") { "pattern" } else { "key" }
        Add-KeySpec -Specs $specs -Mode $mode -Value $value
    }
    "SelectorSnapshots" {
        $botPart = if ($BotId) { $BotId } else { "*" }
        $userPart = if ($UserId) { $UserId } else { "*" }
        $coursePart = if ($CourseCode) { $CourseCode } else { "*" }
        $value = "selector-snapshot:${botPart}:${userPart}:${coursePart}"
        $mode = if ($botPart -eq "*" -or $userPart -eq "*" -or $coursePart -eq "*") { "pattern" } else { "key" }
        Add-KeySpec -Specs $specs -Mode $mode -Value $value
    }
    "AdaptiveSnapshots" {
        $botPart = if ($BotId) { $BotId } else { "*" }
        $userPart = if ($UserId) { $UserId } else { "*" }
        $coursePart = if ($CourseCode) { $CourseCode } else { "*" }
        $value = "adaptive-snapshot:${botPart}:${userPart}:${coursePart}"
        $mode = if ($botPart -eq "*" -or $userPart -eq "*" -or $coursePart -eq "*") { "pattern" } else { "key" }
        Add-KeySpec -Specs $specs -Mode $mode -Value $value
    }
    "ExactKey" {
        Require-Value "ExactKey" $ExactKey
        Add-KeySpec -Specs $specs -Mode "key" -Value $ExactKey
    }
    "Pattern" {
        Require-Value "Pattern" $Pattern
        Add-KeySpec -Specs $specs -Mode "pattern" -Value $Pattern
    }
}

$broadSpecs = @(@($specs) | Where-Object {
    $_.mode -eq "pattern" -and $_.value -match '[*?]'
})

if ($broadSpecs.Count -gt 0 -and -not $AllowBroadDelete) {
    $patterns = ($broadSpecs | ForEach-Object { $_.value }) -join ", "
    throw "Broad deletion is blocked. Re-run with -AllowBroadDelete to use pattern-based invalidation: $patterns"
}

Assert-SafeShellValue -Name "Namespace" -Value $Namespace
Assert-SafeShellValue -Name "PodTarget" -Value $PodTarget
Assert-SafeShellValue -Name "SshUser" -Value $SshUser
Assert-SafeShellValue -Name "SshHost" -Value $SshHost

foreach ($deployment in $Deployments) {
    Assert-SafeShellValue -Name "Deployment" -Value $deployment
}

if (-not (Test-Path -LiteralPath $KeyPath)) {
    throw "SSH key file not found: $KeyPath"
}

$deleteKeys = -not $ListOnly
if ($deleteKeys) {
    $operation = "Invalidate Redis cache scope '$Scope'"
    $target = "$SshUser@$SshHost / $Namespace / $PodTarget"
    if (-not $PSCmdlet.ShouldProcess($target, $operation)) {
        $deleteKeys = $false
    }
}

$request = [ordered]@{
    scope   = $Scope
    specs   = @($specs)
    delete  = $deleteKeys
    preview = 200
}

$requestJson = $request | ConvertTo-Json -Depth 8 -Compress
$requestBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($requestJson))

$pythonScript = @"
import base64
import json
import os
import urllib.parse

import redis

request = json.loads(base64.b64decode("$requestBase64").decode("utf-8"))
client = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

matched = []
for spec in request["specs"]:
    if spec["mode"] == "key":
        if client.exists(spec["value"]):
            matched.append(spec["value"])
    elif spec["mode"] == "pattern":
        matched.extend(sorted(client.scan_iter(match=spec["value"])))

deduped = []
seen = set()
for key in matched:
    if key in seen:
        continue
    seen.add(key)
    deduped.append(key)

deleted = 0
if request["delete"] and deduped:
    deleted = int(client.delete(*deduped))

parsed = urllib.parse.urlparse(os.environ["REDIS_URL"])
result = {
    "scope": request["scope"],
    "delete_requested": bool(request["delete"]),
    "redis_endpoint": f"{parsed.hostname}:{parsed.port}{parsed.path}",
    "matched_key_count": len(deduped),
    "deleted_key_count": deleted,
    "preview_keys": deduped[: request.get("preview", 200)],
    "preview_truncated": len(deduped) > request.get("preview", 200),
    "specs": request["specs"],
}
print(json.dumps(result))
"@

$sshArgs = @(
    "-i", $KeyPath,
    "$SshUser@$SshHost",
    "kubectl exec -i -n $Namespace $PodTarget -- python -"
)

$resultJson = $pythonScript | & ssh @sshArgs
$result = $resultJson | ConvertFrom-Json
$resultSpecs = @($result.specs)
$resultPreviewKeys = @($result.preview_keys)

Write-Host ""
Write-Host "Redis cache operation summary"
Write-Host "Scope: $($result.scope)"
Write-Host "Mode: $(if ($result.delete_requested) { 'delete' } else { 'list-only' })"
Write-Host "Redis endpoint: $($result.redis_endpoint)"
Write-Host "Matched keys: $($result.matched_key_count)"
Write-Host "Deleted keys: $($result.deleted_key_count)"
Write-Host ""
Write-Host "Requested specs:"
foreach ($spec in $resultSpecs) {
    Write-Host "  [$($spec.mode)] $($spec.value)"
}

if ($resultPreviewKeys.Count -gt 0) {
    Write-Host ""
    Write-Host "Matched keys preview:"
    foreach ($key in $resultPreviewKeys) {
        Write-Host "  $key"
    }
    if ($result.preview_truncated) {
        Write-Host "  ..."
    }
}
else {
    Write-Host ""
    Write-Host "No matching Redis keys found."
}

if ($RestartDeployments) {
    if (-not $deleteKeys) {
        Write-Host ""
        Write-Host "Skipping deployment restart because this run did not delete keys."
    }
    elseif ($result.deleted_key_count -eq 0) {
        Write-Host ""
        Write-Host "Skipping deployment restart because no Redis keys were deleted."
    }
    else {
        $restartCommands = New-Object 'System.Collections.Generic.List[string]'
        foreach ($deployment in $Deployments) {
            $restartCommands.Add("kubectl rollout restart deployment/$deployment -n $Namespace") | Out-Null
        }
        foreach ($deployment in $Deployments) {
            $restartCommands.Add("kubectl rollout status deployment/$deployment -n $Namespace --timeout=300s") | Out-Null
        }

        Write-Host ""
        Write-Host "Restarting deployments and waiting for rollout..."
        & ssh -i $KeyPath "$SshUser@$SshHost" ($restartCommands -join " && ")
    }
}
