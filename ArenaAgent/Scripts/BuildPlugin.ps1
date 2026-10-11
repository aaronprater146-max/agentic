<#
.SYNOPSIS
Compiles the ArenaAgent plugin source against a launcher-installed Unreal Engine.

.DESCRIPTION
Launcher installs ship the full build toolchain (Engine\Build\BatchFiles\Build.bat -> UnrealBuildTool),
but UBT compiles plugin modules as part of a project target. This script therefore:
  1. Locates your engine (argument, env var, registry, or C:\Program Files\Epic Games\UE_5.*).
  2. Creates a tiny scratch host project in %TEMP% (kept between runs for fast incremental builds).
  3. Mirrors the plugin into <scratch>\Plugins\ArenaAgent.
  4. Runs: Build.bat ArenaAgentScratchEditor Win64 Development -Project=<scratch>.uproject

.PARAMETER EnginePath
Explicit engine root (the folder that contains Engine\). Auto-detected when omitted.

.PARAMETER ScratchDir
Where the scratch host project lives. Defaults to %TEMP%\ArenaAgentScratch.

.EXAMPLE
Scripts\Build.bat
Scripts\Build.bat -EnginePath "C:\Program Files\Epic Games\UE_5.8"
#>
param(
    [string]$EnginePath = "",
    [string]$ScratchDir = ""
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginRoot = Split-Path -Parent $ScriptRoot   # .../ArenaAgent

function Write-Step($msg) { Write-Host "[ArenaAgent] $msg" -ForegroundColor Cyan }
function Write-Fail($msg) { Write-Host "[ArenaAgent] ERROR: $msg" -ForegroundColor Red }

# ---------------------------------------------------------------- find engine
function Find-EnginePath {
    if ($EnginePath -and (Test-Path $EnginePath)) { return (Resolve-Path $EnginePath).Path }

    if ($env:ARENA_UE_PATH -and (Test-Path $env:ARENA_UE_PATH)) { return (Resolve-Path $env:ARENA_UE_PATH).Path }

    # Registry: launcher + source-build registrations.
    $RegRoots = @(
        "HKLM:\SOFTWARE\Epic Games\Unreal Engine",
        "HKLM:\SOFTWARE\EpicGames\Unreal Engine",
        "HKCU:\SOFTWARE\Epic Games\Unreal Engine\Builds",
        "HKCU:\SOFTWARE\EpicGames\Unreal Engine\Builds"
    )
    foreach ($Root in $RegRoots) {
        if (Test-Path $Root) {
            foreach ($Key in (Get-ChildItem $Root -ErrorAction SilentlyContinue)) {
                $Dir = (Get-ItemProperty $Key.PSPath -ErrorAction SilentlyContinue).InstalledDirectory
                if ($Dir -and (Test-Path $Dir)) { return $Dir }
            }
        }
    }

    # Common launcher install locations, newest version first.
    $Candidates = @()
    foreach ($Drive in @($env:SystemDrive, "C", "D", "E") | Select-Object -Unique) {
        $Base = "${Drive}:\Program Files\Epic Games"
        if (Test-Path $Base) {
            $Candidates += Get-ChildItem $Base -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^UE_?\d+\.\d+' } |
                Sort-Object { [version]($_.Name -replace '^UE_?', '') } -Descending
        }
    }
    foreach ($C in $Candidates) {
        if (Test-Path (Join-Path $C.FullName "Engine\Build\BatchFiles\Build.bat")) { return $C.FullName }
    }
    return $null
}

Write-Step "Locating Unreal Engine..."
$Engine = Find-EnginePath
if (-not $Engine) {
    Write-Fail "Could not find a UE5 install. Pass -EnginePath `"C:\Program Files\Epic Games\UE_5.8`" or set ARENA_UE_PATH."
    exit 2
}
$BuildBat = Join-Path $Engine "Engine\Build\BatchFiles\Build.bat"
if (-not (Test-Path $BuildBat)) {
    Write-Fail "No Build.bat under '$Engine'. Is this an engine root (contains Engine\)?"
    exit 2
}
Write-Step "Engine: $Engine"

# ------------------------------------------------- engine association (5.x)
$Assoc = "5.8"
$VersionFile = Join-Path $Engine "Engine\Build\Build.version"
if (Test-Path $VersionFile) {
    $V = Get-Content $VersionFile -Raw | ConvertFrom-Json
    $Assoc = "$($V.MajorVersion).$($V.MinorVersion)"
}
Write-Step "Engine association: $Assoc"

# ------------------------------------------------------------- scratch project
if (-not $ScratchDir) { $ScratchDir = Join-Path $env:TEMP "ArenaAgentScratch" }
New-Item -ItemType Directory -Force -Path $ScratchDir | Out-Null
$ProjectName = "ArenaAgentScratch"
$UProject = Join-Path $ScratchDir "$ProjectName.uproject"
if (-not (Test-Path $UProject)) {
    $UProjectJson = @"
{
	"FileVersion": 3,
	"EngineAssociation": "$Assoc",
	"Category": "Build",
	"Description": "Scratch host project for compiling the ArenaAgent plugin",
	"Plugins": [
		{
			"Name": "ArenaAgent",
			"Enabled": true
		}
	]
}
"@
    Set-Content -Path $UProject -Value $UProjectJson -Encoding ASCII
    Write-Step "Created scratch project: $UProject"
}

# ------------------------------------------------------- mirror plugin sources
$TargetPlugin = Join-Path $ScratchDir "Plugins\ArenaAgent"
New-Item -ItemType Directory -Force -Path (Join-Path $ScratchDir "Plugins") | Out-Null
Write-Step "Syncing plugin sources -> $TargetPlugin"
robocopy $PluginRoot $TargetPlugin /MIR /XD Intermediate Binaries Saved .git > $null
# robocopy exit codes < 8 mean success
if ($LASTEXITCODE -ge 8) {
    Write-Fail "robocopy failed with code $LASTEXITCODE"
    exit 2
}

# ------------------------------------------------------------------- build UBT
Write-Step "Running UnrealBuildTool (${ProjectName}Editor Win64 Development). This can take several minutes the first time..."
& $BuildBat "$($ProjectName)Editor" Win64 Development "-Project=$UProject" -WaitMutex
$Result = $LASTEXITCODE

if ($Result -eq 0) {
    Write-Host ""
    Write-Host "[ArenaAgent] BUILD SUCCEEDED." -ForegroundColor Green
    Write-Step "Copy '$TargetPlugin' into <YourProject>\Plugins\ArenaAgent (or point your project at it) and launch the editor."
    exit 0
}
else {
    Write-Fail "UnrealBuildTool exited with code $Result. Paste the errors back and we'll fix them."
    exit $Result
}
