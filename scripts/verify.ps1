#Requires -Version 5.1
<#
.SYNOPSIS
  Reproducible local verification for the WBS 3.10 demonstrator.

.DESCRIPTION
  Runs tests, CLI checks, manifest rendering and client-side validation, a live
  HTTP smoke test, and optional container/Trivy checks. Writes a Markdown record
  to evidence/local/local-verification.md.

  This proves the repository state only. It is not HDE pipeline, registry,
  Argo CD or owner-acceptance evidence.
#>
[CmdletBinding()]
param(
    [int]$Port = 18080,
    [switch]$SkipDocker
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$evidenceDir = Join-Path $root 'evidence\local'
$reportPath = Join-Path $evidenceDir 'local-verification.md'
$renderedPath = Join-Path $env:TEMP 'binarybitops-rendered.yaml'
$serverOut = Join-Path $env:TEMP 'binarybitops-server-stdout.log'
$serverErr = Join-Path $env:TEMP 'binarybitops-server-stderr.log'
$checks = New-Object System.Collections.ArrayList

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
if (Test-Path $reportPath) { Remove-Item -Force $reportPath }

function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail = '', [string]$State = '')
    if (-not $State) { $State = if ($Passed) { 'PASS' } else { 'FAIL' } }
    [void]$checks.Add([pscustomobject]@{ Name = $Name; Passed = $Passed; State = $State; Detail = $Detail })
}

function Invoke-Step {
    param([string]$Name, [scriptblock]$Command)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $Command 2>&1 | Out-String
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($null -eq $code) { $code = 0 }
    return [pscustomobject]@{ Name = $Name; Output = $output.Trim(); ExitCode = $code }
}

function Add-Report {
    param([string]$Title, [string]$Body)
    Add-Content -Path $reportPath -Value "## $Title`n"
    Add-Content -Path $reportPath -Value '```text'
    Add-Content -Path $reportPath -Value $Body
    Add-Content -Path $reportPath -Value '```'
    Add-Content -Path $reportPath -Value ''
}

$started = (Get-Date).ToUniversalTime()
$branch = (git -C $root rev-parse --abbrev-ref HEAD 2>$null)
$commit = (git -C $root rev-parse HEAD 2>$null)
$shortCommit = (git -C $root rev-parse --short HEAD 2>$null)
$dirty = (git -C $root status --porcelain 2>$null)

$pythonVersion = (python --version 2>&1 | Out-String).Trim()
$kubectlVersion = (kubectl version --client 2>&1 | Select-Object -First 1 | Out-String).Trim()
$gitVersion = (git --version 2>&1 | Out-String).Trim()

$header = @"
# WBS 3.10 local verification

- Timestamp (UTC): $($started.ToString('yyyy-MM-ddTHH:mm:ssZ'))
- Host: $env:COMPUTERNAME
- OS: $([System.Environment]::OSVersion.VersionString)
- Repository: $root
- Branch: $branch
- Commit: $commit
- Working tree dirty: $(if ($dirty) { 'yes' } else { 'no' })
- Python: $pythonVersion
- Git: $gitVersion
- kubectl: $kubectlVersion

> This evidence covers the local repository only. It does not prove an approved
> PR, a Tekton PipelineRun, a registry digest, Argo CD sync, Vault injection in
> the cluster, observability ingestion or owner acceptance. Do not use it as HDE
> delivery evidence.
"@
Set-Content -Path $reportPath -Value $header -Encoding UTF8
Add-Content -Path $reportPath -Value ''

# 1. Tests -------------------------------------------------------------------
$tests = Invoke-Step 'tests' { cmd /c "python -m unittest discover -s tests -t . -v 2>&1" }
Add-Check 'Unit, HTTP, secret and manifest tests' ($tests.ExitCode -eq 0) "exit $($tests.ExitCode)"
Add-Report 'Test suite' $tests.Output

# 2. CLI ---------------------------------------------------------------------
$cli = Invoke-Step 'cli' { cmd /c "python binarybitops.py 2>&1" }
$cliOk = ($cli.ExitCode -eq 0) -and ($cli.Output -match 'GitHub authoritative repository') -and ($cli.Output -match '12 AND 10 = 8, OR = 14, XOR = 6')
Add-Check 'CLI model view' $cliOk "exit $($cli.ExitCode)"
Add-Report 'CLI output' $cli.Output

# 3. Manifests ---------------------------------------------------------------
$env:GIT_SHA = $shortCommit
$env:BUILD_DATE = $started.ToString('yyyy-MM-ddTHH:mm:ssZ')
$env:DEMO_ENV = 'local-verify'
$env:DEMO_RELEASE = 'wbs-3.10'

$render = Invoke-Step 'render' {
    $yamlText = (kubectl kustomize (Join-Path $root 'deploy\overlays\nonprod')) -join "`n"
    [System.IO.File]::WriteAllText($renderedPath, $yamlText, (New-Object System.Text.UTF8Encoding($false)))
    Get-Content $renderedPath
}
$renderOk = ($render.ExitCode -eq 0) -and (Test-Path $renderedPath)
Add-Check 'Render non-production overlay' $renderOk "exit $($render.ExitCode)"
Add-Report 'Rendered overlay (kubectl kustomize)' ($render.Output.Substring(0, [Math]::Min(6000, $render.Output.Length)) + "`n... (truncated)")

if ($renderOk) {
    $rendered = Get-Content $renderedPath -Raw
    $digestPinned = $rendered -match 'binarybitops-demo@sha256:[0-9a-f]{64}'
    $tagPlaceholder = $rendered -match 'binarybitops-demo:0\.1\.0'
    Add-Check 'Image reference present' ($digestPinned -or $tagPlaceholder) "digest pinned: $digestPinned; pre-release tag: $tagPlaceholder"
    Add-Check 'Restricted security context rendered' (($rendered -match 'readOnlyRootFilesystem: true') -and ($rendered -match 'runAsNonRoot: true')) ''
    Add-Check 'Default-deny NetworkPolicy rendered' ($rendered -match 'kind: NetworkPolicy') ''

    $kubeconform = Get-Command kubeconform -ErrorAction SilentlyContinue
    if (-not $kubeconform) {
        $localKubeconform = Join-Path $root 'tools\kubeconform.exe'
        if (Test-Path $localKubeconform) { $kubeconform = Get-Item $localKubeconform }
    }
    if ($kubeconform) {
        $kubeconformPath = if ($kubeconform -is [System.Management.Automation.CommandInfo]) { $kubeconform.Source } else { $kubeconform.FullName }
        $validate = Invoke-Step 'kubeconform' {
            & $kubeconformPath -strict -summary -ignore-missing-schemas $renderedPath
        }
        Add-Check 'Kubernetes schema validation (kubeconform)' ($validate.ExitCode -eq 0) "exit $($validate.ExitCode)"
        Add-Report 'Kubernetes schema validation (kubeconform)' $validate.Output
    } else {
        Add-Check 'Kubernetes schema validation (kubeconform)' $true 'kubeconform not installed; covered by manifest tests and PR workflow' 'SKIP'
    }
}

# 4. Live HTTP smoke test ----------------------------------------------------
$serverProcess = $null
try {
    $env:PORT = "$Port"
    $env:GIT_SHA = $shortCommit
    if (Test-Path $serverOut) { Remove-Item -Force $serverOut }
    if (Test-Path $serverErr) { Remove-Item -Force $serverErr }

    $serverProcess = Start-Process -FilePath 'python' -ArgumentList '-m', 'binarybitops.server' `
        -WorkingDirectory $root -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr

    $baseUri = "http://127.0.0.1:$Port"
    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri "$baseUri/healthz" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    Add-Check 'Server starts and answers /healthz' $ready ''

    if ($ready) {
        $health = Invoke-WebRequest -Uri "$baseUri/healthz" -UseBasicParsing -TimeoutSec 5
        $readyz = Invoke-WebRequest -Uri "$baseUri/readyz" -UseBasicParsing -TimeoutSec 5
        $version = Invoke-WebRequest -Uri "$baseUri/version" -UseBasicParsing -TimeoutSec 5
        $status = Invoke-WebRequest -Uri "$baseUri/api/status" -UseBasicParsing -TimeoutSec 5
        $bitops = Invoke-WebRequest -Uri "$baseUri/api/bitops?left=12&right=10" -UseBasicParsing -TimeoutSec 5
        $index = Invoke-WebRequest -Uri "$baseUri/" -UseBasicParsing -TimeoutSec 5
        $metrics = Invoke-WebRequest -Uri "$baseUri/metrics" -UseBasicParsing -TimeoutSec 5

        $bitopsJson = $bitops.Content | ConvertFrom-Json
        Add-Check 'Bitwise API result (12,10 -> 8,14,6)' `
            (($bitopsJson.and -eq 8) -and ($bitopsJson.or -eq 14) -and ($bitopsJson.xor -eq 6)) `
            "and=$($bitopsJson.and) or=$($bitopsJson.or) xor=$($bitopsJson.xor)"

        $statusJson = $status.Content | ConvertFrom-Json
        Add-Check 'Status reports scope boundary' ($statusJson.scope -match 'not the Binary Bit Ops/Nexus application') ''
        Add-Check 'Version reports local commit' ($version.Content -match [regex]::Escape($shortCommit)) ''

        Add-Check 'HTML banner rendered' ($index.Content -match 'DEMONSTRATOR ONLY') ''
        Add-Check 'Metrics expose build info and counters' `
            (($metrics.Content -match 'binarybitops_build_info') -and ($metrics.Content -match 'binarybitops_http_requests_total')) ''

        $smoke = @"
GET /healthz              -> $($health.StatusCode) $($health.Content)
GET /readyz               -> $($readyz.StatusCode) $($readyz.Content)
GET /version              -> $($version.StatusCode)
$($version.Content)
GET /api/status           -> $($status.StatusCode)
$($status.Content)
GET /api/bitops?left=12&right=10 -> $($bitops.StatusCode)
$($bitops.Content)
GET / -> $($index.StatusCode); banner present: $($index.Content -match 'DEMONSTRATOR ONLY')
GET /metrics -> $($metrics.StatusCode); first lines:
$(($metrics.Content -split "`n" | Select-Object -First 12) -join "`n")
"@
        Add-Report 'HTTP smoke test' $smoke
    }
} finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
        $serverProcess.WaitForExit(5000) | Out-Null
    }
    if (Test-Path $serverErr) {
        $errors = Get-Content $serverErr -Raw
        if ($errors) { Add-Report 'Server stderr' $errors }
    }
}

# 5. Trivy (optional) --------------------------------------------------------
$trivy = Get-Command trivy -ErrorAction SilentlyContinue
if (-not $trivy) {
    $localTrivy = Join-Path $root 'tools\trivy.exe'
    if (Test-Path $localTrivy) { $trivy = Get-Item $localTrivy }
}
if ($trivy) {
    $trivyPath = if ($trivy -is [System.Management.Automation.CommandInfo]) { $trivy.Source } else { $trivy.FullName }
    $trivyVersion = Invoke-Step 'trivy-version' { & $trivyPath --version }
    $scan = Invoke-Step 'trivy' {
        & $trivyPath fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --exit-code 0 --no-progress `
            --ignorefile (Join-Path $root '.trivyignore.yaml') --skip-dirs .git --skip-dirs evidence --skip-dirs tools $root
    }
    Add-Check 'Trivy local scan executed' ($scan.ExitCode -eq 0) "exit $($scan.ExitCode); findings may still be listed"
    Add-Report 'Trivy version' $trivyVersion.Output
    Add-Report 'Trivy filesystem scan (HIGH/CRITICAL)' $scan.Output
} else {
    Add-Check 'Trivy local scan' $true 'trivy not installed in this workspace' 'SKIP'
    Add-Report 'Trivy' 'Skipped: trivy is not installed on this host.'
}

# 6. Container (optional) ----------------------------------------------------
$dockerAvailable = $false
if (-not $SkipDocker -and (Get-Command docker -ErrorAction SilentlyContinue)) {
    $dockerInfo = Invoke-Step 'docker-info' { docker info --format '{{.ServerVersion}}' }
    $dockerAvailable = ($dockerInfo.ExitCode -eq 0)
}
if ($dockerAvailable) {
    $imageTag = "binarybitops-demo:verify-$shortCommit"
    $build = Invoke-Step 'docker-build' {
        docker build -t $imageTag --build-arg "GIT_SHA=$shortCommit" --build-arg "BUILD_DATE=$($started.ToString('yyyy-MM-ddTHH:mm:ssZ'))" $root
    }
    Add-Check 'Container image build' ($build.ExitCode -eq 0) "exit $($build.ExitCode)"
    Add-Report 'Docker build' $build.Output

    if ($build.ExitCode -eq 0) {
        docker run -d --name bbops-verify -p 18081:8080 -e DEMO_ENV=container-verify $imageTag | Out-Null
        $containerReady = $false
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            try {
                $response = Invoke-WebRequest -Uri 'http://127.0.0.1:18081/healthz' -UseBasicParsing -TimeoutSec 2
                if ($response.StatusCode -eq 200) { $containerReady = $true; break }
            } catch { Start-Sleep -Milliseconds 250 }
        }
        $inspect = Invoke-Step 'docker-inspect' { docker inspect --format '{{.Config.User}} {{.Config.Healthcheck.Test}}' $imageTag }
        $smoke = Invoke-Step 'container-smoke' { Invoke-WebRequest -Uri 'http://127.0.0.1:18081/api/status' -UseBasicParsing -TimeoutSec 5 | Select-Object -ExpandProperty Content }
        Add-Check 'Container runs and is reachable' $containerReady ''
        Add-Check 'Container runtime user is non-root' (($inspect.Output -match '10001')) $inspect.Output
        Add-Report 'Container inspection and smoke test' ($inspect.Output + "`n" + $smoke.Output)
        docker rm -f bbops-verify | Out-Null
    }
} else {
    Add-Check 'Container image build' $true 'Docker daemon not reachable in this workspace' 'SKIP'
    Add-Report 'Docker' 'Skipped: no reachable Docker daemon. Build the image in the HDE Tekton pipeline or on a host with Docker.'
}

# 7. Secret patterns ---------------------------------------------------------
$secretPattern = 'AKIA[0-9A-Z]{16}|-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}'
$hits = Get-ChildItem -Path $root -Recurse -File |
    Where-Object { $_.FullName -notmatch '\\\.git\\|\\evidence\\local\\|\\tools\\' -and $_.Length -lt 2000000 } |
    Select-String -Pattern $secretPattern -ErrorAction SilentlyContinue
Add-Check 'No credential-shaped strings in tracked paths' ($null -eq $hits) ''
if ($hits) { Add-Report 'Secret pattern hits' ($hits | Out-String) }

# 8. Summary -----------------------------------------------------------------
$failed = @($checks | Where-Object { $_.State -eq 'FAIL' })
$skipped = @($checks | Where-Object { $_.State -eq 'SKIP' })
$rows = $checks | ForEach-Object {
    "| $($_.Name) | $($_.State) | $($_.Detail) |"
}
$summary = @"
## Summary

| Check | State | Detail |
| --- | --- | --- |
$($rows -join "`n")

- Checks: $($checks.Count)
- Passed: $(@($checks | Where-Object { $_.State -eq 'PASS' }).Count)
- Failed: $($failed.Count)
- Skipped (tool unavailable): $($skipped.Count)
- Docker used: $dockerAvailable

Local verification is **not** HDE acceptance evidence. The outstanding items are
listed in `evidence/wbs-3.10-record.md` and `docs/task-3.10-status.md`.
"@
Add-Content -Path $reportPath -Value $summary

Write-Output "Wrote $reportPath"
Write-Output "Passed $(@($checks | Where-Object { $_.State -eq 'PASS' }).Count) of $($checks.Count) checks; failed $($failed.Count); skipped $($skipped.Count)."
if ($failed.Count -gt 0) {
    $failed | ForEach-Object { Write-Output "  - $($_.Name): $($_.Detail)" }
    exit 1
}
exit 0
