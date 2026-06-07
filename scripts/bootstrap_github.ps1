#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Bootstraps the full GitHub project structure for the ITS platform:
  labels -> milestones (M0-M6) -> task issues (50) -> epic issues (14, with task
  checklists) -> native sub-issue links (task under epic).

.DESCRIPTION
  Single source of truth is scripts/issues.manifest.json. Rich issue bodies are read
  from docs/issues/<KEY>.md (tasks) and docs/issues/epics/<EKEY>.md (epics). The script
  is IDEMPOTENT: it skips labels/milestones/issues that already exist (matched by name /
  title) and ignores already-linked sub-issues, so a partial run can be safely re-run.

.PREREQUISITES
  - gh CLI authenticated (gh auth status) with 'repo' scope.
  - Run from anywhere; paths are resolved relative to this script.

.EXAMPLE
  pwsh scripts/bootstrap_github.ps1
#>
[CmdletBinding()]
param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
$Manifest  = Join-Path $ScriptDir 'issues.manifest.json'
$IssuesDir = Join-Path $RepoRoot 'docs\issues'

if (-not (Test-Path $Manifest)) { throw "Manifest not found: $Manifest" }
$m = Get-Content $Manifest -Raw | ConvertFrom-Json
$Repo = $m.repo
Write-Host "Repo: $Repo" -ForegroundColor Cyan
if ($DryRun) { Write-Host "DRY RUN — no changes will be made." -ForegroundColor Yellow }

function Invoke-Gh {
  param([string[]]$GhArgs, [switch]$AllowFail)
  if ($DryRun) { Write-Host "  [dry-run] gh $($GhArgs -join ' ')" -ForegroundColor DarkGray; return $null }
  $out = & gh @GhArgs 2>&1
  if ($LASTEXITCODE -ne 0 -and -not $AllowFail) { throw "gh failed: gh $($GhArgs -join ' ')`n$out" }
  return $out
}

# ---------------------------------------------------------------- 1. Labels
Write-Host "`n== Labels ==" -ForegroundColor Green
foreach ($l in $m.labels) {
  Invoke-Gh @('label','create',$l.name,'-R',$Repo,'--color',$l.color,'--description',$l.description,'--force') -AllowFail | Out-Null
  Write-Host "  label: $($l.name)"
}

# ---------------------------------------------------------------- 2. Milestones
Write-Host "`n== Milestones ==" -ForegroundColor Green
$existingMs = @{}
$msJson = & gh api "repos/$Repo/milestones?state=all&per_page=100" 2>$null
if ($LASTEXITCODE -eq 0 -and $msJson) {
  foreach ($ms in ($msJson | ConvertFrom-Json)) { $existingMs[$ms.title] = $ms.number }
}
foreach ($ms in $m.milestones) {
  if ($existingMs.ContainsKey($ms.title)) {
    Write-Host "  exists: $($ms.title)"
  } else {
    Invoke-Gh @('api',"repos/$Repo/milestones",'-f',"title=$($ms.title)",'-f',"description=$($ms.description)") -AllowFail | Out-Null
    Write-Host "  created: $($ms.title)"
  }
}

# ---------------------------------------------------------------- helper: existing issues map (title -> {number,id})
function Get-IssueMap {
  $map = @{}
  $raw = & gh issue list -R $Repo --state all --limit 1000 --json number,title,id 2>$null
  if ($LASTEXITCODE -eq 0 -and $raw) {
    foreach ($i in ($raw | ConvertFrom-Json)) { $map[$i.title] = [pscustomobject]@{ number = $i.number; id = $i.id } }
  }
  return $map
}

function New-Issue {
  param([string]$Title, [string[]]$Labels, [string]$Milestone, [string]$BodyFile, [string]$FallbackBody)
  $existing = Get-IssueMap
  if ($existing.ContainsKey($Title)) { Write-Host "  exists: $Title (#$($existing[$Title].number))"; return }
  $args = @('issue','create','-R',$Repo,'--title',$Title)
  if ($Labels -and $Labels.Count -gt 0) { $args += @('--label', ($Labels -join ',')) }
  if ($Milestone) { $args += @('--milestone',$Milestone) }
  if ($BodyFile -and (Test-Path $BodyFile)) {
    $args += @('--body-file',$BodyFile)
  } else {
    $args += @('--body',$FallbackBody)
    Write-Host "  (no body file, using fallback) $Title" -ForegroundColor Yellow
  }
  Invoke-Gh $args | Out-Null
  Write-Host "  created: $Title"
}

# ---------------------------------------------------------------- 3. Task issues
Write-Host "`n== Task issues ==" -ForegroundColor Green
foreach ($t in $m.tasks) {
  $bf = Join-Path $IssuesDir "$($t.key).md"
  $fb = "Detailspezifikation: $($t.epic) / siehe docs/. Akzeptanzkriterien in docs/01-github-issues.md und dem zugehoerigen Fachdokument."
  New-Issue -Title $t.title -Labels $t.labels -Milestone $t.milestone -BodyFile $bf -FallbackBody $fb
}

# ---------------------------------------------------------------- 4. Epic issues (with task checklist)
Write-Host "`n== Epic issues ==" -ForegroundColor Green
$issueMap = Get-IssueMap
foreach ($e in $m.epics) {
  if ($issueMap.ContainsKey($e.title)) { Write-Host "  exists: $($e.title) (#$($issueMap[$e.title].number))"; continue }
  $epicBodyFile = Join-Path $IssuesDir "epics\$($e.key).md"
  $body = ""
  if (Test-Path $epicBodyFile) { $body = Get-Content $epicBodyFile -Raw }
  else { $body = "# $($e.title)`n`nSiehe $($e.doc). Milestone: $($e.milestone)." }
  # append checklist of this epic's tasks (fallback to native sub-issues)
  $body += "`n`n## Tasks (Sub-Issues)`n"
  foreach ($t in ($m.tasks | Where-Object { $_.epic -eq $e.key })) {
    if ($issueMap.ContainsKey($t.title)) {
      $body += "- [ ] #$($issueMap[$t.title].number) — $($t.key)`n"
    } else {
      $body += "- [ ] $($t.key) — $($t.title)`n"
    }
  }
  $tmp = Join-Path ([System.IO.Path]::GetTempPath()) "epic-$($e.key).md"
  if (-not $DryRun) { Set-Content -Path $tmp -Value $body -Encoding utf8 }
  $args = @('issue','create','-R',$Repo,'--title',$e.title,'--label',($e.labels -join ','),'--milestone',$e.milestone,'--body-file',$tmp)
  Invoke-Gh $args | Out-Null
  Write-Host "  created epic: $($e.title)"
}

# ---------------------------------------------------------------- 5. Native sub-issue links
Write-Host "`n== Sub-issue links ==" -ForegroundColor Green
$issueMap = Get-IssueMap
$linkOk = 0; $linkSkip = 0
$subQuery = 'mutation($e:ID!,$s:ID!){addSubIssue(input:{issueId:$e,subIssueId:$s}){subIssue{number}}}'
foreach ($e in $m.epics) {
  if (-not $issueMap.ContainsKey($e.title)) { continue }
  $epicId = $issueMap[$e.title].id
  foreach ($t in ($m.tasks | Where-Object { $_.epic -eq $e.key })) {
    if (-not $issueMap.ContainsKey($t.title)) { continue }
    $taskId = $issueMap[$t.title].id
    if ($DryRun) { Write-Host "  [dry-run] link $($t.key) -> $($e.key)" -ForegroundColor DarkGray; continue }
    $res = & gh api graphql -H "GraphQL-Features: sub_issues" -f query=$subQuery -f e=$epicId -f s=$taskId 2>&1
    if ($LASTEXITCODE -eq 0) { $linkOk++; Write-Host "  linked: $($t.key) -> $($e.key)" }
    else { $linkSkip++; Write-Host "  skip (already linked or unsupported): $($t.key) -> $($e.key)" -ForegroundColor DarkYellow }
  }
}
Write-Host "`nSub-issue links: $linkOk ok, $linkSkip skipped." -ForegroundColor Cyan
Write-Host "Bootstrap complete." -ForegroundColor Green
