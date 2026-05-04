param(
    [string]$Python = "",
    [string]$AppVersion = "1.0.0",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SharedVenv  = Join-Path (Split-Path -Parent $ProjectRoot) ".venv\Scripts\python.exe"

if ($Python -eq "") {
    if (Test-Path $SharedVenv) {
        $Python = $SharedVenv
    } else {
        $Python = "python"
    }
}

Write-Host "[NoteForge] Python: $Python"
Write-Host "[NoteForge] Version: $AppVersion"

$DistDir     = Join-Path $ProjectRoot "dist\windows"
$WorkDir     = Join-Path $ProjectRoot "build\windows"
$EntryScript = Join-Path $ProjectRoot "run_noteforge_entry.py"
$IconPath    = Join-Path $ProjectRoot "assets\noteforge_icon.ico"
$AssetsDir   = Join-Path $ProjectRoot "assets"
$SpecDir     = Join-Path $ProjectRoot "build"

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
New-Item -ItemType Directory -Force -Path $SpecDir | Out-Null

# PyInstaller インストール確認
Write-Host "[NoteForge] Installing build dependencies..."
& $Python -m pip install pyinstaller pillow --quiet
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# アイコン生成（未存在の場合）
if (-not (Test-Path $IconPath)) {
    Write-Host "[NoteForge] Generating icon..."
    & $Python (Join-Path $AssetsDir "generate_icon.py")
}

Write-Host "[NoteForge] Building EXE..."
$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--name", "SakuraNoteForge",
    "--windowed",
    "--distpath", $DistDir,
    "--workpath", $WorkDir,
    "--specpath", $SpecDir,
    "--add-data", "$AssetsDir;assets",
    "--collect-all", "markdown",
    "--collect-all", "pygments",
    "--collect-all", "PySide6.QtWebEngineWidgets"
)

if (Test-Path $IconPath) {
    $PyInstallerArgs += @("--icon", $IconPath)
}

$PyInstallerArgs += $EntryScript

& $Python @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$AppDir = Join-Path $DistDir "SakuraNoteForge"
Write-Host "[NoteForge] EXE 生成完了: $AppDir"

if (-not $SkipInstaller) {
    $IssScript = Join-Path $ProjectRoot "installer\SakuraNoteForge.iss"
    if (-not (Test-Path $IssScript)) {
        Write-Host "[NoteForge] .iss ファイルが見つかりません。インストーラー生成をスキップ。"
    } else {
        $IsccPath = ""
        foreach ($candidate in @(
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            "C:\Program Files\Inno Setup 6\ISCC.exe"
        )) {
            if (Test-Path $candidate) { $IsccPath = $candidate; break }
        }

        if ($IsccPath -eq "") {
            Write-Host "[NoteForge] Inno Setup が見つかりません。インストーラー生成をスキップ。"
            Write-Host "  → https://jrsoftware.org/isdl.php からインストール後、再実行してください。"
        } else {
            Write-Host "[NoteForge] Inno Setup でインストーラー生成中..."
            & $IsccPath "/DAppVersion=$AppVersion" $IssScript
            if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
            $InstallerDir = Join-Path $ProjectRoot "dist\installer"
            Write-Host "[NoteForge] インストーラー生成完了: $InstallerDir"
        }
    }
}

Write-Host ""
Write-Host "=== ビルド完了 ==="
Write-Host "EXE:         $AppDir\SakuraNoteForge.exe"
